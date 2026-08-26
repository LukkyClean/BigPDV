# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/http/client_factory.py
# DESCRIÇÃO: Factory que seleciona o client fiscal por ambiente.
# ---------------------------------------------------------------------------

import logging

from app.core.config import settings

from .client import FiscalClientProtocol
from .client_mock import FiscalClientMock
from .client_startbig import FiscalClientStartBig

logger = logging.getLogger(__name__)


def get_fiscal_client(ambiente: int) -> FiscalClientProtocol:
    """
    Retorna o client adequado ao ambiente de emissão.

    - ambiente == 2 (Homologação) OU FISCAL_MOCK_ENABLED: retorna mock
    - ambiente == 1 (Produção): retorna client StartBig (real)

    O FISCAL_MOCK_ENABLED permite forçar mock mesmo em ambiente 1 (dev).
    """
    if ambiente == 2 or settings.FISCAL_MOCK_ENABLED:
        logger.info("[FISCAL] Usando client MOCK (ambiente=%d, mock_enabled=%s)",
                     ambiente, settings.FISCAL_MOCK_ENABLED)
        return FiscalClientMock()

    logger.info("[FISCAL] Usando client StartBig (ambiente=%d)", ambiente)
    return FiscalClientStartBig()
