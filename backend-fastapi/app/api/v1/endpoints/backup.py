from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.cloud_sync import download_chain

router = APIRouter()

@router.get(
    "/{ciclo}",
    status_code=status.HTTP_200_OK,
    summary="Inicia o backup manual do banco de dados",
)
async def backup_download(
    db: Session = Depends(get_db),
    *,
    ciclo: str = Path(..., description="ID do backup a ser baixado")
):
    backup_download = await download_chain(db, ciclo)
    return backup_download