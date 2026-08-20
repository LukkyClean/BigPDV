# ---------------------------------------------------------------------------
# ARQUIVO: endpoints/funcionario.py
# MÓDULO: Interface de API (Controller)
# DESCRIÇÃO: Gerencia as rotas para operações de Funcionários e RH.
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends, status, Query, Path
from sqlalchemy.orm import Session
from typing import Sequence, Optional

from app.schemas.usuario import UsuarioCreate
from app.schemas.funcionario import FuncionarioCreate, FuncionarioRead, FuncionarioUpdate
from app.core.depends import check_permission, _handle_db_transaction
from app.db.session import get_db
from app.services import funcionario as funcionario_service

router = APIRouter()

# ===========================================================================
# ROTAS DE CRIAÇÃO (POST)
# ===========================================================================

@router.post(
    "/",
    response_model=FuncionarioRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar Funcionário",
    description="Cria Funcionário, Usuário de acesso e Endereços em uma única transação."
)
def create_funcionario(
    user_token: dict = Depends(check_permission(required_permission="funcionario")),
    *,
    funcionario_to_add: FuncionarioCreate,
    db: Session = Depends(get_db)
):
    """
    Endpoint de cadastro completo (Onboarding).
    Requer: Token de usuário com permissão de 'funcionario'.
    """
    return _handle_db_transaction(
        db, 
        funcionario_service.create_funcionario, 
        user_token["empresa_id"],
        funcionario_to_add
    )

# ===========================================================================
# ROTAS DE LEITURA (GET)
# ===========================================================================

@router.get(
    "/",
    response_model=Sequence[FuncionarioRead],
    status_code=status.HTTP_200_OK,
    summary="Listar ou Buscar Funcionários",
    description="Busca por termo (Nome, CPF, Email) ou retorna todos os ativos."
)
def get_funcionario_by_search(
    user_token: dict = Depends(check_permission(required_permission="funcionario")),
    *,
    buscar: Optional[str] = Query(
        None,
        description="Termo para filtro (Nome, CPF, RG, Email)."
    ),
    db: Session = Depends(get_db)
):
    return _handle_db_transaction(
        db, 
        funcionario_service.get_funcionario_by_search,
        buscar
    )

# ===========================================================================
# ROTAS DE ATUALIZAÇÃO (PUT)
# ===========================================================================

@router.put(
    "/{funcionario_id}",
    response_model=FuncionarioRead,
    status_code=status.HTTP_200_OK,
    summary="Atualizar Dados Cadastrais",
    description="Atualiza dados pessoais, documentos e endereços."
)
def update_funcionario_by_funcionario_id(
    user_token: dict = Depends(check_permission(required_permission="funcionario")),
    funcionario_id: int = Path(..., description="ID do funcionário", ge=1),
    *,
    funcionario_to_update: FuncionarioUpdate,
    db: Session = Depends(get_db)
):
    return _handle_db_transaction(
        db, 
        funcionario_service.update_funcionario_by_id, 
        funcionario_id, 
        funcionario_to_update
    )

@router.post(
    "/{funcionario_id}/acesso",
    response_model=FuncionarioRead,
    status_code=status.HTTP_201_CREATED,
    summary="Conceder Acesso ao Sistema",
    description=(
        "Cria o login de um funcionario cadastrado SEM acesso. "
        "Recusa (409) se ele ja tiver usuario — trocar credencial e outro assunto."
    ),
)
def conceder_acesso_funcionario(
    user_token: dict = Depends(check_permission(required_permission="funcionario")),
    funcionario_id: int = Path(..., description="ID do funcionário", ge=1),
    *,
    usuario_to_add: UsuarioCreate,
    db: Session = Depends(get_db)
):
    return _handle_db_transaction(
        db,
        funcionario_service.conceder_acesso,
        funcionario_id,
        usuario_to_add
    )

@router.put(
    "/toggle_ativo/{funcionario_id}",
    response_model=FuncionarioRead,
    status_code=status.HTTP_200_OK,
    summary="Ativar/Desativar Funcionário",
    description="Alterna status. Se desativado, bloqueia também o acesso do Usuário vinculado."
)
def active_funcionario_by_id(
    user_token: dict = Depends(check_permission(required_permission="funcionario")),
    funcionario_id: int = Path(..., description="ID do funcionário", ge=1),
    *,
    db: Session = Depends(get_db)
):
    return _handle_db_transaction(
        db, 
        funcionario_service.toggle_active_disable_funcionario_by_id, 
        funcionario_id
    )

@router.put(
    "/{funcionario_id}/cargo",
    response_model=FuncionarioRead,
    status_code=status.HTTP_200_OK,
    summary="Alterar Cargo",
    description="Vincula um novo cargo (perfil de permissões) ao funcionário."
)
def add_cargo_funcionario(
    user_token: dict = Depends(check_permission(required_permission="funcionario")),
    funcionario_id: int = Path(..., description="ID do funcionário", ge=1),
    cargo_id: int = Query(..., description="ID do novo cargo"),
    *,
    db: Session = Depends(get_db)
):
    return _handle_db_transaction(
        db,
        funcionario_service.update_cargo_funcionario,
        funcionario_id,
        cargo_id
    )