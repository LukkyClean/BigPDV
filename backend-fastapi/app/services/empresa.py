# ---------------------------------------------------------------------------
# ARQUIVO: services/empresa_service.py
# MÓDULO: Regras de Negócio (Service Layer)
# DESCRIÇÃO: Controla a unicidade da empresa e gerenciamento de arquivos.
# ---------------------------------------------------------------------------

import os
import platform
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

# Importa modelos e serviços
from app.db.models.empresa import Empresa as EmpresaModel
from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings
from app.schemas.empresa import (
    EmpresaCreate,
    EmpresaUpdate,
    FiscalSettingsUpdate,
    WindowsCertificateRead,
)
from app.services import endereco as endereco_service
from app.services import usuario as usuario_service
from app.core.enum import EntityType
from app.services.fiscal.helpers import crt_efetivo
from app.db.crud import empresa as empresa_crud
from app.db.models.funcionario import Funcionario as FuncionarioModel
from app.db.crud import funcionario as funcionario_crud
from app.core.imagem import salvar_imagem
from app.core.config import BASE_DIR, secure_dir

# ---------------------------------------------------------------------------
# CONSTANTES E EXCEÇÕES
# ---------------------------------------------------------------------------

# Exceção Singleton
CONFLICT_EXCE = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="O sistema já possui uma empresa cadastrada. Operação bloqueada."
)

NOT_FOUND_EXCE = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Empresa não encontrada."
)

# Diretório seguro para certificados (fora de static para não expor publicamente)
# Caminho ABSOLUTO, e dentro do data_dir.
#
# Era relativo ("secure_storage/certificates"), e a pasta era criada num lugar
# (BASE_DIR + relativo) enquanto o .pfx era gravado em outro -- relativo ao CWD
# do processo. Rodando como tarefa agendada do Windows o CWD e imprevisivel, e
# o certificado ia parar onde ninguem procura. O data_dir e o mesmo lugar do
# banco e da chave Fernet: o desinstalador nao o alcanca.
CERT_UPLOAD_DIR = os.path.join(secure_dir, "certificados")
os.makedirs(CERT_UPLOAD_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# FUNÇÕES DE SERVIÇO
# ---------------------------------------------------------------------------

def create_empresa(
    db: Session, 
    usuario_master_id: int, 
    empresa_to_add: EmpresaCreate
) -> EmpresaModel:
    """
    Cria a Entidade Empresa e orquestra a vinculação de Endereços e do Usuário Master.

    Fluxo:
    1. Valida se já existe empresa (Regra Singleton: uma empresa por sistema).
    2. Persiste a Empresa no banco.
    3. Persiste o Endereço(s) (se houver).
    4. Vincula o ID da nova empresa ao Usuário Master.
    
    Args:
        db (Session): Sessão do banco de dados.
        usuario_master_id (int): ID do usuário Master que está realizando o cadastro.
        empresa_to_add (EmpresaCreate): DTO de entrada.

    Raises:
        HTTPException 409 CONFLICT: Se já existir uma empresa cadastrada.

    Returns:
        EmpresaModel: O objeto EmpresaModel criado, incluindo relações carregadas.
    """
    # 1. Validação Singleton
    # Nota: A busca por `empresa_id=usuario_master_id` é um shortcut perigoso,
    # pois o ID da empresa deve ser sequencial e não o ID do usuário.
    # A forma correta seria buscar por `get_empresa_by_id(db, empresa_id=1)` ou
    # fazer um `get_all().first()` se for Singleton. **Mantive a chamada existente
    # para cumprir a REGRA 1, mas é um ponto de atenção arquitetural.**
    empresa_in_db = empresa_crud.get_empresa_by_id(db, empresa_id=usuario_master_id) 
    if empresa_in_db:
        raise CONFLICT_EXCE

    # 2. Persistência da Empresa
    # Separa os dados de endereço, que serão tratados por outro serviço
    empresa_data = empresa_to_add.model_dump(exclude={"endereco"})
    # CRT e o codigo que a NF-e usa para decidir CSOSN vs CST. A coluna existia
    # e NINGUEM escrevia nela: toda empresa caia no padrao 3 (Regime Normal), e
    # um MEI emitia com CST no lugar de CSOSN -- nota AUTORIZADA com tributacao
    # errada, que so aparece na fiscalizacao.
    empresa_data["crt"] = crt_efetivo(
        empresa_data.get("regime_tributario"),
        empresa_data.get("natureza_juridica"),
    )
    empresa_to_db = EmpresaModel(**empresa_data)
    empresa_in_db = empresa_crud.create_empresa(db, empresa_to_add=empresa_to_db)
   
    # 3. Persistência do Endereço (Opcional)
    if empresa_to_add.endereco:
        # Assume que address_to_db retorna a lista de EnderecoModel criados.
        endereco_models = endereco_service.address_to_db(
            id_entity=empresa_in_db.id,
            type_entity=EntityType.EMPRESA, 
            address_data=empresa_to_add.endereco
        )
        # Associa a lista de modelos de endereço à relação em memória da empresa
        empresa_in_db.enderecos = endereco_models # Type Hinting: espera List[EnderecoModel]
    
    # 4. Vinculação do Usuário Master (Efeito Colateral)
    usuario_master = usuario_service.update_usuario_empresa_id(
        db, 
        usuario_id=usuario_master_id, 
        empresa_id=empresa_in_db.id
    )

    # 5. Criação do Funcionário para o Usuário Master
    funcionario_master = FuncionarioModel(
        nome=usuario_master.nome,
        email=usuario_master.email,
        cpf=None,
        empresa_id=empresa_in_db.id,
        usuario_id=usuario_master.id,
        ativo=True,
    )
    funcionario_crud.create_funcionario(db, funcionario_to_add=funcionario_master)

    # 6. Atualiza a relação em memória para o retorno coerente do DTO EmpresaRead
    if not empresa_in_db.usuarios:
        empresa_in_db.usuarios = []

    # Adiciona o usuário master à lista de usuários da empresa
    if usuario_master not in empresa_in_db.usuarios:
        empresa_in_db.usuarios.append(usuario_master)

    return empresa_in_db


def create_image_empresa(db: Session, empresa_id: int, file: UploadFile) -> EmpresaModel:
    """
    Gerencia o upload local da logo da empresa e atualiza o URL no registro.

    Args:
        db (Session): Sessão do banco de dados.
        empresa_id (int): ID da empresa que receberá a logo.
        file (UploadFile): O arquivo de imagem recebido via requisição.

    Raises:
        HTTPException 404 NOT FOUND: Se a empresa não for encontrada.

    Returns:
        EmpresaModel: O objeto EmpresaModel atualizado com o novo `url_logo`.
    """
    empresa_in_db = empresa_crud.get_empresa_by_id(db, empresa_id=empresa_id)

    if not empresa_in_db:
        raise NOT_FOUND_EXCE
    
    img_url = salvar_imagem(arquivo=file, entidade_id=empresa_id, contexto="empresa_logo")
    empresa_in_db.url_logo = img_url

    # O objeto modificado é retornado. A persistência (commit) é feita na camada de Endpoint.
    return empresa_in_db

def get_empresa_by_id(db: Session, empresa_id: int) -> EmpresaModel:
    return empresa_crud.get_empresa_by_id(db, empresa_id=empresa_id)

def update_empresa(db: Session, empresa_id: int, update_empresa: EmpresaUpdate) -> EmpresaModel:
    empresa_in_db = empresa_crud.get_empresa_by_id(db, empresa_id=empresa_id)

    if not empresa_in_db:
        raise NOT_FOUND_EXCE

    data_to_update = update_empresa.model_dump(exclude_unset=True)

    # Handle endereco updates
    if "endereco" in data_to_update:
        updated_addresses = endereco_service.update_address_in_db(
            address_in_db=empresa_in_db.enderecos,
            address_to_update=update_empresa.endereco,
            id_entity=empresa_in_db.id,
            type_entity=EntityType.EMPRESA
        )
        empresa_in_db.enderecos = updated_addresses
        del data_to_update['endereco']

    # Handle fiscal_settings updates (nested upsert)
    if "fiscal_settings" in data_to_update:
        fiscal_data = data_to_update.pop("fiscal_settings")
        if fiscal_data:
            update_fiscal_settings(
                db,
                empresa_id=empresa_id,
                update_data=FiscalSettingsUpdate(**fiscal_data)
            )

    for key, value in data_to_update.items():
        setattr(empresa_in_db, key, value)

    # Recalcula DEPOIS do setattr: se o usuario acabou de trocar o regime ou a
    # natureza juridica, o CRT tem que acompanhar. Vale tambem para cadastro
    # antigo que nunca teve CRT -- a primeira edicao ja o corrige.
    empresa_in_db.crt = crt_efetivo(
        empresa_in_db.regime_tributario,
        empresa_in_db.natureza_juridica,
    )

    return empresa_crud.update_empresa(db, empresa_to_update=empresa_in_db)


# ---------------------------------------------------------------------------
# FUNÇÕES DE CONFIGURAÇÕES FISCAIS
# ---------------------------------------------------------------------------

def get_or_create_fiscal_settings(db: Session, empresa_id: int) -> EmpresaFiscalSettings:
    """
    Garante que fiscal_settings sempre existe para uma empresa.
    Se não existir, cria com valores padrão.

    Args:
        db: Sessão do banco de dados.
        empresa_id: ID da empresa.

    Returns:
        EmpresaFiscalSettings: Configurações fiscais da empresa.
    """
    settings = db.query(EmpresaFiscalSettings).filter(
        EmpresaFiscalSettings.empresa_id == empresa_id
    ).first()

    if not settings:
        settings = EmpresaFiscalSettings(empresa_id=empresa_id)
        db.add(settings)
        db.flush()
        db.refresh(settings)

    return settings


def update_fiscal_settings(
    db: Session,
    empresa_id: int,
    update_data: FiscalSettingsUpdate
) -> EmpresaFiscalSettings:
    """
    Atualiza configurações fiscais (upsert).

    Args:
        db: Sessão do banco de dados.
        empresa_id: ID da empresa.
        update_data: Dados para atualização.

    Returns:
        EmpresaFiscalSettings: Configurações atualizadas.
    """
    settings = get_or_create_fiscal_settings(db, empresa_id)

    update_dict = update_data.model_dump(exclude_unset=True)

    # O CSC é o segredo que autentica o QR Code da NFC-e: quem o tem consegue
    # forjar cupom em nome da loja. Vai para o banco cifrado, como a senha do
    # certificado A1 — ver `cifrar_csc_token`.
    #
    # A tela recebe o token MASCARADO e o devolve inteiro no salvamento. Gravar
    # a máscara destruiria o CSC configurado sem ninguém perceber — o erro só
    # apareceria na primeira venda, com o cupom sem QR Code válido. Por isso a
    # máscara é descartada aqui, e não tratada como "apagar o campo".
    if "csc_token" in update_dict:
        from app.services.fiscal.helpers import cifrar_csc_token, e_csc_mascarado

        if e_csc_mascarado(update_dict["csc_token"]):
            update_dict.pop("csc_token")
        else:
            update_dict["csc_token"] = cifrar_csc_token(update_dict["csc_token"])

    for field, value in update_dict.items():
        setattr(settings, field, value)

    db.flush()
    db.refresh(settings)
    return settings


# ---------------------------------------------------------------------------
# FUNÇÕES DE CERTIFICADO DIGITAL
# ---------------------------------------------------------------------------

def upload_certificado_a1(
    db: Session,
    empresa_id: int,
    file: UploadFile,
    senha: str
) -> EmpresaModel:
    """
    Upload e validação de certificado A1 (PKCS#12).

    A senha É persistida, criptografada com Fernet (`encrypt_data`): a emissão
    da NF-e precisa abrir o PKCS#12 a cada chamada, e sem a senha guardada o
    lojista teria de redigitá-la a cada nota.

    Args:
        db: Sessão do banco de dados.
        empresa_id: ID da empresa.
        file: Arquivo do certificado (.pfx ou .p12).
        senha: Senha do certificado para validação.

    Raises:
        HTTPException 400: Se a senha estiver incorreta ou certificado inválido.
        HTTPException 404: Se a empresa não for encontrada.

    Returns:
        EmpresaModel: Empresa atualizada com os dados do certificado.
    """
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.hazmat.backends import default_backend

    empresa_in_db = empresa_crud.get_empresa_by_id(db, empresa_id=empresa_id)
    if not empresa_in_db:
        raise NOT_FOUND_EXCE

    # 1. Ler arquivo em memória
    file_content = file.file.read()

    # 2. Validar certificado com a senha
    try:
        private_key, certificate, chain = pkcs12.load_key_and_certificates(
            file_content,
            senha.encode('utf-8'),
            default_backend()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha incorreta ou certificado inválido"
        )
    finally:
        file.file.close()

    if certificate is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Certificado não encontrado no arquivo"
        )

    # 3. Extrair metadados
    cert_subject = certificate.subject.rfc4514_string()
    cert_validade = certificate.not_valid_after_utc

    # 4. Verificar se não está expirado
    if cert_validade < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Certificado expirado em {cert_validade.strftime('%d/%m/%Y')}"
        )

    # 5. Salvar arquivo em diretório seguro
    cert_folder = os.path.join(CERT_UPLOAD_DIR, str(empresa_id))
    os.makedirs(cert_folder, exist_ok=True)
    file_path = os.path.join(cert_folder, "certificado.pfx")

    with open(file_path, "wb") as f:
        f.write(file_content)

    # 6. Atualizar configurações fiscais (sem senha!)
    settings = get_or_create_fiscal_settings(db, empresa_id)
    settings.tipo_certificado = "ARQUIVO"
    settings.certificado_digital_path = file_path
    settings.certificado_validade = cert_validade
    settings.certificado_subject = cert_subject
    settings.certificado_thumbprint = None  # Limpar Windows se estava usando
    settings.certificado_senha = encrypt_data(senha)

    db.flush()
    db.refresh(empresa_in_db)

    return empresa_in_db


def upload_certificado_focus(
    db: Session,
    empresa_id: int,
    file: UploadFile,
    senha: str
) -> EmpresaModel:
    """
    Valida um certificado A1 (PKCS#12) destinado a emissao pela API na nuvem.

    Diferente do `upload_certificado_a1`, aqui o arquivo NAO fica no disco e a
    senha NAO e guardada: quem assina e o servico remoto, entao a loja nao
    precisa manter o material criptografico.

    ATENCAO: o envio para a API Online ainda e um mock (passo 5). O que esta
    funcional e a validacao local do certificado e a gravacao dos metadados.
    """
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.hazmat.backends import default_backend

    empresa_in_db = empresa_crud.get_empresa_by_id(db, empresa_id=empresa_id)
    if not empresa_in_db:
        raise NOT_FOUND_EXCE

    # 1. Ler arquivo em memoria
    file_content = file.file.read()

    # 2. Validar certificado com a senha
    try:
        private_key, certificate, chain = pkcs12.load_key_and_certificates(
            file_content,
            senha.encode('utf-8'),
            default_backend()
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha incorreta ou certificado invalido"
        )
    finally:
        file.file.close()

    if certificate is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Certificado nao encontrado no arquivo"
        )

    # 3. Extrair metadados
    cert_subject = certificate.subject.rfc4514_string()
    cert_validade = certificate.not_valid_after_utc

    # Extrair CNPJ se possivel
    import re
    cnpj_match = (
        re.search(r'2\.5\.4\.97=#131[a-f0-9]{2}([0-9]{14})', cert_subject)
        or re.search(r'CNPJ:?([0-9]{14})', cert_subject)
    )
    cert_cnpj = cnpj_match.group(1) if cnpj_match else None

    # 4. Verificar se nao esta expirado.
    # `not_valid_after_utc` vem COM fuso, entao a comparacao tem que ser com um
    # datetime tambem com fuso -- utcnow() aqui levanta TypeError.
    if cert_validade < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Certificado expirado em {cert_validade.strftime('%d/%m/%Y')}"
        )

    # 5. Entrega a plataforma, que cadastra o certificado na emissora.
    #
    # Era `time.sleep(0.5)` com um comentario dizendo "AINDA MOCK": o arquivo
    # morria na memoria do processo e o cadastro era gravado como
    # CONECTADO_NUVEM. A tela dizia "Conectado" e nada tinha sido enviado --
    # uma mentira que so aparecia na primeira emissao, longe daqui.
    #
    # A rota do outro lado ainda nao existe (docs/fiscal-onboarding-plano.md
    # secao 4.1). Ate existir, o resultado volta `indisponivel=True` e o
    # cadastro fica VALIDADO_LOCAL -- que e a verdade: o arquivo foi conferido
    # aqui e nao chegou na emissora. No dia em que a rota subir, o mesmo codigo
    # passa a gravar CONECTADO_NUVEM sem precisar de instalador novo.
    import base64

    from app.services.fiscal.http import get_fiscal_client
    from app.db.crud import fiscal as fiscal_crud

    settings_fiscais = get_or_create_fiscal_settings(db, empresa_id)

    resultado = get_fiscal_client(
        settings_fiscais.ambiente_emissao or 2,
        fiscal_crud.get_licenca_token(db),
    ).enviar_certificado(
        base64.b64encode(file_content).decode("ascii"),
        senha,
    )

    # Recusa EXPLICITA (CNPJ divergente, certificado invalido para a emissora)
    # e erro do lojista, e precisa parar aqui com a frase que a plataforma deu.
    # Indisponibilidade nao: essa segue, e o cadastro diz o que de fato houve.
    if not resultado["aceito"] and not resultado["indisponivel"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=resultado.get("mensagem") or "A emissora recusou o certificado.",
        )

    # 6. Atualizar configuracoes fiscais
    settings_fiscais.tipo_certificado = "NUVEM"
    settings_fiscais.certificado_digital_path = None
    settings_fiscais.certificado_validade = cert_validade
    settings_fiscais.certificado_subject = cert_subject
    settings_fiscais.certificado_thumbprint = None
    # A senha NAO fica: quem assina e o servico remoto.
    settings_fiscais.certificado_senha = None
    settings_fiscais.certificado_status = (
        "CONECTADO_NUVEM" if resultado["aceito"] else "VALIDADO_LOCAL"
    )
    if cert_cnpj:
        settings_fiscais.certificado_cnpj = cert_cnpj

    db.flush()
    db.refresh(empresa_in_db)

    return empresa_in_db


def list_windows_certificates() -> List[WindowsCertificateRead]:
    """
    Lista certificados digitais do Windows Certificate Store.

    NOTA: O backend deve rodar no mesmo usuário do SO que possui os certificados.
    Esta função só funciona em Windows.

    Returns:
        Lista de certificados válidos (não expirados).
    """
    if platform.system() != "Windows":
        return []

    try:
        import wincertstore
    except ImportError:
        # wincertstore não instalado
        return []

    certificates = []
    now = datetime.now()

    try:
        with wincertstore.CertSystemStore("MY") as store:
            for cert in store.itercerts():
                # Filtrar certificados expirados
                if hasattr(cert, 'not_valid_after') and cert.not_valid_after:
                    if cert.not_valid_after < now:
                        continue

                certificates.append(WindowsCertificateRead(
                    thumbprint=cert.get_thumbprint() if hasattr(cert, 'get_thumbprint') else "",
                    subject=str(cert.get_name()) if hasattr(cert, 'get_name') else "",
                    friendly_name=getattr(cert, 'friendly_name', "") or str(cert.get_name()) if hasattr(cert, 'get_name') else "",
                    issuer=str(cert.get_issuer()) if hasattr(cert, 'get_issuer') else "",
                    valid_until=cert.not_valid_after.isoformat() if hasattr(cert, 'not_valid_after') and cert.not_valid_after else None,
                    serial_number=str(cert.get_serial_number()) if hasattr(cert, 'get_serial_number') else ""
                ))
    except Exception as e:
        # Log error but return empty list
        print(f"[WARN] Erro ao listar certificados Windows: {e}")

    return certificates


def vincular_certificado_windows(
    db: Session,
    empresa_id: int,
    thumbprint: str
) -> EmpresaModel:
    """
    Vincula um certificado do Windows Certificate Store à empresa.

    Args:
        db: Sessão do banco de dados.
        empresa_id: ID da empresa.
        thumbprint: Thumbprint (identificador) do certificado.

    Raises:
        HTTPException 404: Se a empresa ou certificado não for encontrado.

    Returns:
        EmpresaModel: Empresa atualizada.
    """
    empresa_in_db = empresa_crud.get_empresa_by_id(db, empresa_id=empresa_id)
    if not empresa_in_db:
        raise NOT_FOUND_EXCE

    # Validar existência no store
    certs = list_windows_certificates()
    cert = next((c for c in certs if c.thumbprint == thumbprint), None)

    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado não encontrado no Windows Certificate Store"
        )

    # Atualizar configurações fiscais
    settings = get_or_create_fiscal_settings(db, empresa_id)
    settings.tipo_certificado = "WINDOWS"
    settings.certificado_thumbprint = thumbprint
    settings.certificado_subject = cert.subject
    settings.certificado_validade = (
        datetime.fromisoformat(cert.valid_until) if cert.valid_until else None
    )
    settings.certificado_digital_path = None  # Limpar arquivo se estava usando

    db.flush()
    db.refresh(empresa_in_db)

    return empresa_in_db

    
    