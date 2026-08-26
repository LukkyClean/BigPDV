"""
FiscalTaxEngine — Motor de cálculo tributário para NF-e.

Módulo de domínio puro (sem dependência de DB ou HTTP) que calcula
ICMS, PIS, COFINS e rateio proporcional para emissão de NF-e.

Uso:
    from app.services.fiscal.tax_engine import calcular_impostos
    resultado = calcular_impostos(itens, dados_nota)
"""

from .engine import calcular_impostos  # noqa: F401

__all__ = ["calcular_impostos"]
