# ---------------------------------------------------------------------------
# ARQUIVO: endpoints/forma_pagamento.py
# DESCRICAO: Endpoints CRUD para o catálogo global de Formas de Pagamento.
#
# FormaPagamento é uma entidade de catálogo do sistema.
# É usada na finalização de OS para registrar como o cliente pagou.
# Exemplos: Dinheiro, PIX, Cartão de Crédito, Cartão de Débito, Cheque.
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends, status, Path, Response
from sqlalchemy.orm import Session
from typing import List

from app.core.depends import check_permission, _handle_db_transaction
from app.db.session import get_db
from app.db.models.forma_pagamento import FormaPagamento as FormaPagamentoModel
from app.db.crud import forma_pagamento as fp_crud
from app.schemas.forma_pagamento import FormaPagamentoCreate, FormaPagamentoUpdate, FormaPagamentoRead
from fastapi import HTTPException

router = APIRouter()

module_permission = ["servico", "venda", "view_sales", "manage_sales", "view_services", "manage_services"]


# ===========================================================================
# HELPERS INTERNOS
# ===========================================================================

def _get_fp_or_404(db: Session, fp_id: int) -> FormaPagamentoModel:
    """Busca forma de pagamento pelo ID ou lança 404."""
    fp = fp_crud.get_forma_pagamento_by_id(db, fp_id=fp_id)
    if not fp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Forma de pagamento não encontrada"
        )
    return fp


def _create_fp_service(db: Session, fp_data: FormaPagamentoCreate) -> FormaPagamentoModel:
    """
    Cria nova forma de pagamento.
    Valida unicidade do nome (case-insensitive) antes de persistir.
    """
    if fp_crud.get_forma_pagamento_by_nome(db, nome=fp_data.nome):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe uma forma de pagamento com o nome '{fp_data.nome}'"
        )
    fp_to_db = FormaPagamentoModel(
        nome=fp_data.nome,
        ativo=fp_data.ativo,
        dias_para_receber=fp_data.dias_para_receber,
        conta_bancaria_id=fp_data.conta_bancaria_id,
    )
    return fp_crud.create_forma_pagamento(db, fp_to_add=fp_to_db)


def _update_fp_service(db: Session, fp_id: int, fp_data: FormaPagamentoUpdate) -> FormaPagamentoModel:
    """
    Atualiza uma forma de pagamento.
    Valida unicidade do nome se o nome for alterado.
    """
    fp_in_db = _get_fp_or_404(db, fp_id)

    if fp_data.nome is not None and fp_data.nome.lower() != fp_in_db.nome.lower():
        if fp_crud.get_forma_pagamento_by_nome(db, nome=fp_data.nome):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Já existe uma forma de pagamento com o nome '{fp_data.nome}'"
            )
        fp_in_db.nome = fp_data.nome

    if fp_data.ativo is not None:
        fp_in_db.ativo = fp_data.ativo

    if fp_data.dias_para_receber is not None:
        fp_in_db.dias_para_receber = fp_data.dias_para_receber

    # ZERO SIGNIFICA "volta para a principal". `None` ja quer dizer "nao mexe"
    # num PATCH parcial, entao sobrou o zero para limpar -- sem ele nao haveria
    # como desfazer a escolha de uma conta depois de feita.
    if fp_data.conta_bancaria_id is not None:
        fp_in_db.conta_bancaria_id = fp_data.conta_bancaria_id or None

    return fp_crud.update_forma_pagamento(db, fp_to_update=fp_in_db)


def _delete_fp_service(db: Session, fp_id: int) -> None:
    """Desativa (soft delete) uma forma de pagamento."""
    fp_in_db = _get_fp_or_404(db, fp_id)
    fp_in_db.ativo = False
    fp_crud.update_forma_pagamento(db, fp_to_update=fp_in_db)


# ===========================================================================
# ROTAS
# ===========================================================================

@router.get(
    "/",
    response_model=List[FormaPagamentoRead],
    status_code=status.HTTP_200_OK,
    summary="Listar Formas de Pagamento",
    description="Retorna todas as formas de pagamento cadastradas (ativas e inativas)."
)
def get_formas_pagamento(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    db: Session = Depends(get_db)
):
    return fp_crud.get_formas_pagamento(db)


@router.post(
    "/",
    response_model=FormaPagamentoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Criar Forma de Pagamento",
    description="Cadastra uma nova forma de pagamento no catálogo do sistema."
)
def create_forma_pagamento(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    fp_data: FormaPagamentoCreate,
    db: Session = Depends(get_db)
):
    return _handle_db_transaction(db, _create_fp_service, fp_data)


@router.put(
    "/{fp_id}",
    response_model=FormaPagamentoRead,
    status_code=status.HTTP_200_OK,
    summary="Atualizar Forma de Pagamento",
    description="Atualiza nome e/ou status ativo de uma forma de pagamento."
)
def update_forma_pagamento(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    fp_id: int = Path(..., ge=1, description="ID da forma de pagamento"),
    *,
    fp_data: FormaPagamentoUpdate,
    db: Session = Depends(get_db)
):
    return _handle_db_transaction(db, _update_fp_service, fp_id, fp_data)


@router.delete(
    "/{fp_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desativar Forma de Pagamento",
    description="Desativa (soft delete) uma forma de pagamento. Não a remove fisicamente pois pode estar vinculada a pagamentos históricos."
)
def delete_forma_pagamento(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    fp_id: int = Path(..., ge=1, description="ID da forma de pagamento"),
    *,
    db: Session = Depends(get_db)
):
    _handle_db_transaction(db, _delete_fp_service, fp_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
