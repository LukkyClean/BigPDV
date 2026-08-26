# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/http/client_mock.py
# DESCRIÇÃO: Client mock para ambiente de homologação local.
#
# Simula respostas da API de emissão fiscal sem fazer chamadas externas.
# Gera dados fictícios (chave de acesso, protocolo, URLs) para testar
# o fluxo completo de emissão no BigPDV.
# ---------------------------------------------------------------------------

import logging
import random
import string
import time
from datetime import datetime

from .client import EmissaoResultado

logger = logging.getLogger(__name__)


def _gerar_chave_acesso() -> str:
    """Gera chave de acesso fictícia com 44 dígitos."""
    return "".join(random.choices(string.digits, k=44))


def _gerar_protocolo() -> str:
    """Gera protocolo fictício com 15 dígitos."""
    return "".join(random.choices(string.digits, k=15))


def _gerar_numero_nota() -> int:
    """Gera número de nota aleatório para testes."""
    return random.randint(1, 999999)


class FiscalClientMock:
    """
    Client mock que simula a API de emissão fiscal.

    Por padrão retorna 'autorizado'. Útil para testar fluxos de UI,
    services e endpoints sem depender da API Online StartBig.
    """

    def __init__(self, delay: float = 0.3):
        self._delay = delay

    def _simular_latencia(self) -> None:
        if self._delay > 0:
            time.sleep(self._delay)

    def emitir_nfe(self, ref: str, payload: dict) -> EmissaoResultado:
        logger.info("[FISCAL MOCK] emitir_nfe ref=%s", ref)
        self._simular_latencia()

        chave = _gerar_chave_acesso()
        protocolo = _gerar_protocolo()

        resultado: EmissaoResultado = {
            "status": "autorizado",
            "chave_acesso": chave,
            "protocolo": protocolo,
            "numero": payload.get("numero", _gerar_numero_nota()),
            "serie": payload.get("serie", 1),
            "url_pdf": f"https://mock.startbig.com.br/danfe/{ref}.pdf",
            "url_xml": f"https://mock.startbig.com.br/xml/{ref}.xml",
            "codigo_sefaz": 100,
            "mensagem_sefaz": "Autorizado o uso da NF-e (HOMOLOGAÇÃO - SEM VALOR FISCAL)",
        }

        logger.info(
            "[FISCAL MOCK] NF-e autorizada — chave=%s protocolo=%s",
            chave, protocolo,
        )
        return resultado

    def consultar_nfe(self, ref: str) -> EmissaoResultado:
        logger.info("[FISCAL MOCK] consultar_nfe ref=%s", ref)
        self._simular_latencia()

        return {
            "status": "autorizado",
            "chave_acesso": _gerar_chave_acesso(),
            "protocolo": _gerar_protocolo(),
            "numero": None,
            "serie": None,
            "url_pdf": f"https://mock.startbig.com.br/danfe/{ref}.pdf",
            "url_xml": f"https://mock.startbig.com.br/xml/{ref}.xml",
            "codigo_sefaz": 100,
            "mensagem_sefaz": "Autorizado o uso da NF-e (HOMOLOGAÇÃO - SEM VALOR FISCAL)",
        }

    def cancelar_nfe(self, ref: str, justificativa: str) -> EmissaoResultado:
        logger.info("[FISCAL MOCK] cancelar_nfe ref=%s justificativa=%s", ref, justificativa)
        self._simular_latencia()

        return {
            "status": "cancelado",
            "chave_acesso": None,
            "protocolo": _gerar_protocolo(),
            "numero": None,
            "serie": None,
            "url_pdf": None,
            "url_xml": None,
            "codigo_sefaz": 135,
            "mensagem_sefaz": "Evento registrado e vinculado a NF-e (HOMOLOGAÇÃO)",
        }
