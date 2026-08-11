import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import zipfile
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

from app.core.config import database_path

from ._constants import (
    BACKUP_FILENAME_REGEX,
    BACKUP_TIMESTAMP_FORMAT,
    INTEGRITY_CHECK_OK,
    LOCAL_BACKUP,
    MANIFEST_FILENAME,
    BackupError,
)


def _sha256(filepath: str) -> str:
    sha = hashlib.sha256()
    # Lemos em blocos de 1 MB para não carregar arquivos grandes na memória.
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _create_snapshot_db(backup_path: str) -> None:
    origin = sqlite3.connect(database_path)
    to = sqlite3.connect(backup_path)
    try:
        origin.backup(to)
    finally:
        origin.close()
        to.close()


def _verify_integrity(backup_path: str) -> bool:
    conn = sqlite3.connect(backup_path)
    # .fetchone() retorna a primeira linha do resultado, ex: ("ok",)
    try:
        result = conn.execute("PRAGMA integrity_check;").fetchone()
        return result is not None and result[0] == INTEGRITY_CHECK_OK
    finally:
        conn.close()


def _parse_timestamp_from_filename(filename: str) -> Optional[datetime]:
    match = BACKUP_FILENAME_REGEX.match(filename)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), BACKUP_TIMESTAMP_FORMAT)
    except ValueError:
        return None


def load_manifest(backup_path: str) -> dict:
    """Lê o manifest.json de dentro de um arquivo ZIP de backup."""
    filepath = os.path.join(LOCAL_BACKUP, backup_path)
    with zipfile.ZipFile(filepath, "r") as zf:
        try:
            return json.loads(zf.read(MANIFEST_FILENAME))
        except KeyError:
            raise BackupError(f"Manifesto não encontrado no backup: {MANIFEST_FILENAME}")


def _exists_file(file_in_manifest: Optional[dict], st_info) -> bool:
    if file_in_manifest is None:
        return False
    return (
        file_in_manifest["tamanho"] == st_info.st_size
        and file_in_manifest["mtime_ns"] == st_info.st_mtime_ns
    )


def limpar_snapshots_antigos(dias: int = 7) -> None:
    """Remove subpastas de OLD_DIR com mais de `dias` dias."""
    from ._constants import OLD_DIR

    if not os.path.exists(OLD_DIR):
        return
    limite = datetime.now() - timedelta(days=dias)
    for entry in os.scandir(OLD_DIR):
        if not entry.is_dir():
            continue
        mtime = datetime.fromtimestamp(entry.stat().st_mtime)
        if mtime < limite:
            shutil.rmtree(entry.path, ignore_errors=True)
            logger.info("[LIMPEZA] Snapshot antigo removido: %s", entry.path)
