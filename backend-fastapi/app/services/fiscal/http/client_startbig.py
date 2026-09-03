# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/http/client_startbig.py
# DESCRIÇÃO: Client real que chama a API Online StartBig para emissão fiscal.
# ---------------------------------------------------------------------------

import logging
import httpx
from typing import Optional

from .client import EmissaoResultado

logger = logging.getLogger(__name__)

# Chaves cujo valor nunca pode ir para o log em disco do cliente.
_CHAVES_SENSIVEIS = (
    "password", "senha", "token", "secret", "certificado", "csc",
    "authorization", "cpf", "cnpj", "chave_pix",
)


def _ofuscar(valor, _nivel: int = 0):
    """
    Remove valores sensíveis antes de registrar em disco.

    O log fica na máquina do cliente, sem proteção. Um corpo de resposta da
    API costuma ecoar o documento inteiro — CPF, endereço e valores do
    destinatário — e às vezes credenciais.
    """
    if _nivel > 6:
        return "..."
    if isinstance(valor, dict):
        return {
            chave: (
                "***"
                if any(s in str(chave).lower() for s in _CHAVES_SENSIVEIS)
                else _ofuscar(item, _nivel + 1)
            )
            for chave, item in valor.items()
        }
    if isinstance(valor, (list, tuple)):
        return [_ofuscar(item, _nivel + 1) for item in valor[:20]]
    if isinstance(valor, str) and len(valor) > 200:
        return valor[:200] + "…"
    return valor


def _resposta_para_log(response) -> str:
    """Corpo da resposta pronto para log — ofuscado quando for JSON."""
    try:
        return str(_ofuscar(response.json()))[:600]
    except Exception:
        return f"<corpo nao-JSON, {len(response.content or b'')} bytes>"


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

    def emitir_nfe(
        self, ref: str, payload: dict, idempotency_key: Optional[str] = None
    ) -> EmissaoResultado:
        url = f"{self.base_url}/erp/fiscal/nfe/emitir"
        body = {
            "ref": ref,
            "payload": payload
        }
        headers = dict(self.headers)
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=body, headers=headers)
                response.raise_for_status()
                return self._parse_response(response.json())
        except httpx.HTTPStatusError as exc:
            logger.error("[FISCAL] Erro HTTP ao emitir NF-e: %s - %s",
                         exc.response.status_code, _resposta_para_log(exc.response))
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

    def inutilizar_numeracao(
        self, ref: str, payload: dict, idempotency_key: Optional[str] = None
    ) -> EmissaoResultado:
        url = f"{self.base_url}/erp/fiscal/nfe/inutilizar"
        body = {"ref": ref, "payload": payload}
        headers = dict(self.headers)
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=body, headers=headers)
                response.raise_for_status()
                return self._parse_response(response.json())
        except httpx.HTTPStatusError as exc:
            logger.error("[FISCAL] Erro HTTP ao inutilizar numeracao: %s", exc.response.status_code)
            try:
                return self._parse_response(exc.response.json())
            except Exception:
                return {"status": "erro", "mensagem_sefaz": f"Erro {exc.response.status_code} da API"}
