from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from typing import Optional

from app.db.models.produto_fotos import ProdutoFoto as ProdutoFotoModel

# ===========================================================================
# ENTIDADE: FOTO DO PRODUTO
# ===========================================================================

def get_produto_image_by_id(db: Session, image_id: int) -> Optional[ProdutoFotoModel]:
    """Busca uma foto específica do produto pelo seu ID."""
    stmt = select(ProdutoFotoModel).where(ProdutoFotoModel.id == image_id)
    return db.scalar(stmt)


def get_produto_principal_image(db: Session, produto_id: int) -> Optional[ProdutoFotoModel]:
    """Busca a foto marcada como principal para um determinado produto."""
    stmt = select(ProdutoFotoModel).where(
        and_(
            ProdutoFotoModel.produto_id == produto_id,
            ProdutoFotoModel.principal == True
        )
    )
    return db.scalar(stmt)


def create_produto_image(db: Session, image_to_add: ProdutoFotoModel) -> ProdutoFotoModel:
    """Adiciona e persiste uma nova foto vinculada a um produto."""
    db.add(image_to_add)
    db.flush()
    db.refresh(image_to_add)
    return image_to_add


def delete_produto_image(db: Session, image_to_delete: ProdutoFotoModel) -> ProdutoFotoModel:
    """Remove uma foto de produto do banco de dados."""
    db.delete(image_to_delete)
    db.flush()
    return image_to_delete