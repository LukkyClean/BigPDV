# ---------------------------------------------------------------------------
# ARQUIVO: endpoints/empresa.py
# MÓDULO: Interface de API (Controller)
# DESCRIÇÃO: Gerencia o ciclo de vida da entidade Empresa (Tenant).
# ---------------------------------------------------------------------------

import base64
import mimetypes
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Path, UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.empresa import (
    EmpresaCreate,
    EmpresaAdminRead,
    EmpresaUpdate,
    WindowsCertificateRead,
    CertificadoWindowsVincular,
)
from app.db.models.usuario import Usuario as UsuarioModel
from app.core.config import BASE_DIR
from app.core.depends import get_current_master_user, get_current_user, _handle_db_transaction
from app.db.session import get_db
from app.services import empresa as empresa_service


router = APIRouter()


@router.post(
    "/",
    response_model=EmpresaAdminRead,
    status_code=status.HTTP_201_CREATED,
    summary="Inicializar Empresa (Setup)",
    description="Cria a empresa única do sistema e vincula o usuário Master logado a ela."
)
def create_empresa(
    usuario_master: dict = Depends(get_current_master_user),
    *,
    empresa_to_add: EmpresaCreate,
    db: Session = Depends(get_db)
):
    """
    Realiza o cadastro da empresa (Tenant) no banco de dados.
    
    Regras:
    1. Requer um usuário Master autenticado.
    2. Só permite o cadastro se não houver nenhuma empresa registrada (Singleton).
    3. Vincula automaticamente o usuário logado como pertencente a essa empresa.

    Args:
        usuario_master (dict): Payload do token do Usuário Master (contém 'sub'/ID).
        empresa_to_add (EmpresaCreate): Payload com dados da empresa e endereço.
        db (Session): Sessão de banco de dados.

    Returns:
        EmpresaRead: Dados da empresa criada.
    """
    # A ID do usuário Master é extraída do token (campo 'sub')
    usuario_master_id = int(usuario_master.get("sub"))
    
    return _handle_db_transaction(
        db,
        empresa_service.create_empresa,
        usuario_master_id,
        empresa_to_add
    )

@router.post(
    "/imagem",
    response_model=EmpresaAdminRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload de Logomarca",
    description="Armazena a imagem enviada e atualiza a URL da logo da empresa."
)
def create_image_empresa(
    usuario_master: dict = Depends(get_current_master_user),
    file: UploadFile = File(..., description="Arquivo de imagem (JPEG, PNG)"),
    db: Session = Depends(get_db)
):
    """
    Endpoint para upload de branding da empresa.
    
    Args:
        usuario_master (dict): Payload do token do Usuário Master (contém 'empresa_id').
        file (UploadFile): O arquivo de imagem enviado.
        db (Session): Sessão de banco de dados.

    Returns:
        EmpresaRead: Dados da empresa atualizada.
    """
    # FIX/Ajuste: Deve-se passar o empresa_id e não o sub (usuario_id)
    empresa_id: Optional[int] = usuario_master.get("empresa_id")

    if not empresa_id:
        # Se o Master não tiver empresa_id no token, significa que a empresa não foi criada
        # ou o token está desatualizado. Levanta uma exceção (404/400).
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O ID da Empresa não está presente no token de acesso. Crie a empresa primeiro."
        )

    return _handle_db_transaction(
        db,
        empresa_service.create_image_empresa,
        empresa_id, # Passa o ID da empresa do token
        file
    )

@router.get(
    "/",
    response_model=EmpresaAdminRead,
    status_code=status.HTTP_200_OK,
    summary="Retorna os dados da empresa cadastrada!",
    description="Retorna empresa com fiscal_settings sempre instanciado (nunca null)."
)
def get_empresa_data(
    user_token: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    empresa_id = user_token.get('empresa_id')
    empresa = empresa_service.get_empresa_by_id(db, empresa_id)

    # Garantir que fiscal_settings existe (get_or_create)
    if empresa and not empresa.fiscal_settings:
        empresa_service.get_or_create_fiscal_settings(db, empresa_id)
        db.commit()
        db.refresh(empresa)

    return empresa

@router.get(
    "/logo-base64",
    status_code=status.HTTP_200_OK,
    summary="Logo da empresa como data URL base64",
    description=(
        "Devolve a logo da empresa em base64 (data URL). Usado pela impressão "
        "térmica (ESC/POS), que precisa LER os pixels da imagem para gerar o "
        "raster monocromático. O `<img>`/`fetch` cru contra o /static falha em "
        "modo CORS dentro do webview do Tauri (origem tauri.localhost != backend "
        "127.0.0.1:porta); este endpoint trafega pelo mesmo canal /api já "
        "autenticado, entregando os bytes em JSON sem depender de CORS no /static."
    ),
)
def get_logo_base64(
    user_token: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    empresa_id = user_token.get('empresa_id')
    empresa = empresa_service.get_empresa_by_id(db, empresa_id)

    if not empresa or not empresa.url_logo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa sem logo cadastrada.",
        )

    caminho = os.path.join(BASE_DIR, empresa.url_logo)
    if not os.path.isfile(caminho):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo da logo não encontrado no servidor.",
        )

    mime = mimetypes.guess_type(caminho)[0] or "image/webp"
    with open(caminho, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    return {"data_url": f"data:{mime};base64,{b64}"}

@router.put(
    '/',
    response_model=EmpresaAdminRead,
    status_code=status.HTTP_200_OK,
    summary="Atualiza os dados de empresa"
)
def update_empresa(
    user_token: dict = Depends(get_current_master_user),
    *,
    empresa_update_data: EmpresaUpdate,
    db: Session = Depends(get_db),
):
    empresa_id = user_token['empresa_id']

    return _handle_db_transaction(
        db,
        empresa_service.update_empresa,
        empresa_id,
        empresa_update_data
    )


# ---------------------------------------------------------------------------
# ENDPOINTS DE CERTIFICADO DIGITAL
# ---------------------------------------------------------------------------

@router.post(
    "/certificado-a1",
    response_model=EmpresaAdminRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload de Certificado A1 (PKCS#12)",
    description="""
    Realiza upload e validação de certificado digital A1.

    **Segurança:**
    - A senha é usada APENAS para validar o certificado
    - A senha NÃO é persistida no banco de dados
    - O arquivo é salvo em diretório seguro (fora de /static)

    **Validações:**
    - Verifica se a senha está correta
    - Verifica se o certificado não está expirado
    - Extrai metadados (subject, validade)
    """
)
def upload_certificado_a1(
    user_token: dict = Depends(get_current_master_user),
    file: UploadFile = File(..., description="Arquivo .pfx ou .p12"),
    senha: str = Form(..., description="Senha do certificado"),
    db: Session = Depends(get_db)
):
    empresa_id: Optional[int] = user_token.get("empresa_id")

    if not empresa_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID da Empresa não encontrado no token. Crie a empresa primeiro."
        )

    return _handle_db_transaction(
        db,
        empresa_service.upload_certificado_a1,
        empresa_id,
        file,
        senha
    )


@router.get(
    "/certificados-windows",
    response_model=List[WindowsCertificateRead],
    status_code=status.HTTP_200_OK,
    summary="Lista certificados do Windows",
    description="""
    Lista certificados digitais válidos do Windows Certificate Store.

    **Requisitos:**
    - Backend deve rodar em Windows
    - Backend deve rodar no mesmo usuário que possui os certificados
    - Retorna apenas certificados não expirados
    """
)
def list_certificados_windows(
    user_token: dict = Depends(get_current_master_user)
):
    return empresa_service.list_windows_certificates()


@router.post(
    "/certificado-windows",
    response_model=EmpresaAdminRead,
    status_code=status.HTTP_200_OK,
    summary="Vincula certificado do Windows",
    description="""
    Vincula um certificado do Windows Certificate Store à empresa.

    O certificado é identificado pelo thumbprint (identificador único).
    Não há upload de arquivo - o certificado já deve estar instalado no Windows.
    """
)
def vincular_certificado_windows(
    user_token: dict = Depends(get_current_master_user),
    payload: CertificadoWindowsVincular = ...,
    db: Session = Depends(get_db)
):
    empresa_id: Optional[int] = user_token.get("empresa_id")

    if not empresa_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID da Empresa não encontrado no token. Crie a empresa primeiro."
        )

    return _handle_db_transaction(
        db,
        empresa_service.vincular_certificado_windows,
        empresa_id,
        payload.thumbprint
    )