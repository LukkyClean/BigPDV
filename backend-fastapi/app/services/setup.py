# ---------------------------------------------------------------------------
# ARQUIVO: services/setup.py
# MÓDULO: Regras de Negócio (Service Layer)
# DESCRIÇÃO: Orquestra a criação atômica do setup inicial do sistema.
#            Cria: Usuario Master + Empresa + Endereco + Cargo Master + Funcionario.
# ---------------------------------------------------------------------------

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.schemas.auth import SetupCreate
from app.schemas.usuario import UsuarioCreate
from app.core.security import create_access_token

from app.services import usuario as usuario_service
from app.services import endereco as endereco_service
from app.services import licenca as licenca_service
from app.db.crud import usuario as usuario_crud
from app.db.crud import cargo as cargo_crud
from app.db.crud import empresa as empresa_crud
from app.db.crud import funcionario as funcionario_crud
from app.db.models.empresa import Empresa as EmpresaModel
from app.db.models.funcionario import Funcionario as FuncionarioModel
from app.db.models.cargo import Cargo as CargoModel
from app.core.enum import EntityType, Gender


def setup_sistema(db: Session, setup_data: SetupCreate) -> str:
    """
    Executa o setup inicial do sistema de forma atômica.

    Fluxo:
    1. Valida que não existe Master no sistema.
    2. Cria o Usuario Master.
    3. Cria a Empresa (com dados PJ se aplicável).
    4. Cria o Endereço (se fornecido).
    5. Cria o Cargo Master com permissões totais.
    6. Cria o Funcionario Master com dados do responsável.
    7. Gera e retorna o JWT token.

    Args:
        db (Session): Sessão do banco de dados.
        setup_data (SetupCreate): Dados completos do setup.

    Raises:
        HTTPException 409: Se o sistema já foi inicializado.
        HTTPException 500: Se o funcionário master não foi criado.

    Returns:
        str: Token JWT para autenticação imediata.
    """
    # 1. Check rápido (não é a proteção real — constraint do banco é)
    if usuario_crud.get_usuario_master(db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O sistema já foi inicializado. Setup bloqueado."
        )

    # 1.5 Registrar Licença (ANTES de criar entidades locais — garante atomicidade)
    # Pula o registro na API se a licença já existir localmente (caso de reconexão)
    from app.core.hwid import obter_hwid
    from app.db.crud import configuracao_licenca as licenca_crud
    
    hwid = obter_hwid()
    licenca_existente = licenca_crud.get_licenca_by_hwid(db, hwid)
    
    is_pj = setup_data.tipo_pessoa == "PJ"
    
    if not licenca_existente:

        endereco_licenca = {}
        if setup_data.endereco and len(setup_data.endereco) > 0:
            end = setup_data.endereco[0]
            endereco_licenca = {
                "cep": end.cep,
                "logradouro": end.logradouro,
                "numero": end.numero,
                "bairro": end.bairro,
                "cidade": end.cidade,
                "estado": end.estado.value if hasattr(end.estado, "value") else str(end.estado),
            }

        documento_licenca = setup_data.cnpj if is_pj else (setup_data.cpf or "")
        nome_licenca = setup_data.razao_social if is_pj else setup_data.nome_responsavel
        email_licenca = setup_data.email_responsavel or setup_data.email

        licenca_service.registrar_licenca(
            db=db,
            documento=documento_licenca,
            nome_ou_razao=nome_licenca,
            email=email_licenca,
            senha=setup_data.senha,
            endereco_data=endereco_licenca,
        )

    # 2. Criar Usuario Master
    usuario_create = UsuarioCreate(
        nome=setup_data.nome_usuario,
        email=setup_data.email,
        senha=setup_data.senha,
    )
    usuario_master = usuario_service.create_usuario(
        db,
        usuario_to_add=usuario_create,
        empresa_id=None,
        is_master=True,
    )

    # Flush para detectar IntegrityError de is_master duplicado (TOCTOU protection)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O sistema já foi inicializado. Setup bloqueado."
        )

    # 3. Criar Empresa (is_pj já definido no passo 1.5)
    # Em PF, quem assina a loja é a própria pessoa: o CPF e o nome do responsável
    # SÃO o documento e a razão social da empresa. Deixá-los nulos aqui fazia o
    # cadastro nascer sem documento — os cupons saíam sem a linha "CPF:" e a tela
    # de empresa não deixava salvar nada até o campo ser preenchido à mão.
    empresa_to_db = EmpresaModel(
        razao_social=setup_data.razao_social if is_pj else setup_data.nome_responsavel,
        nome_fantasia=setup_data.nome_loja,
        is_cnpj=is_pj,
        documento=setup_data.cnpj if is_pj else setup_data.cpf,
        segmento=setup_data.segmento,
        celular=setup_data.celular,
        email=setup_data.email_loja,
        telefone=setup_data.telefone,
        inscricao_estadual=setup_data.inscricao_estadual if is_pj else None,
        inscricao_municipal=setup_data.inscricao_municipal if is_pj else None,
        regime_tributario=setup_data.regime_tributario if is_pj else None,
    )
    empresa = empresa_crud.create_empresa(db, empresa_to_add=empresa_to_db)

    # 4. Criar Endereço (se fornecido)
    if setup_data.endereco:
        endereco_models = endereco_service.address_to_db(
            id_entity=empresa.id,
            type_entity=EntityType.EMPRESA,
            address_data=setup_data.endereco,
        )
        empresa.enderecos = endereco_models

    # Vincular usuario ao empresa
    usuario_master = usuario_service.update_usuario_empresa_id(
        db,
        usuario_id=usuario_master.id,
        empresa_id=empresa.id,
    )

    # 5. Criar Cargo Master
    cargo_master = CargoModel(
        empresa_id=empresa.id,
        nome="Master",
        permissoes={"all": True},
    )
    cargo_crud.create_cargo_funcionario(db, cargo_to_add=cargo_master)

    # 6. Criar Funcionario Master com dados do responsável
    funcionario_master = FuncionarioModel(
        nome=setup_data.nome_responsavel,
        email=setup_data.email_responsavel,
        celular=setup_data.celular_responsavel,
        cpf=setup_data.cpf if setup_data.tipo_pessoa == "PF" else None,
        rg=setup_data.rg if setup_data.tipo_pessoa == "PF" else None,
        genero=Gender(setup_data.genero) if setup_data.tipo_pessoa == "PF" and setup_data.genero else None,
        data_nascimento=date.fromisoformat(setup_data.data_nascimento) if setup_data.tipo_pessoa == "PF" and setup_data.data_nascimento else None,
        empresa_id=empresa.id,
        usuario_id=usuario_master.id,
        cargo_id=cargo_master.id,
        ativo=True,
    )
    funcionario_crud.create_funcionario(db, funcionario_to_add=funcionario_master)

    # 7. Gerar JWT Token
    token_data = {"sub": str(usuario_master.id)}
    return create_access_token(data=token_data)
