# ---------------------------------------------------------------------------
# ARQUIVO: app/db/crud/produto_fiscal.py
# MÓDULO: Repository — Dados Fiscais de Produto
# DESCRIÇÃO: Operações de banco de dados para a tabela 'produto_fiscal'.
# ---------------------------------------------------------------------------

from typing import Optional
from sqlalchemy.orm import Session

from app.db.models.produto_fiscal import ProdutoFiscal
from app.schemas.produto_fiscal import ProdutoFiscalCreate, ProdutoFiscalUpdate


def get_by_produto_id(db: Session, produto_id: int) -> Optional[ProdutoFiscal]:
    """Retorna os dados fiscais de um produto, ou None se ainda não preenchidos."""
    return (
        db.query(ProdutoFiscal)
        .filter(ProdutoFiscal.produto_id == produto_id)
        .first()
    )


def create(db: Session, produto_id: int, dados: ProdutoFiscalCreate) -> ProdutoFiscal:
    """Cria um novo registro de dados fiscais para o produto."""
    registro = ProdutoFiscal(produto_id=produto_id, **dados.model_dump())
    db.add(registro)
    db.flush()
    db.refresh(registro)
    return registro


def update(db: Session, registro: ProdutoFiscal, dados: ProdutoFiscalUpdate) -> ProdutoFiscal:
    """Atualiza os dados fiscais de um produto existente."""
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(registro, campo, valor)
    db.flush()
    db.refresh(registro)
    return registro


def upsert(db: Session, produto_id: int, dados: ProdutoFiscalCreate | ProdutoFiscalUpdate) -> ProdutoFiscal:
    """
    Cria ou atualiza os dados fiscais de um produto.
    Simplifica o frontend: não precisa saber se o registro já existe.
    """
    registro = get_by_produto_id(db, produto_id)
    if registro is None:
        return create(db, produto_id, ProdutoFiscalCreate(**dados.model_dump()))
    return update(db, registro, ProdutoFiscalUpdate(**dados.model_dump()))
