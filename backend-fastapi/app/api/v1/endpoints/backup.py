# ---------------------------------------------------------------------------
# ARQUIVO: endpoints/backup.py
# DESCRICAO: Endpoints de backup em nuvem.
#
# ACESSO: EXCLUSIVO do Master -> Depends(get_current_master_user).
#   Baixar uma cadeia da nuvem prepara a substituicao do banco da loja. O
#   backend escuta em 0.0.0.0 e e alcancavel por qualquer terminal da LAN
#   (ver core/discovery.py), entao um endpoint sem autenticacao aqui deixaria
#   qualquer maquina da rede disparar a restauracao. A versao originada no
#   master nao tinha dependencia de auth; ela foi adicionada nesta branch.
# ---------------------------------------------------------------------------

from typing import Any, Dict

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.core.depends import get_current_master_user, get_db
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
    user_token: Dict[str, Any] = Depends(get_current_master_user),
    db: Session = Depends(get_db),
    *,
    ciclo: str = Path(..., description="ID do ciclo de backup a ser baixado"),
):
    return await download_chain(db, ciclo)
