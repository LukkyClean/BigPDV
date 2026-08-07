from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.backup import DownloadChainResponse
from app.services.cloud_sync import download_chain

router = APIRouter()

@router.get(
    "/{ciclo}",
    response_model=DownloadChainResponse,
    status_code=status.HTTP_200_OK,
    summary="Baixa e restaura cadeia de backups da nuvem",
)
async def backup_download(
    db: Session = Depends(get_db),
    *,
    ciclo: str = Path(..., description="ID do ciclo de backup a ser baixado")
):
    return await download_chain(db, ciclo)