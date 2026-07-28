# ---------------------------------------------------------------------------
# ARQUIVO: endpoints/venda.py
# DESCRICAO: Endpoints mockados para o módulo de Vendas (PDV).
#
# IMPORTANTE — Ordem de declaração das rotas:
#   Rotas com paths estáticos DEVEM ser declaradas ANTES de rotas com
#   path parameters, pois FastAPI resolve rotas em ordem de declaração.
#
# Estrutura de endpoints:
#   POST   /                              → Criar rascunho de venda
#   PATCH  /{venda_id}                    → Atualizar dados gerais da venda
#   POST   /{venda_id}/itens              → Adicionar item ao carrinho
#   PATCH  /{venda_id}/itens/{item_id}    → Editar item do carrinho
#   DELETE /{venda_id}/itens/{item_id}    → Remover item do carrinho
#   POST   /{venda_id}/cancelar           → Cancelar venda
#   POST   /{venda_id}/finalizar          → Finalizar venda (checkout)
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.depends import check_permission, get_db, _handle_db_transaction, is_visao_gerencial
from app.schemas.vendas import (
    ProdutosAlterSummary,
    FinalizarVendaPayload,
    CancelarVendaPayload,
    ReabrirVendaPayload,
    ProdutoVendaCreate,
    ProdutoVendaUpdate,
    VendaCreate,
    VendaListRead,
    VendaRead,
    VendaSearchFilters,
    VendaStatusSummary,
    VendaUpdate,
    VendaFinanceSummary
)

from app.services import venda as venda_service

router = APIRouter()

module_permission = ["venda", "view_sales", "manage_sales", "delete_sales"]

# ===========================================================================
# CRIAÇÃO (POST /)
# ===========================================================================

@router.post(
    "/",
    response_model=VendaRead,
    status_code=status.HTTP_201_CREATED,
    summary="Criar Rascunho de Venda",
    description=(
        "Cria uma nova venda no status RASCUNHO, gerando o ID identificador do carrinho para adição posterior de itens e pagamentos."
    ),
)
def criar_venda(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    db: Session = Depends(get_db),
    payload: VendaCreate,
):
    return _handle_db_transaction(
        db,
        venda_service.create_sale,
        payload
    )


# ===========================================================================
# ATUALIZAÇÃO GERAL (PATCH /{venda_id})
# ===========================================================================

@router.patch(
    "/{venda_id}",
    response_model=VendaRead,
    summary="Atualizar Dados Gerais da Venda",
    description=(
        "Permite vincular/alterar o cliente, aplicar descontos globais, "
        "registrar frete (entrega) ou valores de adiantamento."
    ),
)
def atualizar_venda(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    db: Session = Depends(get_db),
    venda_id: int = Path(..., description="ID da venda"),
    payload: VendaUpdate,
):
    return _handle_db_transaction(
        db,
        venda_service.update_sale,
        venda_id,
        payload
    )


# ===========================================================================
# ITENS DO CARRINHO
# ===========================================================================

@router.post(
    "/{venda_id}/itens",
    response_model=ProdutosAlterSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Adicionar Item ao Carrinho",
    description=(
        "Insere um produto (cadastrado ou avulso) na venda. "
        "Retorna o produto adicionado junto com o resumo financeiro atualizado."
    ),
)
def adicionar_item(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    db: Session = Depends(get_db),
    venda_id: int = Path(..., description="ID da venda"),
    payload: ProdutoVendaCreate,
):
    sale, product = _handle_db_transaction(
        db,
        venda_service.add_item_to_sale,
        venda_id,
        payload
    )
    return ProdutosAlterSummary(
        produto_adicionado=product,
        financeiro_atualizado=VendaFinanceSummary(
            subtotal=sale.subtotal or 0,
            descontos=sale.descontos or 0,
            entrega=sale.entrega or 0,
            total=sale.total or 0
        )
    )


@router.patch(
    "/{venda_id}/itens/{item_id}",
    response_model=ProdutosAlterSummary,
    summary="Editar Item do Carrinho",
    description=(
        "Altera propriedades de um produto já adicionado, como quantidade, "
        "desconto específico ou descrição de produtos avulsos."
    ),
)
def editar_item(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    db: Session = Depends(get_db),
    venda_id: int = Path(..., description="ID da venda"),
    item_id: int = Path(..., description="ID do item no carrinho"),
    payload: ProdutoVendaUpdate,
):
    sale, product = _handle_db_transaction(
        db,
        venda_service.update_item_in_sale,
        venda_id,
        item_id,
        payload
    )

    return ProdutosAlterSummary(
        produto_adicionado=product,
        financeiro_atualizado=VendaFinanceSummary(
            subtotal=sale.subtotal or 0,
            descontos=sale.descontos or 0,
            entrega=sale.entrega or 0,
            total=sale.total or 0
        )
    )


@router.delete(
    "/{venda_id}/itens/{item_id}",
    response_model=VendaRead,
    status_code=status.HTTP_200_OK,
    summary="Remover Item do Carrinho",
    description="Exclui o produto do rascunho da venda.",
)
def remover_item(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    db: Session = Depends(get_db),
    venda_id: int = Path(..., description="ID da venda"),
    item_id: int = Path(..., description="ID do item no carrinho"),
):
    return _handle_db_transaction(
        db,
        venda_service.remove_item_from_sale,
        venda_id,
        item_id
    )


# ===========================================================================
# AÇÕES DA VENDA (cancelar/ reabrir / finalizar)
# ===========================================================================

@router.delete(
    "/{venda_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Descartar Rascunho de Venda",
    description=(
        "Deleta permanentemente uma venda ATIVA que não foi finalizada. "
        "Use este endpoint para descartar rascunhos/carrinhos abandonados."
    ),
)
def descartar_venda(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    db: Session = Depends(get_db),
    venda_id: int = Path(..., description="ID da venda"),
):
    _handle_db_transaction(db, venda_service.delete_draft_sale, venda_id)


@router.post(
    "/{venda_id}/cancelar",
    response_model=VendaRead,
    status_code=status.HTTP_200_OK,
    summary="Cancelar Venda Finalizada",
    description=(
        "Reservado para cancelamento de vendas já finalizadas (devolução/estorno). "
        "Para descartar rascunhos use DELETE /{venda_id}."
    ),
)
def cancelar_venda(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    db: Session = Depends(get_db),
    venda_id: int = Path(..., description="ID da venda"),
    payload: CancelarVendaPayload,
):
    return _handle_db_transaction(
        db,
        venda_service.cancel_sale,
        venda_id,
        payload.motivo,
        payload.codigo_gerente,
    )

@router.post(
    "/{venda_id}/reabrir",
    response_model=VendaRead,
    summary="Reabrir Venda",
    description=(
        "Reverte o status de uma venda cancelada para RASCUNHO, permitindo que seja editada e finalizada posteriormente."
    ),
)
def reabrir_venda(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    db: Session = Depends(get_db),
    venda_id: int = Path(..., description="ID da venda"),
    payload: ReabrirVendaPayload = ReabrirVendaPayload(),
):
    return _handle_db_transaction(
        db,
        venda_service.reopen_sale,
        venda_id,
        payload.codigo_gerente,
    )   


@router.post(
    "/{venda_id}/finalizar",
    response_model=VendaRead,
    summary="Finalizar Venda (Checkout)",
    description=(
        "Recebe os pagamentos e valida se a soma cobre o total financeiro. "
        "Caso positivo, efetua a baixa de estoque e muda o status para CONCLUIDA."
    ),
)
def finalizar_venda(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    db: Session = Depends(get_db),
    venda_id: int = Path(..., description="ID da venda"),
    payload: FinalizarVendaPayload,
):
    return _handle_db_transaction(
        db,
        venda_service.finish_sale,
        venda_id,
        payload.pagamentos,
        payload.acrescimo or 0
    )

@router.get(
    "/",
    response_model=VendaListRead,
    summary="Listar Vendas",
    description=(
        "Retorna uma lista paginada de vendas, permitindo filtros por status e busca textual por cliente ou ID da venda."
    )
)
def listar_vendas(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100, description="Número máximo de vendas a retornar por página"),
    page: int = Query(1, ge=1, description="Número da página para paginação"),
    filters: VendaSearchFilters = Depends()
):
    if not is_visao_gerencial(user_token):
        filters.funcionario_id = user_token.get("funcionario_id")

    sales_in_db, total_sales, total_pages, links = venda_service.get_sales(
        db, filters=filters, page=page, limit=limit
    )

    return VendaListRead(
        filters=filters,
        vendas=sales_in_db,
        total=total_sales,
        page=page,
        limit=limit,
        total_pages=total_pages,
        links=links
    )

@router.get(
    "/{venda_id}",
    response_model=VendaRead,
    summary="Obter Detalhes da Venda",
    description=(
        "Retorna os detalhes completos de uma venda específica, incluindo itens, pagamentos e informações do cliente."
    )
)
def obter_detalhes_venda(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    db: Session = Depends(get_db),
    venda_id: int = Path(..., description="ID da venda"),
):
    return venda_service.get_sale_by_id(db, venda_id)

@router.get(
    "/status/",
    response_model=VendaStatusSummary,
    status_code=status.HTTP_200_OK,
    summary="Resumo de Status das Vendas",
    description=(
        "Fornece um resumo quantitativo das vendas no sistema"
    )
)
def resumo_status_vendas(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    db: Session = Depends(get_db),
):
    funcionario_id = None if is_visao_gerencial(user_token) else user_token.get("funcionario_id")
    return venda_service.get_sales_status(db, funcionario_id=funcionario_id)

    
