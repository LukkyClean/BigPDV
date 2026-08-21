from fastapi import HTTPException, status

from sqlalchemy.orm import Session
from app.db.crud.produtos import produto as produto_crud

# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _validar_produto_existe(db: Session, produto_id: int) -> None:
    """
    Garante que o produto existe.

    Raises:
        HTTPException 404: Se o produto não existir.
    """
    if produto_crud.get_produto_by_id(db, produto_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Produto {produto_id} não encontrado.",
        )