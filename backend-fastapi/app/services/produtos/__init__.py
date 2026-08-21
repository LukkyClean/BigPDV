# ---------------------------------------------------------------------------
# MÓDULO: app/services/produto/__init__.py
# DESCRIÇÃO: Facade do módulo de produtos. Ponto único de entrada para as rotas.
# ---------------------------------------------------------------------------

from .configuracoes import (
    get_or_create_configuracao_produtos,
    update_configuracao_produtos,
)

from .estoque import (
    decrease_product_in_stock,
    restore_product_to_stock,
)

from .fiscal import (
    get_dados_fiscais,
    upsert_dados_fiscais,
)

from .imagem import (
    create_produto_image,
    replace_produto_principal_image,
    delete_produto_image,
)

from .produto import (
    create_produto,
    get_produto_by_search,
    get_produto_simple_by_search,
    update_produto_by_id,
    toggle_active_disable_produto_by_id,
    get_produto_by_id,
)

# A lista __all__ define explicitamente o que será exportado quando alguém 
# fizer: "from app.services.produto import *"
__all__ = [
    # Configurações
    "get_or_create_configuracao_produtos",
    "update_configuracao_produtos",
    
    # Estoque
    "decrease_product_in_stock",
    "restore_product_to_stock",
    
    # Fiscal
    "get_dados_fiscais",
    "upsert_dados_fiscais",
    
    # Imagem
    "create_produto_image",
    "replace_produto_principal_image",
    "delete_produto_image",
    
    # Produto (Core)
    "create_produto",
    "get_produto_by_search",
    "get_produto_simple_by_search",
    "update_produto_by_id",
    "toggle_active_disable_produto_by_id",
    "get_produto_by_id",
]