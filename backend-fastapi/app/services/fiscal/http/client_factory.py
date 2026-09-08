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


def get_fiscal_client(ambiente: int, token: str = "") -> FiscalClientProtocol:
    """
    Retorna o client adequado ao ambiente de emissão.

    - FISCAL_MOCK_ENABLED=True: retorna mock (não faz chamadas HTTP)
    - FISCAL_MOCK_ENABLED=False: retorna client StartBig (ambiente=1=Produção, ambiente=2=Homologação)
    """
    if settings.FISCAL_MOCK_ENABLED:
        logger.info("[FISCAL] Usando client MOCK (mock_enabled=%s)", settings.FISCAL_MOCK_ENABLED)
        return FiscalClientMock()

    logger.info("[FISCAL] Usando client StartBig (ambiente=%d)", ambiente)
    return FiscalClientStartBig(ambiente=ambiente, token=token)
