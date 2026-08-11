import logging
from typing import Optional

import httpx

from ._constants import API_TIMEOUT
from .flow import CloudSyncError

logger = logging.getLogger(__name__)


def _client(timeout: httpx.Timeout) -> httpx.AsyncClient:
    # Fábrica isolada para os testes substituírem por um MockTransport.
    return httpx.AsyncClient(timeout=timeout)


def _get_license_token(db) -> Optional[str]:
    # Import local evita importação circular com app.db
    from app.db.crud import configuracao_licenca as license_crud
    license = license_crud.get_licenca(db)
    return license.token if license else None


async def _renew_license(db) -> None:
    # 401 → reusa a rotina de renovação que já existe no módulo de licença.
    from app.services.licenca import renovar_licenca_background
    await renovar_licenca_background(db)


def _safe_json(response: httpx.Response) -> dict:
    # Corpo JSON ou {} — evita que um corpo não-JSON vire segunda exceção.
    try:
        return response.json()
    except Exception:
        return {}


async def _request(db, method: str, url: str,
                   payload: Optional[dict] = None) -> httpx.Response:
    """
    Chamada autenticada com a política de 401: renova o token UMA vez e
    repete UMA vez. Qualquer outra resposta volta ao chamador para ser
    tratada pelo `codigo`. Falha de rede vira CloudSyncError sem code.
    """
    response: Optional[httpx.Response] = None
    for attempt in (1, 2):
        token = _get_license_token(db)
        if not token:
            raise CloudSyncError("Licença sem token válido - sync adiado.")
        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with _client(API_TIMEOUT) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                else:
                    response = await client.post(url, json=payload, headers=headers)
        except httpx.RequestError as e:
            raise CloudSyncError(f"Falha de rede em {url}: {e}") from e

        if response.status_code == 401 and attempt == 1:
            logger.info("[SYNC] 401 - renovando token e repetindo uma vez.")
            await _renew_license(db)
            continue
        return response
    return response
