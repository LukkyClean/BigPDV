# app/services/fiscal/__init__.py
from .core import verificar_completude_venda, verificar_completude_os

__all__ = ["verificar_completude_venda", "verificar_completude_os"]