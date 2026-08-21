# ---------------------------------------------------------------------------
# ARQUIVO: app/services/estoque/_errors.py
# DESCRIÇÃO: Exceções específicas do módulo de estoque.
# ---------------------------------------------------------------------------

from fastapi import HTTPException, status

not_found_exce = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Produto não encontrado no sistema"
)

bad_request_exce = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Estoque insuficiente para a quantidade solicitada"
)
