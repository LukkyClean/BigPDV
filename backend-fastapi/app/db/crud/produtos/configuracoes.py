from sqlalchemy.orm import Session
from app.db.models.configuracao_produtos import ConfiguracaoProdutos

def get_configuracao_produtos(db: Session, empresa_id: int) -> ConfiguracaoProdutos | None:
    return db.query(ConfiguracaoProdutos).filter(
        ConfiguracaoProdutos.empresa_id == empresa_id
    ).first()


def create_configuracao_produtos(db: Session, empresa_id: int) -> ConfiguracaoProdutos:
    config = ConfiguracaoProdutos(empresa_id=empresa_id)
    db.add(config)
    db.flush()
    return config


def update_configuracao_produtos(
    db: Session,
    config: ConfiguracaoProdutos,
) -> ConfiguracaoProdutos:
    db.flush()
    return config
