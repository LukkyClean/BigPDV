# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/http/client_startbig.py
# DESCRIÇÃO: Client real que chama a API Online StartBig para emissão fiscal.
#
# PLACEHOLDER — os endpoints da API Online ainda não estão definidos.
# Quando estiverem prontos, implementar os métodos usando cloud/_http.py.
# ---------------------------------------------------------------------------

import logging

from .client import EmissaoResultado

logger = logging.getLogger(__name__)

_NAO_IMPLEMENTADO = (
    "Endpoints da API Online StartBig ainda não definidos. "
    "Use o ambiente de homologação (mock) para testes."
)


class FiscalClientStartBig:
    """
    Client que se comunica com a API Online StartBig para emissão fiscal.

    O fluxo real será:
    BigPDV → API StartBig (api.startbig.com.br/erp/fiscal/...) → Focus NFe → SEFAZ

    Por enquanto todos os métodos levantam NotImplementedError.
    """

    def emitir_nfe(self, ref: str, payload: dict) -> EmissaoResultado:
        raise NotImplementedError(_NAO_IMPLEMENTADO)

    def consultar_nfe(self, ref: str) -> EmissaoResultado:
        raise NotImplementedError(_NAO_IMPLEMENTADO)

    def cancelar_nfe(self, ref: str, justificativa: str) -> EmissaoResultado:
        raise NotImplementedError(_NAO_IMPLEMENTADO)
