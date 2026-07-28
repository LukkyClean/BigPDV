# ---------------------------------------------------------------------------
# ARQUIVO: routers/auth.py
# MÓDULO: Interface de API (Router)
# DESCRIÇÃO: Define os endpoints públicos e protegidos para autenticação.
#            Gerencia o ciclo de vida do Token (emissão e revogação).
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends, status, Request, HTTPException
from sqlalchemy.orm import Session

from app.core.depends import get_token, _handle_db_transaction
from app.db.session import get_db
from app.schemas.auth import UsuarioLogin, SetupCreate, StatusResponse, LogoutRequest, ReconnectRequest
from app.services import auth as auth_service
from app.services import setup as setup_service
from app.services.licenca import desconectar_terminal

router = APIRouter()

# ===========================================================================
# EMISSÃO DE TOKEN JWT (LOGIN)
# ===========================================================================

@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    summary="Login com retorno de JWT Bearer Token"
)
async def login(request: Request, db: Session = Depends(get_db)):
    """
    Aceita as credenciais tanto em JSON (usado pelo frontend) quanto em
    form-data (útil no Swagger). Monta o UsuarioLogin e emite o token JWT.
    """
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        dados = await request.json()
        email = dados.get("email")
        senha = dados.get("senha")
        hwid = dados.get("hwid")
    else:
        form = await request.form()
        email = form.get("username") or form.get("email")
        senha = form.get("password") or form.get("senha")
        hwid = form.get("hwid")

    if not email or not senha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credenciais de login inválidas",
        )

    # O HWID identifica o terminal e e o que faz o limite da licenca valer.
    # Sem ele, o login nao acontece: aceitar hwid vazio permitia burlar o
    # limite de terminais (a API de licenca aceita string vazia), entao um
    # cliente que simplesmente omitisse o campo logava sem ocupar vaga.
    if not (hwid or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Terminal não identificado. Atualize o aplicativo e tente novamente.",
        )

    usuario_credentials = UsuarioLogin(email=email, senha=senha, hwid=hwid.strip())

    token_value = _handle_db_transaction(
        db,
        auth_service.login,
        login_usuario=usuario_credentials,
    )

    return {"access_token": token_value, "token_type": "bearer"}


# ===========================================================================
# REVOGAÇÃO DE TOKEN (LOGOUT)
# ===========================================================================

@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Realizar logout e revogar o token"
)
async def logout(
    body: LogoutRequest,
    token: dict = Depends(get_token),
    db: Session = Depends(get_db),
):
    """
    Invalida o token de acesso atual do usuário e desconecta o terminal.

    1. Revoga o JWT (JTI adicionado à blocklist).
    2. Remove o terminal de terminais_conectados.
    3. Notifica a API StartBig da desconexão.

    Args:
        body (LogoutRequest): Contém o HWID do terminal.
        token (dict): Payload do token atual (extraído via dependência get_token).
        db (Session): Sessão do banco de dados.
    """
    _handle_db_transaction(
        db,
        auth_service.logout_service,
        token
    )

    await desconectar_terminal(db, body.hwid)

    return {"message": "Logout bem-sucedido"}


# ===========================================================================
# STATUS DO SISTEMA (PÚBLICO)
# ===========================================================================

@router.get(
    "/status",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Verifica se o sistema foi inicializado"
)
def get_system_status(db: Session = Depends(get_db)):
    """
    Endpoint público que verifica se existe um usuário Master no sistema.
    Usado pelo frontend para decidir se deve redirecionar para o setup inicial.
    """
    inicializado = auth_service.verificar_sistema_inicializado(db)
    return StatusResponse(inicializado=inicializado)


# ===========================================================================
# SETUP INICIAL E RECONEXÃO (PÚBLICO)
# ===========================================================================

@router.post(
    "/reconnect",
    status_code=status.HTTP_200_OK,
    summary="Reconecta uma licença existente via API StartBig"
)
def reconnect_licenca_endpoint(
    reconnect_data: ReconnectRequest,
    db: Session = Depends(get_db),
):
    """
    Endpoint público para reconectar uma licença já existente na StartBig.
    Salva a licença localmente e retorna se o sistema já está inicializado.
    """
    from app.services import licenca as licenca_srv
    
    # Executa a reconexão
    _handle_db_transaction(
        db,
        licenca_srv.reconnect_licenca,
        reconnect_data.email,
        reconnect_data.senha,
    )
    
    # Verifica se o sistema (Empresa, Master) já foi inicializado
    inicializado = auth_service.verificar_sistema_inicializado(db)
    
    return {"success": True, "inicializado": inicializado}

@router.post(
    "/setup",
    status_code=status.HTTP_201_CREATED,
    summary="Setup inicial do sistema"
)
def setup_inicial(
    setup_data: SetupCreate,
    db: Session = Depends(get_db),
):
    """
    Endpoint público para o setup inicial do sistema.
    Cria atomicamente: Empresa + Endereço + Usuário Master + Cargo Master + Funcionário.
    Retorna JWT Bearer Token para login automático.
    """
    token_value = _handle_db_transaction(
        db,
        setup_service.setup_sistema,
        setup_data,
    )

    return {"access_token": token_value, "token_type": "bearer"}