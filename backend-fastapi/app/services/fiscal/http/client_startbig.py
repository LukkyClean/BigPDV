# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/http/client_startbig.py
# DESCRIÇÃO: Client real que chama a API Online StartBig para emissão fiscal.
# ---------------------------------------------------------------------------

import logging
import httpx
from typing import Optional

from .client import EmissaoResultado

logger = logging.getLogger(__name__)

class FiscalClientStartBig:
    """
    Client que se comunica com a API Online StartBig para emissão fiscal.
    """

    def __init__(self, ambiente: int = 1, token: str = ""):
        self.ambiente = ambiente
        self.token = token
        self.base_url = "https://api.startbig.com.br"

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def _parse_response(self, response_data: dict) -> EmissaoResultado:
        """Converte a resposta padrão da API para EmissaoResultado."""
        mensagem = response_data.get("mensagem_sefaz")
        if not mensagem:
            msg_api = response_data.get("message")
            if isinstance(msg_api, list):
                mensagem = " | ".join(str(m) for m in msg_api)
            elif msg_api:
                mensagem = str(msg_api)
            else:
                mensagem = "Erro desconhecido"

        return {
            "status": response_data.get("status", "erro"),
            "chave_acesso": response_data.get("chave_acesso"),
            "protocolo": response_data.get("protocolo"),
            "numero": response_data.get("numero"),
            "serie": response_data.get("serie"),
            "url_pdf": response_data.get("url_pdf"),
            "url_xml": response_data.get("url_xml"),
            "codigo_sefaz": response_data.get("codigo_sefaz"),
            "mensagem_sefaz": mensagem
        }

    def emitir_nfe(self, ref: str, payload: dict) -> EmissaoResultado:
        url = f"{self.base_url}/erp/fiscal/nfe/emitir"
        body = {
            "ref": ref,
            "payload": payload
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=body, headers=self.headers)
                response.raise_for_status()
                return self._parse_response(response.json())
        except httpx.HTTPStatusError as exc:
            logger.error("[FISCAL] Erro HTTP ao emitir NF-e: %s - %s", exc.response.status_code, exc.response.text)
            try:
                data = exc.response.json()
                return self._parse_response(data)
            except Exception:
                return {"status": "erro", "mensagem_sefaz": f"Erro {exc.response.status_code} da API"}
        except Exception as exc:
            logger.error("[FISCAL] Falha na requisição de emissão: %s", exc)
            return {"status": "erro", "mensagem_sefaz": str(exc)}

    def consultar_nfe(self, ref: str) -> EmissaoResultado:
        url = f"{self.base_url}/erp/fiscal/nfe/consultar"
        params = {"ref": ref}
        
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(url, params=params, headers=self.headers)
                response.raise_for_status()
                return self._parse_response(response.json())
        except httpx.HTTPStatusError as exc:
            logger.error("[FISCAL] Erro HTTP ao consultar NF-e: %s", exc.response.status_code)
            try:
                return self._parse_response(exc.response.json())
            except Exception:
                return {"status": "erro", "mensagem_sefaz": f"Erro {exc.response.status_code} da API"}
        except Exception as exc:
            logger.error("[FISCAL] Falha na requisição de consulta: %s", exc)
            return {"status": "erro", "mensagem_sefaz": str(exc)}

    def cancelar_nfe(self, ref: str, justificativa: str) -> EmissaoResultado:
        url = f"{self.base_url}/erp/fiscal/nfe/cancelar"
        body = {
            "ref": ref,
            "justificativa": justificativa
        }
        
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.post(url, json=body, headers=self.headers)
                response.raise_for_status()
                return self._parse_response(response.json())
        except httpx.HTTPStatusError as exc:
            logger.error("[FISCAL] Erro HTTP ao cancelar NF-e: %s", exc.response.status_code)
            try:
                return self._parse_response(exc.response.json())
            except Exception:
                return {"status": "erro", "mensagem_sefaz": f"Erro {exc.response.status_code} da API"}
        except Exception as exc:
            logger.error("[FISCAL] Falha na requisição de cancelamento: %s", exc)
            return {"status": "erro", "mensagem_sefaz": str(exc)}
