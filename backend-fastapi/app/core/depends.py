# ---------------------------------------------------------------------------
# ARQUIVO: app/core/depends.py
# DESCRIÇÃO: Dependências (Middlewares) para proteção de rotas.
# ---------------------------------------------------------------------------

import logging
from typing import Callable, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.core.security import verify_token_data
from app.services import usuario as usuario
from app.db.crud import token as token_crud
from app.db.crud import configuracao_licenca as licenca_crud
from app.db.session import get_db
from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def data_token_validation(db: Session, usuario_token: Dict[str, Any]) -> Dict[str, Any]:
    """
    Busca os dados mais recentes do usuário no banco (re-hidratação) e atualiza o payload.
    
    Isso previne que um token tenha informações desatualizadas (e.g., status 'ativo' mudou).

    Args:
        db (Session): Sessão de banco de dados.
        usuario_token (Dict[str, Any]): O payload decodificado do token (contém 'sub').

    Raises:
        HTTPException 403 FORBIDDEN: Se o usuário (sub) não for encontrado no banco.

    Returns:
        Dict[str, Any]: O payload do token atualizado com dados recentes do ORM.
    """
    try:
        # Busca o usuário no banco para obter os dados mais atuais
        usuario_in_db = usuario.get_usuario_by_id(
            db, 
            usuario_id=int(usuario_token["sub"])
        )
    except HTTPException as http_exce:
        # Erro 404 do service (Usuário não encontrado) é transformado em 403 (Token Inválido)
        # REGRA 4 aplicada: Mais específico, não printa exceção de segurança no console de prod
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token inválido. Usuário associado ao token não existe ou está inativo."
        )
    
    # REGRA 4 aplicada: O token é atualizado com dados de permissão/status frescos
    usuario_token["ativo"] = usuario_in_db.ativo
    usuario_token["is_master"] = usuario_in_db.is_master
    usuario_token["empresa_id"] = usuario_in_db.empresa_id
    usuario_token["nome"] = (
        usuario_in_db.funcionario.nome
        if usuario_in_db.funcionario
        else usuario_in_db.nome
    )
    
    # Pega o funcionario_id e permissões do cargo
    if usuario_in_db.funcionario:
        usuario_token["funcionario_id"] = usuario_in_db.funcionario.id
        if usuario_in_db.funcionario.cargo:
            usuario_token["permissoes"] = usuario_in_db.funcionario.cargo.permissoes or {}
            usuario_token["cargo"] = usuario_in_db.funcionario.cargo.nome
        else:
            usuario_token["permissoes"] = {}
            usuario_token["cargo"] = "Sem Cargo"
    else:
        usuario_token["funcionario_id"] = None
        usuario_token["permissoes"] = {}
        usuario_token["cargo"] = "Sem Cargo" # Define um valor padrão

    return usuario_token
    
    
# =========================
# 1. Validação Técnica (Assinatura e Blocklist)
# =========================
def get_token(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> Dict[str, Any]:
    """
    Dependência principal: Decodifica o token, valida a assinatura e verifica a blocklist.

    Args:
        db (Session): Sessão de banco de dados.
        token (str): O token JWT extraído do cabeçalho 'Authorization: Bearer'.

    Raises:
        HTTPException 401 UNAUTHORIZED: Se a assinatura for inválida ou o token tiver sido revogado.

    Returns:
        Dict[str, Any]: O payload decodificado e validado do token.
    """

    # Valida assinatura e decodifica. Se falhar, levanta 401.
    token_data = verify_token_data(token)

    # Valida Blocklist (Logout)
    if token_crud.get_revoke_token(db, token_data.get("jti")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão encerrada ou token inválido. Faça login novamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Re-hidrata e atualiza o payload com dados frescos do banco
    return data_token_validation(db, usuario_token=token_data)

# =========================
# 1.5. Validação de Licença (Bloqueio Remoto)
# =========================
def verificar_licenca_bloqueada(db: Session = Depends(get_db)) -> None:
    """
    Verifica se a licença foi bloqueada remotamente via heartbeat.
    Executada em toda requisição autenticada.

    Raises:
        HTTPException 403: Se a licença estiver bloqueada.
    """
    licenca = licenca_crud.get_licenca(db)
    if licenca and licenca.bloqueada:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "codigo": "LICENCA_BLOQUEADA",
                "mensagem": "Licença bloqueada. Conexão encerrada pelo servidor.",
            },
        )


# =========================
# 2. Validação de Negócio (Ativo?)
# =========================
def get_current_user(
    usuario_token: Dict[str, Any] = Depends(get_token),
    _licenca: None = Depends(verificar_licenca_bloqueada),
) -> Dict[str, Any]:
    """
    Garante que o usuário está ativo no sistema.

    Args:
        usuario_token (Dict[str, Any]): O payload do token validado.

    Raises:
        HTTPException 403 FORBIDDEN: Se o status 'ativo' for False.

    Returns:
        Dict[str, Any]: O payload do token, confirmando o usuário ativo.
    """
    # Checagem estrita de Booleano (REGRA 4: Robustez)
    if usuario_token.get("ativo") is not True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo. Acesso negado."
        )
    return usuario_token

# Alias para clareza
def get_current_active_user(usuario_token: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Retorna o usuário ativo (Alias)."""
    return usuario_token

def get_current_master_user(usuario_token: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Garante que o usuário ativo possui o papel de Master.

    Args:
        usuario_token (Dict[str, Any]): O payload do token validado.

    Raises:
        HTTPException 403 FORBIDDEN: Se 'is_master' for False.

    Returns:
        Dict[str, Any]: O payload do token, confirmando o usuário Master.
    """
    # Checagem estrita de Booleano (REGRA 4: Robustez)
    if usuario_token.get("is_master") is not True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Acesso exclusivo para Master."
        )
    return usuario_token

# =========================
# 3. Validação de Autorização (Permissões)
# =========================
def check_permission(required_permission: str | list[str]) -> Callable:
    """
    Factory de dependência para verificar permissões finas (Baseado em Claims/ACL).
    
    Args:
        required_permission (str): A string da permissão necessária (ex: 'produto_write').

    Returns:
        Callable: A função de dependência que executa a verificação.
    """
    
    def permission_dependency(usuario_token: Dict[str, Any] = Depends(get_current_active_user)):
        """
        Função de dependência que verifica o Tenant e a Permissão específica.
        """
        
        # 3.1 Validação de Tenant (Empresa)
        if not usuario_token.get("empresa_id"):
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário sem empresa vinculada (Tenant). Acesso negado."
            )

        # 3.2 Superusuário (Master) passa direto
        if usuario_token.get("is_master") is True:
            return usuario_token

        # 3.3 Validação de Cargo
        if usuario_token.get("cargo") == "Sem Cargo":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Funcionário ainda não possui cargo para obter permissões."
            )
        
        # 3.4 Validação da Permissão Fina
        # A re-hidratação já garante que 'permissoes' é um dict, mas esta é uma checagem de segurança
        permissoes = usuario_token.get("permissoes", {})
        
        if permissoes.get("all", False):
            return usuario_token
        
        perms = required_permission if isinstance(required_permission, list) else [required_permission]
        if any(permissoes.get(p) is True for p in perms):
            return usuario_token

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permissão negada. Requer: '{', '.join(perms)}'"
        )
    
    return permission_dependency

# =========================
# 4. Validação de Módulo Fiscal
# =========================
def requer_modulo_fiscal(
    usuario_token: Dict[str, Any] = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Garante que a empresa do usuário possui o módulo fiscal ativo.
    A presença de EmpresaFiscalSettings é o indicador canônico de ativação.

    Raises:
        HTTPException 403: Se o módulo fiscal não estiver ativado para a empresa.

    Returns:
        Dict[str, Any]: O payload do token (passthrough para encadeamento de depends).
    """
    empresa_id = usuario_token.get("empresa_id")
    if not empresa_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário sem empresa vinculada. Acesso negado.",
        )

    fiscal_settings = (
        db.query(EmpresaFiscalSettings)
        .filter(EmpresaFiscalSettings.empresa_id == empresa_id)
        .first()
    )
    if not fiscal_settings:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "codigo": "MODULO_FISCAL_INATIVO",
                "mensagem": "Módulo fiscal não ativado para esta empresa.",
            },
        )

    return usuario_token


_CARGOS_GERENCIAIS = {"gerente", "administrador"}

def is_visao_gerencial(user_token: dict) -> bool:
    """Retorna True se o usuário pode ver dados de toda a empresa (master ou cargo gerencial)."""
    if user_token.get("is_master"):
        return True
    cargo = (user_token.get("cargo") or "").lower()
    return any(c in cargo for c in _CARGOS_GERENCIAIS)


# =========================
# Função Utilitária: Gerenciador de Transação (Core)
# =========================

def _handle_db_transaction(db: Session, func: Callable, *args, **kwargs):
    """
    Executa a lógica de serviço, gerencia o commit/rollback e trata as exceções.

    Args:
        db (Session): Sessão do banco de dados (injetada).
        func (Callable): A função de serviço a ser executada.
        *args, **kwargs: Argumentos a serem passados para a função de serviço.
    
    Retorno: O resultado da função de serviço.
    """
    try:
        # 1. Executa o serviço (onde ocorre a lógica de negócio e manipulação do ORM)
        result = func(db, *args, **kwargs)
        # 2. Se o serviço for bem-sucedido, commita a transação
        db.commit()
        return result
    except HTTPException as http_exce:
        # 3. Trata erros de negócio controlados (404, 409, 403)
        logger.warning("Erro de negócio: %s", http_exce.detail)
        db.rollback()
        raise http_exce
    except ValueError as e:
        # 4. Captura erros de validação de negócio (lançados por serviços)
        logger.warning("Erro de validação: %s", e)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        # 5. Trata erros inesperados (internos)
        logger.exception("Erro inesperado: %s", e)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocorreu um erro interno no servidor."
        )