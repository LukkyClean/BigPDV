# Re-exporta toda a API pública do pacote backup para manter
# compatibilidade com os importadores existentes que usam:
#   from app.services import backup as backup_service
#   from app.services.backup import create_backup, ...

from ._constants import (
    BackupError,
    LOCAL_BACKUP,
    OLD_DIR,
    RESTORE_BACKUPS,
    STATIC_DIR,
    BACKUP_FILENAME_REGEX,
    MANIFEST_FILENAME,
    MARKER_RESTORE_PATH,
)
from ._utils import load_manifest, limpar_snapshots_antigos
from .local import (
    check_backup,
    count_backups_today,
    create_backup,
    delete_old_backups,
    get_last_backup,
    list_backups,
)
from .restore import (
    apply_pending_restore,
    compare_versions,
    confirm_restore,
    prepare_restore,
    restore_from_chain,
    save_backup,
    validate_staging,
)

__all__ = [
    # Exceção
    "BackupError",
    # Constantes
    "LOCAL_BACKUP",
    "OLD_DIR",
    "RESTORE_BACKUPS",
    "STATIC_DIR",
    "BACKUP_FILENAME_REGEX",
    "MANIFEST_FILENAME",
    "MARKER_RESTORE_PATH",
    # Utilitários
    "load_manifest",
    "limpar_snapshots_antigos",
    # Operações locais
    "list_backups",
    "get_last_backup",
    "count_backups_today",
    "create_backup",
    "delete_old_backups",
    "check_backup",
    # Pipeline de restauração
    "save_backup",
    "restore_from_chain",
    "validate_staging",
    "compare_versions",
    "prepare_restore",
    "confirm_restore",
    "apply_pending_restore",
]
