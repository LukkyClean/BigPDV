from fastapi import HTTPException, status

conflict_codigo_produto_exce = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail={
        "campo": "codigo_produto",
        "mensagem": "Código de produto já cadastrado no sistema"
    }
)

not_found_exce = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Produto não encontrado no sistema"
)

internal_error_exce = HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail="Erro em cumprir a requisição. Tente novamente mais tarde."
)

bad_request_exce = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Estoque insuficiente para a quantidade solicitada"
)