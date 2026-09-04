from fastapi import HTTPException, status

not_found_exce = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Serviço não encontrado no sistema"
)

conflict_exce = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="Serviço já cadastrado no sistema"
)