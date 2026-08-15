# ---------------------------------------------------------------------------
# ARQUIVO: endpoints/sessao_caixa.py
# DESCRIÇÃO: Endpoints do turno de caixa (abrir, suprir, sangrar, fechar).
# ---------------------------------------------------------------------------

from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.depends import _handle_db_transaction, check_permission
from app.db.session import get_db
from app.schemas.sessao_caixa import (
    MovimentoCaixaCreate,
    SessaoCaixaAbrir,
    SessaoCaixaFechar,
    SessaoCaixaRead,
    SessaoCaixaResumo,
)
from app.services import sessao_caixa as caixa_service

router = APIRouter()

# A permissão é a de vendas: quem opera o caixa é quem vende. Criar uma
# permissão nova obrigaria o lojista a revisar todos os cargos só para o caixa
# aparecer — e ele já decidiu quem pode vender.
PERMISSAO = "view_sales"


@router.get(
    "/atual",
    response_model=Optional[SessaoCaixaResumo],
    status_code=status.HTTP_200_OK,
    summary="Turno aberto do operador logado (null se não houver)",
)
def get_sessao_atual(
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO)),
    db: Session = Depends(get_db),
):
    """Devolve `null` em vez de 404 quando não há turno aberto.

    A tela pergunta isto o tempo todo para saber se mostra "abrir caixa" ou o
    resumo; "não há caixa aberto" é resposta normal, não erro.
    """
    return _handle_db_transaction(db, caixa_service.get_sessao_atual, usuario_token)


@router.post(
    "/abrir",
    response_model=SessaoCaixaResumo,
    status_code=status.HTTP_201_CREATED,
    summary="Abre o turno com o troco inicial",
)
def abrir_caixa(
    dados: SessaoCaixaAbrir,
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO)),
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(db, caixa_service.abrir_caixa, dados, usuario_token)


@router.post(
    "/suprimento",
    response_model=SessaoCaixaResumo,
    status_code=status.HTTP_201_CREATED,
    summary="Registra entrada de dinheiro que não é venda",
)
def registrar_suprimento(
    dados: MovimentoCaixaCreate,
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO)),
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(db, caixa_service.registrar_suprimento, dados, usuario_token)


@router.post(
    "/sangria",
    response_model=SessaoCaixaResumo,
    status_code=status.HTTP_201_CREATED,
    summary="Registra retirada de dinheiro que não é venda",
)
def registrar_sangria(
    dados: MovimentoCaixaCreate,
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO)),
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(db, caixa_service.registrar_sangria, dados, usuario_token)


@router.post(
    "/fechar",
    response_model=SessaoCaixaResumo,
    status_code=status.HTTP_200_OK,
    summary="Fecha o turno conferindo o dinheiro contado",
)
def fechar_caixa(
    dados: SessaoCaixaFechar,
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO)),
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(db, caixa_service.fechar_caixa, dados, usuario_token)


@router.get(
    "/",
    response_model=List[SessaoCaixaRead],
    status_code=status.HTTP_200_OK,
    summary="Histórico de turnos da empresa",
)
def listar_sessoes(
    limit: int = Query(50, ge=1, le=200),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO)),
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(db, caixa_service.listar_sessoes, usuario_token, limit)


@router.get(
    "/{sessao_id}",
    response_model=SessaoCaixaResumo,
    status_code=status.HTTP_200_OK,
    summary="Resumo de um turno específico",
)
def get_resumo(
    sessao_id: int = Path(..., ge=1),
    usuario_token: dict = Depends(check_permission(required_permission=PERMISSAO)),
    db: Session = Depends(get_db),
):
    return _handle_db_transaction(db, caixa_service.get_resumo_de_sessao, sessao_id, usuario_token)
