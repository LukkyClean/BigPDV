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
from typing import Optional

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

    def emitir_nfe(
        self, ref: str, payload: dict, idempotency_key: Optional[str] = None
    ) -> EmissaoResultado:
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

    def emitir_nfce(
        self, ref: str, payload: dict, idempotency_key: Optional[str] = None
    ) -> EmissaoResultado:
        logger.info("[FISCAL MOCK] emitir_nfce ref=%s", ref)
        self._simular_latencia()

        chave = _gerar_chave_acesso()
        protocolo = _gerar_protocolo()

        # O QR Code real é montado pelo provedor com o CSC e a regra da UF.
        # O mock devolve algo com a MESMA forma (URL de consulta + parâmetros)
        # para o gerador do cupom ser exercitado de verdade nos testes.
        qrcode = (
            f"https://mock.sefaz.gov.br/nfce/qrcode?chNFe={chave}"
            f"&nVersao=100&tpAmb=2&cIdToken={payload.get('csc_id') or '000001'}"
        )

        resultado: EmissaoResultado = {
            "status": "autorizado",
            "chave_acesso": chave,
            "protocolo": protocolo,
            "numero": payload.get("numero", _gerar_numero_nota()),
            "serie": payload.get("serie", 1),
            "url_pdf": f"https://mock.startbig.com.br/danfe-nfce/{ref}.pdf",
            "url_xml": f"https://mock.startbig.com.br/xml/{ref}.xml",
            "codigo_sefaz": 100,
            "mensagem_sefaz": "Autorizado o uso da NFC-e (HOMOLOGAÇÃO - SEM VALOR FISCAL)",
            "qrcode": qrcode,
            "url_consulta": "https://mock.sefaz.gov.br/nfce/consulta",
            # SEM `valor_tributos` de propósito: a Focus também não o devolve
            # no JSON. Quem o obtém é `baixar_xml` + `extrair_valor_tributos`,
            # e devolvê-lo aqui esconderia esse caminho dos testes.
        }

        logger.info(
            "[FISCAL MOCK] NFC-e autorizada — chave=%s protocolo=%s",
            chave, protocolo,
        )
        return resultado

    def baixar_xml(self, caminho: str) -> Optional[str]:
        """XML mínimo, mas com a MESMA forma do real.

        Traz namespace, um `vTotTrib` por item e outro dentro do `ICMSTot` —
        é exatamente a armadilha que o parser precisa enfrentar: pegar o
        primeiro `vTotTrib` que aparece devolveria o tributo de um item só.
        """
        if not caminho:
            return None

        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">'
            "<NFe><infNFe>"
            "<det nItem=\"1\"><imposto><vTotTrib>3.50</vTotTrib></imposto></det>"
            "<det nItem=\"2\"><imposto><vTotTrib>8.50</vTotTrib></imposto></det>"
            "<total><ICMSTot>"
            "<vProd>100.00</vProd><vNF>100.00</vNF><vTotTrib>12.00</vTotTrib>"
            "</ICMSTot></total>"
            "</infNFe></NFe></nfeProc>"
        )

    def consultar_nfe(
        self, ref: str, tipo_documento: str = "NFE"
    ) -> EmissaoResultado:
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

    def cancelar_nfe(
        self, ref: str, justificativa: str, tipo_documento: str = "NFE"
    ) -> EmissaoResultado:
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

    def inutilizar_numeracao(
        self, ref: str, payload: dict, idempotency_key: Optional[str] = None
    ) -> EmissaoResultado:
        logger.info("[FISCAL MOCK] inutilizar_numeracao ref=%s", ref)
        self._simular_latencia()

        return {
            "status": "homologado",
            "chave_acesso": None,
            "protocolo": _gerar_protocolo(),
            "numero": None,
            "serie": payload.get("serie"),
            "url_pdf": None,
            "url_xml": f"https://mock.startbig.com.br/inutilizacao/{ref}.xml",
            "codigo_sefaz": 102,
            "mensagem_sefaz": "Inutilizacao de numero homologado",
        }
