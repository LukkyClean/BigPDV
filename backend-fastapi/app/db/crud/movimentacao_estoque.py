# ---------------------------------------------------------------------------
# ARQUIVO: crud/movimentacao_estoque.py
# DESCRIÇÃO: Operações de banco de dados para movimentações de estoque.
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from typing import Sequence, Optional

from app.db.models.movimentacao_estoque import MovimentacaoEstoque


def create_movimentacao(
    db: Session, movimentacao: MovimentacaoEstoque
) -> MovimentacaoEstoque:
    """Persiste uma nova movimentação de estoque."""
    db.add(movimentacao)
    db.flush()
    db.refresh(movimentacao)
    return movimentacao


def get_movimentacoes(
    db: Session,
    produto_id: Optional[int] = None,
    limit: int = 100
) -> Sequence[MovimentacaoEstoque]:
    """
    Lista movimentações, opcionalmente filtrando por produto.
    Retorna as mais recentes primeiro.
    """
    # joinedload do produto: a resposta expoe `unidade_medida`, lida do produto
    # (ver MovimentacaoEstoque.unidade_medida). Sem isto seria uma consulta por
    # linha -- ate 500 no limite maximo deste endpoint.
    stmt = (
        select(MovimentacaoEstoque)
        .options(joinedload(MovimentacaoEstoque.produto))
        .order_by(MovimentacaoEstoque.created_at.desc())
    )
    if produto_id is not None:
        stmt = stmt.where(MovimentacaoEstoque.produto_id == produto_id)
    stmt = stmt.limit(limit)
    return db.scalars(stmt).all()