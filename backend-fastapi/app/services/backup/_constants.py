import os
import re

from app.core.config import BASE_DIR, database_path

# Os caminhos ficam sob BASE_DIR (e nao sob data_dir) de proposito: `static` e
# escrito por core/imagem.py como BASE_DIR/static/uploads/... e servido pelo
# mount de main.py. Mover a pasta sem mover quem escreve nela faria todo upload
# novo (foto de produto, logo, foto de OS) cair fora do que e servido, e o
# faxineiro de diretorios apagaria a origem no boot seguinte.
LOCAL_BACKUP = os.path.join(BASE_DIR, "backups")
RESTORE_BACKUPS = os.path.join(BASE_DIR, "restore_backups")
STATIC_DIR = os.path.join(BASE_DIR, "static")
OLD_DIR = os.path.join(BASE_DIR, "old")
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
