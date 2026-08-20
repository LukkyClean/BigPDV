# ---------------------------------------------------------------------------
# ARQUIVO: app/services/auth_service.py
# DESCRIÇÃO: Lógica de Login e Logout, geração e revogação de tokens.
# ---------------------------------------------------------------------------

from typing import Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.schemas.auth import UsuarioLogin
from app.core.security import verify_password, create_access_token
from app.services import usuario as usuario_service
from app.services import licenca as licenca_service
from app.services import terminal as terminal_service
from app.db.crud import token as token_crud
from app.db.crud import usuario as usuario_crud
from app.db.models.token import TokenBlocklist

# ---------------------------------------------------------------------------
# EXCEÇÃO PADRONIZADA
# ---------------------------------------------------------------------------

UNAUTHORIZED_EXCE = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Email ou senha incorretos",
    headers={"WWW-Authenticate": "Bearer"},
)

# ---------------------------------------------------------------------------
# FUNÇÕES DE SERVIÇO
# ---------------------------------------------------------------------------

def login(db: Session, login_usuario: UsuarioLogin) -> Dict[str, Any]:
    """
    Autentica o usuário, verifica a senha e gera o token de acesso (JWT).

    Args:
        db (Session): Sessão do banco de dados.
        login_usuario (UsuarioLogin): DTO com email e senha em texto plano.

    Raises:
        HTTPException 401 UNAUTHORIZED: Se o e-mail ou a senha estiverem incorretos.

    Returns:
        Dict[str, Any]: Dicionário contendo o access_token, token_type e expires_in.
    """
    # 1. Busca Usuário
    usuario_in_db = usuario_service.get_usuario_by_email(db, login_usuario.email)

    # 2. Validação de Credenciais
    if not usuario_in_db or not verify_password(login_usuario.senha, usuario_in_db.senha_hash):
        raise UNAUTHORIZED_EXCE

    # 3. Conectar terminal à licença (valida limite na API StartBig)
    licenca_service.conectar_terminal(db, login_usuario.hwid)

    # 3.1 Cadastro DURÁVEL da máquina.
    #
    # A linha acima marca PRESENÇA e some no logout; esta cria o registro que
    # sobrevive, para o nome e o papel do terminal não evaporarem todo dia.
    #
    # DENTRO DE UM SAVEPOINT, e isso não é detalhe. Nada aqui vale mais do que o
    # login funcionar — quem chega para trabalhar às 8h não pode ficar de fora
    # porque o cadastro de uma máquina não gravou. Mas um `try/except` simples
    # não bastaria: capturar o erro sem desfazer deixa a sessão do SQLAlchemy
    # envenenada, e quem quebra é o COMMIT do login, alguns passos depois. O
    # savepoint desfaz só esta parte e o login segue.
    #
    # Sem o cadastro, a máquina se comporta como caixa — que é o lado seguro.
    empresa_id = getattr(usuario_in_db, "empresa_id", None)
    if empresa_id:
        try:
            with db.begin_nested():
                terminal_service.garantir_terminal(db, empresa_id, login_usuario.hwid)
        except Exception:  # noqa: BLE001 — cadastro de máquina não derruba login
            pass

    # 4. Criação do Payload (Claims)
    token_data = {
        "sub": str(usuario_in_db.id),
    }

    # 5. Geração do Token
    access_token = create_access_token(data=token_data)

    return access_token

def logout_service(db: Session, token: Dict[str, Any]) -> None:
    """
    Revoga o token JWT, adicionando seu JTI (ID) à Blocklist.

    Args:
        db (Session): Sessão do banco de dados.
        token (Dict[str, Any]): O payload decodificado do token, contendo 'jti' (ID) e 'exp' (expiração).

    Returns:
        None: A operação é concluída ou falha silenciosamente.
    """
    jti = token.get("jti")
    exp = token.get("exp")
    
    if jti and exp:
        # Converte o timestamp de expiração (UTC) para datetime
        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
        
        # Cria o modelo para persistência
        revoke_token = TokenBlocklist(jti=jti, exp=exp_datetime)
        
        # Persiste a revogação (o CRUD deve fazer o flush/commit)
        token_crud.create_revoke_token(db, revoke_token)


def verificar_sistema_inicializado(db: Session) -> bool:
    """
    Verifica se o sistema foi inicializado checando a existência de um usuário Master.

    Args:
        db (Session): Sessão do banco de dados.

    Returns:
        bool: True se o sistema foi inicializado, False caso contrário.
    """
    master = usuario_crud.get_usuario_master(db)
    return master is not None