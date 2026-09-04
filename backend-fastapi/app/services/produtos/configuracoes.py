from sqlalchemy.orm import Session

from app.db.crud.produtos.configuracoes import (
    get_configuracao_produtos,
    create_configuracao_produtos,
)
from app.db.models.configuracao_produtos import ConfiguracaoProdutos
from app.schemas.configuracao_produtos import ConfiguracaoProdutosUpdate

def get_or_create_configuracao_produtos(
    db: Session,
    empresa_id: int,
) -> ConfiguracaoProdutos:
    config = get_configuracao_produtos(db, empresa_id)
    if not config:
        config = create_configuracao_produtos(db, empresa_id)
    return config

def update_configuracao_produtos(
    db: Session,
    empresa_id: int,
    data: ConfiguracaoProdutosUpdate,
) -> ConfiguracaoProdutos:
    config = get_configuracao_produtos(db, empresa_id)
    if not config:
        config = create_configuracao_produtos(db, empresa_id)
    campos = data.model_dump(exclude_unset=True)
    for campo, valor in campos.items():
        setattr(config, campo, valor)
    return config