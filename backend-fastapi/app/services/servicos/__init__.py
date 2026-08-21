# ---------------------------------------------------------------------------
# MÓDULO: app/services/servico/__init__.py
# DESCRIÇÃO: Facade do módulo de serviços. Ponto único de entrada.
# ---------------------------------------------------------------------------

from .fiscal import (
    get_dados_fiscais,
    upsert_dados_fiscais,
)

from .servico import (
    create_servico,
    get_servico_by_search,
    get_servico_stats,
    update_servico_by_id,
    toggle_active_disable_servico_by_id,
)

# A lista __all__ define explicitamente o que será exportado pelo módulo
__all__ = [
    # Fiscal
    "get_dados_fiscais",
    "upsert_dados_fiscais",
    
    # Serviço (Core)
    "create_servico",
    "get_servico_by_search",
    "get_servico_stats",
    "update_servico_by_id",
    "toggle_active_disable_servico_by_id",
]