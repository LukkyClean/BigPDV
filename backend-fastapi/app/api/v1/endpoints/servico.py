# ---------------------------------------------------------------------------
# ARQUIVO: endpoints/servico.py
# MÓDULO: Interface de API (Controller)
# DESCRIÇÃO: Gerencia as ofertas de serviços (ex: Mão de obra, Consultoria).
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.orm import Session
from typing import Sequence, Optional

from app.core.depends import check_permission, requer_modulo_fiscal, _handle_db_transaction
from app.db.session import get_db
from app.schemas.servico import ServicoCreate, ServicoRead, ServicoFilterParams, ServicoQuery, ServicoUpdate, ServicoStats
from app.schemas.servico_fiscal import ServicoFiscalRead, ServicoFiscalUpdate
from app.services import servico as servico_service
from app.services import servico_fiscal as servico_fiscal_service

router = APIRouter()

# ===========================================================================
# ROTAS DE CRIAÇÃO (POST)
# ===========================================================================

@router.post(
    "/",
    response_model=ServicoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar Novo Serviço",
    description="Cria uma nova oferta de serviço no sistema."
)
def create_servico(
    user_token: dict = Depends(check_permission(required_permission="servico")),
    *,
    servico_to_add: ServicoCreate,
    db: Session = Depends(get_db)
):
    """
    Registra um novo serviço.
    
    Args:
        servico_to_add (ServicoCreate): Dados do serviço (Descrição, Valor, etc).
        db (Session): Sessão de banco de dados.

    Returns:
        ServicoRead: O serviço criado com ID gerado.
    """
    return _handle_db_transaction(
        db,
        servico_service.create_servico,
        servico_to_add
    )

# ===========================================================================
# ROTAS DE LEITURA (GET)
# ===========================================================================

@router.get(
    "/stats",
    response_model=ServicoStats,
    status_code=status.HTTP_200_OK,
    summary="Estatísticas dos Serviços",
    description="Retorna estatísticas agregadas dos serviços cadastrados."
)
def get_servico_stats(
    user_token: dict = Depends(check_permission(required_permission="servico")),
    *,
    db: Session = Depends(get_db)
):
    """Retorna total, ativos, inativos e ticket médio dos serviços."""
    return _handle_db_transaction(
        db,
        servico_service.get_servico_stats,
    )

@router.get(
    "/",
    response_model=ServicoQuery,
    status_code=status.HTTP_200_OK,
    summary="Listar ou Buscar Serviços",
    description="Retorna serviços ativos. Permite filtro por descrição."
)
def get_servico(
    user_token: dict = Depends(check_permission(required_permission="servico")),
    *,
    filters: ServicoFilterParams = Depends(),
    page: int = Query(
        1,
        ge=1,
        description="Termo de busca (Descrição do serviço)."
    ), 
    limit: int = Query(
        20,
        ge=0,
        description="Termo de busca (Descrição do serviço)."
    ),
    db: Session = Depends(get_db)
):
    """
    Busca serviços cadastrados.

    Args:
        buscar (str, optional): Texto para filtrar por descrição.
        db (Session): Sessão do banco.
    """
    filters = filters.model_dump(exclude_unset=True)
    return _handle_db_transaction(
        db,
        servico_service.get_servico_by_search,
        filters,
        page,
        limit
    )

# ===========================================================================
# ROTAS DE ATUALIZAÇÃO (PUT)
# ===========================================================================

@router.put(
    "/{servico_id}",
    response_model=ServicoRead,
    status_code=status.HTTP_200_OK,
    summary="Atualizar Serviço",
    description="Altera dados de um serviço existente."
)
def update_servico(
    user_token: dict = Depends(check_permission(required_permission="servico")),
    servico_id: int = Path(..., description="ID do serviço", ge=1),
    *,
    servico_to_update: ServicoUpdate,
    db: Session = Depends(get_db)
):
    """
    Atualiza atributos de um serviço.

    Args:
        servico_id (int): ID do serviço na URL.
        servico_to_update (ServicoUpdate): Payload com novos dados.
    """
    return _handle_db_transaction(
       db, 
       servico_service.update_servico_by_id,
       servico_id,
       servico_to_update
   )

# ===========================================================================
# ROTAS FISCAIS (GET / PUT)
# ===========================================================================

@router.get(
    "/{servico_id}/fiscal",
    response_model=ServicoFiscalRead,
    status_code=status.HTTP_200_OK,
    summary="Dados Fiscais do Serviço",
    description="Retorna os dados fiscais de um serviço. 404 se ainda não preenchidos.",
)
def get_dados_fiscais_servico(
    user_token: dict = Depends(check_permission(required_permission="servico")),
    _fiscal: dict = Depends(requer_modulo_fiscal),
    servico_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    resultado = servico_fiscal_service.get_dados_fiscais(db, servico_id)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Dados fiscais ainda não preenchidos para este serviço")
    return resultado


@router.put(
    "/{servico_id}/fiscal",
    response_model=ServicoFiscalRead,
    status_code=status.HTTP_200_OK,
    summary="Salvar Dados Fiscais do Serviço",
    description="Cria ou atualiza (upsert) os dados fiscais de um serviço.",
)
def upsert_dados_fiscais_servico(
    user_token: dict = Depends(check_permission(required_permission="servico")),
    _fiscal: dict = Depends(requer_modulo_fiscal),
    *,
    servico_id: int = Path(..., ge=1),
    dados: ServicoFiscalUpdate,
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(
        db,
        servico_fiscal_service.upsert_dados_fiscais,
        servico_id,
        dados,
    )


@router.put(
    "/toggle_ativo/{service_id}",
    response_model=ServicoRead,
    status_code=status.HTTP_200_OK,
    summary="Ativar/Desativar Serviço",
    description="Alterna o status lógico (Soft Delete)."
)
def toggle_status_servico(
    user_token: dict = Depends(check_permission(required_permission="servico")),
    service_id: int = Path(..., description="ID do serviço", ge=1),
    *,
    db: Session = Depends(get_db)
):
    """
    Ativa ou desativa um serviço.
    
    Nota: A função chamada foi ajustada para 'toggle_active_disable_servico_by_id'
    para manter a consistência com os outros módulos.
    """
    return _handle_db_transaction(
        db,
        servico_service.toggle_active_disable_servico_by_id,
        service_id
    )