# app/services/fiscal/http/__init__.py
from .client_factory import get_fiscal_client
from .client import FiscalClientProtocol, EmissaoResultado

__all__ = ["get_fiscal_client", "FiscalClientProtocol", "EmissaoResultado"]
