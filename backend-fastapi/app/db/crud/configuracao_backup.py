from sqlalchemy.orm import Session
from app.db.models.configuracao_backup import ConfiguracaoBackup


def get_configuracao_backup(db: Session, empresa_id: int) -> ConfiguracaoBackup | None:
    return db.query(ConfiguracaoBackup).filter(
        ConfiguracaoBackup.empresa_id == empresa_id
    ).first()


def create_configuracao_backup(db: Session, empresa_id: int) -> ConfiguracaoBackup:
    config = ConfiguracaoBackup(empresa_id=empresa_id)
    db.add(config)
    db.flush()
    return config
