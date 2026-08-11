import os
import re

from app.core.config import BASE_DIR, data_dir, database_path

LOCAL_BACKUP = os.path.join(data_dir, "backup")
RESTORE_BACKUPS = os.path.join(data_dir, "backup", "restore")
STATIC_DIR = os.path.join(data_dir, "static")
OLD_DIR = os.path.join(data_dir, "old")
DATA_DIR = os.path.dirname(database_path)

FULL_TO_SAVE = 4
MIN_DAYS_TO_COMPLETE_SAVE = 7

BACKUP_PREFIX = "backup_"
PRE_RESTORE_PREFIX = "pre_restore_"
BACKUP_SUFFIX = "(_full|_incr)?"
BACKUP_TIMESTAMP_FORMAT = "%Y-%m-%d_%H%M%S"

BACKUP_FILENAME_REGEX = re.compile(
    rf"^{BACKUP_PREFIX}(\d{{4}}-\d{{2}}-\d{{2}}_\d{{6}}){BACKUP_SUFFIX}\.zip$"
)
PRE_RESTORE_FILENAME_REGEX = re.compile(
    rf"^{PRE_RESTORE_PREFIX}(\d{{4}}-\d{{2}}-\d{{2}}_\d{{6}})_(\d{{4}}-\d{{2}}-\d{{2}})\.zip$"
)

MANIFEST_FILENAME = "manifest.json"
STATIC_DIR_NO_ZIP = "static"

MARKER_RESTORE_FILENAME = "restore_pendente.json"
MARKER_RESTORE_PATH = os.path.join(BASE_DIR, MARKER_RESTORE_FILENAME)

OLD_SUFFIX = ".old"
INTEGRITY_CHECK_OK = "ok"


class BackupError(Exception):
    pass
