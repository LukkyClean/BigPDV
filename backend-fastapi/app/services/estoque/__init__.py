# ---------------------------------------------------------------------------
# ARQUIVO: app/services/estoque/__init__.py
# MÓDULO: Estoque
# DESCRIÇÃO: Facade do módulo de controle de estoque e movimentações.
# ---------------------------------------------------------------------------

from .operacoes import (
    decrease_product_in_stock,
    restore_product_to_stock,
)

from .movimentacoes import (
    create_movimentacao,
    get_movimentacoes,
    registrar_movimentacao,
    custo_atual,
    calcular_custo_medio,
)

__all__ = [
    # Operações integradas (Vendas, PDV)
    "decrease_product_in_stock",
    "restore_product_to_stock",
    
    # Endpoints e Histórico
    "create_movimentacao",
    "get_movimentacoes",
    
    # Motor Central (Usado internamente e por cadastros/OS)
    "registrar_movimentacao",
    "custo_atual",
    "calcular_custo_medio",
]
