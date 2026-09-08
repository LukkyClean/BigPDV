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

    @staticmethod
    def _primeiro(dados: dict, *chaves: str):
        """Primeiro valor presente entre as chaves, na ordem dada.

        A API StartBig é uma INTERMEDIÁRIA da Focus NFe, e as duas nem sempre
        usam o mesmo nome: a Focus devolve `qrcode_url`, `numero_protocolo` e
        `caminho_xml_nota_fiscal`, enquanto a intermediária pode normalizar
        para `qrcode`, `protocolo` e `url_xml`. Aceitar as duas grafias evita
        que uma diferença de vocabulário faça o cupom sair sem QR Code — e o
        cupom sem QR Code não vale.
        """
        for chave in chaves:
            valor = dados.get(chave)
            if valor not in (None, ""):
                return valor
        return None

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
            "chave_acesso": self._primeiro(response_data, "chave_acesso", "chave_nfe"),
            "protocolo": self._primeiro(response_data, "protocolo", "numero_protocolo"),
            "numero": response_data.get("numero"),
            "serie": response_data.get("serie"),
            "url_pdf": self._primeiro(response_data, "url_pdf", "caminho_danfe"),
            "url_xml": self._primeiro(
                response_data, "url_xml", "caminho_xml_nota_fiscal",
            ),
            "codigo_sefaz": self._primeiro(response_data, "codigo_sefaz", "status_sefaz"),
            "mensagem_sefaz": mensagem,
            # Campos de NFC-e. Vêm None na NF-e, que não os devolve.
            "qrcode": self._primeiro(response_data, "qrcode", "qrcode_url"),
            "url_consulta": self._primeiro(
                response_data, "url_consulta", "url_consulta_nf",
            ),
            # A Focus CALCULA o vTotTrib (tabela IBPT por NCM) mas não o
            # devolve no JSON — só no XML. Por isso quase sempre vem None aqui
            # e quem o busca é `obter_valor_tributos_do_xml`.
            "valor_tributos": self._primeiro(
                response_data, "valor_tributos", "valor_total_tributos",
            ),
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

    def emitir_nfce(
        self, ref: str, payload: dict, idempotency_key: Optional[str] = None
    ) -> EmissaoResultado:
        """Emite NFC-e. Mesmo contrato da NF-e, outro endpoint e sem polling."""
        url = f"{self.base_url}/erp/fiscal/nfce/emitir"
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
            logger.error("[FISCAL] Erro HTTP ao emitir NFC-e: %s - %s",
                         exc.response.status_code, _resposta_para_log(exc.response))
            try:
                data = exc.response.json()
                return self._parse_response(data)
            except Exception:
                return {"status": "erro", "mensagem_sefaz": f"Erro {exc.response.status_code} da API"}
        except Exception as exc:
            logger.error("[FISCAL] Falha na requisição de emissão de NFC-e: %s", exc)
            return {"status": "erro", "mensagem_sefaz": str(exc)}

    def baixar_xml(self, caminho: str) -> Optional[str]:
        """Baixa o XML autorizado. Devolve None em qualquer falha."""
        if not caminho:
            return None

        # A Focus devolve caminho RELATIVO em `caminho_xml_nota_fiscal`
        # (ex.: "/arquivos/.../123-nfe.xml"); a intermediária pode devolver a
        # URL completa. Aceitar os dois evita montar uma URL malformada.
        url = caminho if caminho.startswith("http") else f"{self.base_url}{caminho}"

        try:
            with httpx.Client(timeout=15.0) as client:
                resposta = client.get(url, headers=self.headers)
                resposta.raise_for_status()
                return resposta.text
        except Exception as exc:
            # Só o valor dos tributos depende disto. A nota já está autorizada
            # — derrubar o fluxo aqui seria perder o cupom por um detalhe de
            # impressão.
            logger.warning("[FISCAL] Falha ao baixar XML em %s: %s", url, exc)
            return None

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
