import asyncio
import logging
import os
from typing import Optional

import httpx

from app.schemas.backup import CloudPlanResponse, DownloadChainResponse

from ._constants import API_BACKUP_DOWNLOAD, GET_TIMEOUT
from ._http import _client, _request, _safe_json
from .flow import CloudSyncError

logger = logging.getLogger(__name__)


async def get_cloud_plan(db, cycle: str) -> CloudPlanResponse:
    # Import local — evita ciclo: download → core.hwid → (chain)
    from app.core.hwid import obter_hwid

    payload = {"hwid": obter_hwid()}
    if cycle:
        payload["ciclo"] = cycle

    response = await _request(db, "POST", API_BACKUP_DOWNLOAD, payload=payload)

    if response.status_code == 404:
        body = _safe_json(response)
        if body.get("codigo") == "BACKUP_INEXISTENTE" and not cycle:
            # §5b: nada NESTE ciclo, mas pode haver em ciclo anterior.
            return CloudPlanResponse(
                status="needs_explicit_cycle",
                code="BACKUP_INEXISTENTE",
                details="Ciclo corrente vazio; reconsultar com ciclo explícito.",
            )
        raise CloudSyncError(
            f"url-download 404: {body.get('codigo')}",
            code=body.get("codigo"), http_status=404,
        )
    if response.status_code >= 400:
        body = _safe_json(response)
        raise CloudSyncError(
            f"url-download falhou ({response.status_code}): {body.get('codigo')}",
            code=body.get("codigo"), http_status=response.status_code,
        )

    return CloudPlanResponse(status="ok", plan=response.json())


async def download_chain(db, cycle: Optional[str] = None) -> DownloadChainResponse:
    # Import local — evita ciclo: download ↔ backup
    from app.services import backup as backup_service

    planned = await get_cloud_plan(db, cycle)

    if planned.status == "needs_explicit_cycle":
        return DownloadChainResponse(status="needs_explicit_cycle", details=planned.details)

    plan = planned.plan
    files = plan.get("arquivos", [])
    resolved_cycle = plan.get("ciclo") or cycle

    if not files:
        return DownloadChainResponse(
            status="no_files",
            details="Nenhum backup disponível na nuvem para este ciclo.",
            ciclo=resolved_cycle,
        )

    ordered_files: list[str] = []

    async with _client(GET_TIMEOUT) as client:
        for fileinfo in files:
            url = fileinfo.get("url")
            chave = fileinfo.get("chave", "")
            filename = os.path.basename(chave) or fileinfo.get("arquivo", "")

            try:
                download_response = await client.get(url)
            except httpx.RequestError as e:
                raise CloudSyncError(f"Falha de rede no GET para {url}: {e}") from e

            if download_response.status_code != 200:
                raise CloudSyncError(
                    f"Download de {filename} falhou ({download_response.status_code}).",
                    http_status=download_response.status_code,
                )

            await asyncio.to_thread(backup_service.save_backup, cycle, filename, download_response.content)
            ordered_files.append(filename)

    await asyncio.to_thread(backup_service.restore_from_chain, cycle, ordered_files)
    return DownloadChainResponse(
        status="success",
        ciclo=resolved_cycle,
        ordered_files=ordered_files,
        restaura_ate=plan.get("restauraAte"),
        cadeia_completa=plan.get("cadeiaCompleta", False),
        indisponiveis=plan.get("indisponiveis", []),
        total_bytes=plan.get("totalBytes"),
    )
