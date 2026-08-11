from sqlalchemy.orm import Session

from app.db.crud.configuracao_backup import (
    get_configuracao_backup,
    create_configuracao_backup,
)
from app.db.models.configuracao_backup import ConfiguracaoBackup
from app.schemas.configuracao_backup import ConfiguracaoBackupUpdate


def get_or_create_configuracao_backup(
    db: Session,
    empresa_id: int,
) -> ConfiguracaoBackup:
    config = get_configuracao_backup(db, empresa_id)
    if not config:
        config = create_configuracao_backup(db, empresa_id)
    return config


def update_configuracao_backup(
    db: Session,
    empresa_id: int,
    data: ConfiguracaoBackupUpdate,
) -> ConfiguracaoBackup:
    config = get_configuracao_backup(db, empresa_id)
    if not config:
        config = create_configuracao_backup(db, empresa_id)

    campos = data.model_dump(exclude_unset=True)
    for campo, valor in campos.items():
        setattr(config, campo, valor)

    return config
