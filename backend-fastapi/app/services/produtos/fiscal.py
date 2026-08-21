# ---------------------------------------------------------------------------
# ARQUIVO: app/services/produto_fiscal.py
# MÓDULO: Service Layer — Dados Fiscais de Produto
# DESCRIÇÃO: Regras de negócio para leitura e atualização de dados fiscais
#            de produtos. Camada 2 de validação (completude condicional).
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from typing import Optional

from .helpers import _validar_produto_existe

from app.db.crud.produtos import fiscal as fiscal_crud
from app.db.models.produto_fiscal import ProdutoFiscal

from app.schemas.produto_fiscal import ProdutoFiscalUpdate


def get_dados_fiscais(db: Session, produto_id: int) -> Optional[ProdutoFiscal]:
    """
    Retorna os dados fiscais de um produto.

    Raises:
        HTTPException 404: Se o produto não existir.
    """
    _validar_produto_existe(db, produto_id)
    return fiscal_crud.get_by_produto_id(db, produto_id)


def upsert_dados_fiscais(
    db: Session,
    produto_id: int,
    dados: ProdutoFiscalUpdate,
) -> ProdutoFiscal:
    """
    Cria ou atualiza os dados fiscais de um produto.

    Raises:
        HTTPException 404: Se o produto não existir.
    """
    _validar_produto_existe(db, produto_id)
    return fiscal_crud.upsert(db, produto_id, dados)
