import gc
import json
import logging
import os
import time
import zipfile
from datetime import datetime
from typing import Optional

from sqlalchemy import text

from app.core.config import DB_NAME, database_path
from app.schemas.backup import ConfirmRestoreResponse, PrepareRestoreResponse

from ._constants import (
    LOCAL_BACKUP,
    MANIFEST_FILENAME,
    MARKER_RESTORE_PATH,
    OLD_DIR,
    RESTORE_BACKUPS,
    STATIC_DIR,
    STATIC_DIR_NO_ZIP,
    DATA_DIR,
    BackupError,
)
from ._utils import _sha256, _verify_integrity, load_manifest

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _swap_dir(src: str, dst: str, retries: int = 5, delay: float = 0.5) -> None:
    if os.path.exists(dst):
        return
    for attempt in range(retries):
        try:
            os.replace(src, dst)
            return
        except PermissionError as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise BackupError(f"Falha ao substituir arquivo após {retries} tentativas: {e}")


def _create_restore_marker(restore: dict) -> None:
    if os.path.exists(MARKER_RESTORE_PATH):
        raise BackupError(
            "Uma restauracao ja esta pendente. Reinicie o aplicativo para "
            "aplica-la, ou remova o marcador antes de iniciar outra."
        )
    tmp = MARKER_RESTORE_PATH + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(restore, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, MARKER_RESTORE_PATH)
    except Exception as e:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise BackupError(f"Falha ao criar arquivo de marcador de restauração: {e}")


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def save_backup(cycle: str, filename: str, content: bytes) -> str:
    cycle_dir = os.path.join(RESTORE_BACKUPS, cycle)
    os.makedirs(cycle_dir, exist_ok=True)

    filepath = os.path.join(cycle_dir, filename)
    tmp = filepath + ".tmp"
    try:
        with open(tmp, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, filepath)
    except Exception as e:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise BackupError(f"Falha ao salvar backup na nuvem: {e}")
    return filepath


def restore_from_chain(cycle: str, ordered_filepaths: list[str], target_dir: Optional[str] = None) -> None:
    cycle_dir = os.path.join(RESTORE_BACKUPS, cycle)

    if target_dir is None:
        target_dir = os.path.join(cycle_dir, "_restored")

    os.makedirs(target_dir, exist_ok=True)

    last_zip_path = os.path.join(cycle_dir, ordered_filepaths[-1])
    if not os.path.isfile(last_zip_path):
        raise BackupError(f"Último arquivo de backup não encontrado: {last_zip_path}")

    zip_manifest = load_manifest(last_zip_path)
    final_files = set(zip_manifest["arquivos"].keys())

    for filepath in ordered_filepaths:
        zip_filepath = os.path.join(cycle_dir, filepath)
        if not os.path.isfile(zip_filepath):
            raise BackupError(f"Arquivo de backup não encontrado: {zip_filepath}")

        with zipfile.ZipFile(zip_filepath, "r") as zf:
            if zf.testzip() is not None:
                raise BackupError(f"Falha na verificação de integridade do arquivo ZIP: {zip_filepath}")
            for member in zf.namelist():
                if member not in final_files and member != MANIFEST_FILENAME:
                    continue
                zf.extract(member, path=target_dir)


def validate_staging(cycle: str) -> str:
    cycle_dir = os.path.join(RESTORE_BACKUPS, cycle)
    staging_dir = os.path.join(cycle_dir, "_restored")

    if not os.path.isdir(staging_dir):
        raise BackupError(f"Diretório de staging não encontrado: {staging_dir}")

    manifest_path = os.path.join(staging_dir, MANIFEST_FILENAME)
    if not os.path.isfile(manifest_path):
        raise BackupError(f"Manifesto não encontrado no staging: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        try:
            manifest = json.load(f)
        except json.JSONDecodeError:
            raise BackupError(f"Manifesto inválido no staging: {manifest_path}")

    for arcname, data in manifest.get("arquivos", {}).items():
        restored_file_path = os.path.join(staging_dir, *arcname.split("/"))
        if not os.path.isfile(restored_file_path):
            raise BackupError(f"Arquivo esperado não encontrado no staging: {restored_file_path}")
        st_info = os.stat(restored_file_path)
        if st_info.st_size != data["tamanho"]:
            raise BackupError(f"Tamanho do arquivo {restored_file_path} não corresponde ao manifesto.")
        if _sha256(restored_file_path) != data["sha256"]:
            raise BackupError(f"Checksum SHA256 do arquivo {restored_file_path} não corresponde ao manifesto.")

    if not _verify_integrity(os.path.join(staging_dir, DB_NAME)):
        raise BackupError("Falha na verificação de integridade do banco de dados restaurado.")

    return staging_dir


def compare_versions(chosen: dict, current: dict) -> dict:
    from app.services.cloud.journal import code_content

    chosen_code = code_content(chosen)
    current_code = code_content(current)

    if chosen_code == current_code:
        return {"status": "equals", "details": "O backup selecionado já representa os dados atuais"}

    chosen_date = datetime.fromisoformat(chosen["criado_em"])
    current_date = datetime.fromisoformat(current["criado_em"])

    if chosen_date < current_date:
        return {
            "status": "restore_backup_outdated",
            "details": f"O backup selecionado está desatualizado. Ele restaura os dados até {chosen_date.isoformat()}",
        }
    return {
        "status": "ready",
        "details": "O backup selecionado é mais recente que os dados atuais e pode ser restaurado",
    }


def prepare_restore(cycle: str) -> PrepareRestoreResponse:
    # Importa local para evitar ciclo: restore → local → (chain)
    from .local import create_backup

    # validate_staging verifica existência, manifesto e checksums
    valid_staging = validate_staging(cycle)

    with open(os.path.join(valid_staging, MANIFEST_FILENAME), "r", encoding="utf-8") as f:
        restored_manifest = json.load(f)

    # Backup de segurança do estado ATUAL (fora da corrente principal).
    try:
        pre_restore_backup = create_backup(pre_restore=True, cycle=cycle)
    except BackupError as e:
        raise BackupError(f"Falha ao criar backup pre-restauracao: {e}")

    pre_restore_dir = os.path.join(LOCAL_BACKUP, "pre_restore")
    pre_restore_backup_path = os.path.join(pre_restore_dir, pre_restore_backup.arquivo)
    if not os.path.isfile(pre_restore_backup_path):
        raise BackupError(f"Backup pre-restauracao nao encontrado: {pre_restore_backup_path}")

    # O manifest do backup de segurança é o retrato fiel do estado vivo.
    pre_restore_manifest = load_manifest(pre_restore_backup_path)
    decision = compare_versions(restored_manifest, pre_restore_manifest)

    return PrepareRestoreResponse(
        status=decision.get("status"),
        details=decision.get("details", ""),
        ciclo=cycle,
        pre_restore_backup=pre_restore_backup.arquivo,
    )


def confirm_restore(cycle: str, pre_restore_backup_path: str) -> ConfirmRestoreResponse:
    valid_staging = validate_staging(cycle)

    _create_restore_marker({
        "cycle": cycle,
        "confirmed_at": datetime.now().isoformat(),
        "staging_dir": valid_staging,
        "pre_restore_backup": pre_restore_backup_path,
    })

    return ConfirmRestoreResponse(
        status="confirmed",
        details="Restauração confirmada. Reinicie o aplicativo para aplicar a restauração.",
        ciclo=cycle,
    )


def apply_pending_restore() -> Optional[dict]:
    if not os.path.exists(MARKER_RESTORE_PATH):
        return None

    try:
        with open(MARKER_RESTORE_PATH, "r", encoding="utf-8") as f:
            marker = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        try:
            os.remove(MARKER_RESTORE_PATH)
        except OSError:
            pass
        raise BackupError(f"Marcador de restauracao ilegivel; restauracao abortada: {e}")

    cycle = marker.get("cycle")
    staging_dir = marker.get("staging_dir")

    try:
        validate_staging(cycle)
    except BackupError as e:
        try:
            os.remove(MARKER_RESTORE_PATH)
        except OSError:
            pass
        raise BackupError(f"Staging invalido; restauracao abortada: {e}")

    production_db = database_path
    production_static = STATIC_DIR
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    snapshot_dir = os.path.join(OLD_DIR, ts)
    os.makedirs(snapshot_dir, exist_ok=True)
    old_db = os.path.join(snapshot_dir, DB_NAME)
    old_static = os.path.join(snapshot_dir, STATIC_DIR_NO_ZIP)

    staged_db = os.path.join(staging_dir, DB_NAME)
    staged_static = os.path.join(staging_dir, STATIC_DIR_NO_ZIP)

    # Intervenção profunda no SQLAlchemy e SQLite
    try:
        from app.db.session import engine

        # Força o SQLite a consolidar o WAL no banco principal e liberar os locks
        with engine.connect() as conn:
            conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE);"))
        engine.dispose()
        gc.collect()
        time.sleep(1)
    except Exception as e:
        logger.warning("[RESTORE] Não foi possível dar dispose no engine: %s", e)

    for aux in (production_db + "-wal", production_db + "-shm"):
        if os.path.exists(aux):
            for _ in range(3):
                try:
                    os.remove(aux)
                    break
                except OSError:
                    time.sleep(0.5)

    if os.path.exists(production_db):
        _swap_dir(production_db, old_db)
    if os.path.exists(production_static):
        _swap_dir(production_static, old_static)

    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(staged_db):
        _swap_dir(staged_db, production_db)
    if os.path.exists(staged_static):
        _swap_dir(staged_static, production_static)

    try:
        os.remove(MARKER_RESTORE_PATH)
    except OSError:
        pass

    return {
        "restored_cycle": cycle,
        "old_db": old_db if os.path.exists(old_db) else None,
        "old_static": old_static if os.path.isdir(old_static) else None,
    }
