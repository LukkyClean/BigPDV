import asyncio
import logging
import os
from typing import Any, Dict

import httpx

from ._constants import PUT_TIMEOUT
from ._http import _client, _request, _safe_json
from .flow import CloudSyncError

logger = logging.getLogger(__name__)


async def get_url_upload(db, payload: Dict[str, Any]) -> Dict[str, Any]:
    from ._constants import API_BACKUP_URL_UPLOAD
    response = await _request(db, "POST", API_BACKUP_URL_UPLOAD, payload)
    if response.status_code >= 400:
        body = _safe_json(response)
        raise CloudSyncError(
            f"url-upload recusado ({response.status_code}): {body.get('codigo')}",
            code=body.get("codigo"), http_status=response.status_code,
        )
    return response.json()


def _read_zip(filepath: str) -> bytes:
    """
    Lê o zip INTEIRO em memória — deliberado. Streaming (data=open) ativa
    chunked encoding e omite o Content-Length, que está DENTRO da assinatura
    da presigned URL → 403 SignatureDoesNotMatch. f.read() garante o header.
    """
    if not os.path.exists(filepath):
        raise CloudSyncError(f"Arquivo de backup não encontrado: {filepath}")
    with open(filepath, "rb") as f:
        return f.read()


async def send_zip_to_cloud(url: str, headers: Dict[str, str], filepath: str) -> None:
    # Leitura de disco pesada roda em thread para não travar o event loop.
    content = await asyncio.to_thread(_read_zip, filepath)
    try:
        async with _client(PUT_TIMEOUT) as client:
            response = await client.put(url, headers=headers, content=content)
    except httpx.RequestError as e:
        raise CloudSyncError(f"Falha de rede no PUT para {url}: {e}") from e
    if response.status_code != 200:
        raise CloudSyncError(
            f"PUT ao R2 falhou ({response.status_code}): {response.text[:200]}",
            http_status=response.status_code,
        )


async def confirm_upload(db, payload: Dict[str, Any]) -> Dict[str, Any]:
    from ._constants import API_BACKUP_CONFIRMAR
    response = await _request(db, "POST", API_BACKUP_CONFIRMAR, payload)
    if response.status_code >= 400:
        body = _safe_json(response)
        raise CloudSyncError(
            f"confirmar recusado ({response.status_code}): {body.get('codigo')}",
            code=body.get("codigo"), http_status=response.status_code,
        )
    return response.json()
