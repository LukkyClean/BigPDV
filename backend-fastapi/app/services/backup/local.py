import json
import logging
import os
import tempfile
import zipfile
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import DB_NAME
from app.schemas.backup import BackupCriado, BackupInfo, BackupVerificacao

from ._constants import (
    BACKUP_FILENAME_REGEX,
    BACKUP_PREFIX,
    BACKUP_TIMESTAMP_FORMAT,
    FULL_TO_SAVE,
    LOCAL_BACKUP,
    MANIFEST_FILENAME,
    MIN_DAYS_TO_COMPLETE_SAVE,
    PRE_RESTORE_PREFIX,
    STATIC_DIR,
    STATIC_DIR_NO_ZIP,
    FISCAL_DIR,
    FISCAL_DIR_NO_ZIP,
    FISCAL_DANFE_SUBPASTA,
    FISCAL_DANFE_TETO_BYTES,
    BackupError,
)
from ._manifest import ManifestBuilder
from ._utils import (
    _create_snapshot_db,
    _exists_file,
    _parse_timestamp_from_filename,
    _sha256,
    _verify_integrity,
    load_manifest,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _find_current_anchor() -> Optional[BackupInfo]:
    backups = list_backups()
    return next((b for b in backups if b.completo), None) if backups else None



def _danfe_excede_teto() -> bool:
    """
    A pasta de DANFEs passou do tamanho que vale a pena subir?

    Medida a cada backup, e não uma vez: a loja cresce. Erro de leitura conta
    como "não excede" — na dúvida, incluir o arquivo é o lado seguro.
    """
    pasta = os.path.join(FISCAL_DIR, FISCAL_DANFE_SUBPASTA)
    if not os.path.isdir(pasta):
        return False

    total = 0
    try:
        for root, _, files in os.walk(pasta):
            for nome in files:
                total += os.path.getsize(os.path.join(root, nome))
                if total > FISCAL_DANFE_TETO_BYTES:
                    logger.warning(
                        "[BACKUP] DANFEs somam mais de %d MB: ficam de fora deste "
                        "pacote para não estourar o envio à nuvem. Os XMLs sobem "
                        "normalmente, e os PDFs continuam salvos nesta máquina.",
                        FISCAL_DANFE_TETO_BYTES // (1024 * 1024),
                    )
                    return True
    except OSError:
        return False

    return False

def _is_full_backup(last_anchor: Optional[BackupInfo]) -> bool:
    return (
        last_anchor is None
        or datetime.now() >= datetime.fromisoformat(last_anchor.criado_em) + timedelta(days=MIN_DAYS_TO_COMPLETE_SAVE)
    )


def _join_incr_backups_to_full(backups: list[BackupInfo]) -> list[dict]:
    backup_chain = []
    for b in reversed(backups):
        if b.completo:
            backup_chain.append({"anchor": b, "incr": []})
        elif backup_chain:
            backup_chain[-1]["incr"].append(b)
    backup_chain.reverse()
    return backup_chain


def _referenced_backups_preserve(backups: set[str]) -> set[str]:
    return {
        data["origem"]
        for b_path in backups
        for data in load_manifest(b_path)["arquivos"].values()
    }


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def list_backups() -> list[BackupInfo]:
    if not os.path.exists(LOCAL_BACKUP):
        return []

    backups: list[BackupInfo] = []
    for filename in os.listdir(LOCAL_BACKUP):
        ts = _parse_timestamp_from_filename(filename)
        if ts is None:
            continue
        filepath = os.path.join(LOCAL_BACKUP, filename)
        name, _ = os.path.splitext(filename)
        backups.append(BackupInfo(
            arquivo=filename,
            criado_em=ts.isoformat(),
            tamanho_bytes=os.path.getsize(filepath),
            completo=name.endswith("_full"),
        ))

    return sorted(backups, key=lambda b: b.criado_em, reverse=True)


def get_last_backup() -> Optional[BackupInfo]:
    backups = list_backups()
    return backups[0] if backups else None


def count_backups_today() -> int:
    hoje = datetime.now().date()
    return sum(
        1 for b in list_backups()
        if datetime.fromisoformat(b.criado_em).date() == hoje
    )


def create_backup(
    force_full: bool = False,
    pre_restore: bool = False,
    cycle: Optional[str] = None,
) -> BackupCriado:
    if pre_restore and cycle:
        pre_restore_dir = os.path.join(LOCAL_BACKUP, "pre_restore")
        os.makedirs(pre_restore_dir, exist_ok=True)
    else:
        os.makedirs(LOCAL_BACKUP, exist_ok=True)

    last_anchor = _find_current_anchor()
    is_full = _is_full_backup(last_anchor) or force_full or pre_restore
    backup_type = "full" if is_full else "incr"
    last_backup: Optional[BackupInfo] = get_last_backup() if not is_full else None

    now = datetime.now()
    if pre_restore and cycle:
        stored_filename = f"{PRE_RESTORE_PREFIX}{now.strftime(BACKUP_TIMESTAMP_FORMAT)}_{cycle}.zip"
        stored_filepath = os.path.join(pre_restore_dir, stored_filename)
    else:
        stored_filename = f"{BACKUP_PREFIX}{now.strftime(BACKUP_TIMESTAMP_FORMAT)}_{backup_type}.zip"
        stored_filepath = os.path.join(LOCAL_BACKUP, stored_filename)

    tmp_path = stored_filepath + ".tmp"

    # TemporaryDirectory cria uma pasta temporária e a APAGA sozinha
    with tempfile.TemporaryDirectory(prefix="startbig_bkp_") as tmpdir:
        logger.debug("[BACKUP] Criando snapshot do banco de dados em: %s", tmpdir)
        snapshot_db_path = os.path.join(tmpdir, DB_NAME)
        _create_snapshot_db(snapshot_db_path)

        logger.debug("[BACKUP] Verificando integridade do snapshot...")
        if not _verify_integrity(snapshot_db_path):
            raise BackupError("Falha na verificação de integridade do snapshot do banco de dados.")

        logger.info("[BACKUP] Empacotando snapshot e arquivos estáticos em: %s", stored_filename)

        # O manifest guarda os metadados e checksums de cada arquivo.
        manifest = ManifestBuilder(tipo=backup_type, base=None if is_full else last_backup.arquivo)

        try:
            # ZIP_DEFLATED = com compressão
            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(snapshot_db_path, arcname=DB_NAME)
                st_info = os.stat(snapshot_db_path)
                manifest.add_file(
                    arcname=DB_NAME,
                    sha256=_sha256(snapshot_db_path),
                    size=st_info.st_size,
                    mtime_ns=st_info.st_mtime_ns,
                    origin=stored_filename,
                )

                base_files = load_manifest(last_backup.arquivo)["arquivos"] if last_backup else {}

                # Duas árvores, a mesma regra: arquivo que não mudou desde o
                # último backup entra só no manifesto (incremental), e o que
                # mudou é regravado.
                #
                # `fiscal` entrou em 13/09/2026: são os XMLs autorizados, que a
                # loja é obrigada a guardar por cinco anos. Ficam sob `data/` e
                # por isso não vinham na árvore de `static`.
                for pasta, prefixo in ((STATIC_DIR, STATIC_DIR_NO_ZIP), (FISCAL_DIR, FISCAL_DIR_NO_ZIP)):
                    if not os.path.isdir(pasta):
                        continue

                    # os.walk percorre a árvore de pastas recursivamente
                    for root, subdirs, files in os.walk(pasta):
                        # O DANFE sobe enquanto couber. Passando do teto, a
                        # pasta é podada AQUI (antes de percorrer) e o XML
                        # segue normalmente — documento antes de conveniência.
                        if pasta == FISCAL_DIR and root == pasta:
                            if _danfe_excede_teto():
                                subdirs[:] = [
                                    d for d in subdirs if d != FISCAL_DANFE_SUBPASTA
                                ]

                        for filename in files:
                            abs_path = os.path.join(root, filename)
                            rel = os.path.relpath(abs_path, pasta)
                            arcname = os.path.join(prefixo, rel).replace(os.sep, "/")
                            st_info = os.stat(abs_path)
                            data = base_files.get(arcname)

                            if _exists_file(data, st_info):
                                manifest.add_file(
                                    arcname=arcname,
                                    sha256=data["sha256"],
                                    size=data["tamanho"],
                                    mtime_ns=data["mtime_ns"],
                                    origin=data["origem"],
                                )
                            else:
                                zf.write(abs_path, arcname=arcname)
                                manifest.add_file(
                                    arcname=arcname,
                                    sha256=_sha256(abs_path),
                                    size=st_info.st_size,
                                    mtime_ns=st_info.st_mtime_ns,
                                    origin=stored_filename,
                                )

                zf.writestr(MANIFEST_FILENAME, json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False))

            os.replace(tmp_path, stored_filepath)

        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    delete_old_backups()

    return BackupCriado(
        arquivo=stored_filename,
        criado_em=now.isoformat(),
        tamanho_bytes=os.path.getsize(stored_filepath),
    )


def delete_old_backups() -> list[str]:
    backups = list_backups()
    if not backups:
        return []

    backups_chain = _join_incr_backups_to_full(backups)
    backups_to_save: set[str] = set()

    if backups_chain:
        current = backups_chain[0]
        backups_to_save.add(current["anchor"].arquivo)
        for inc in current["incr"]:
            backups_to_save.add(inc.arquivo)

    for chain in backups_chain[1:FULL_TO_SAVE]:
        backups_to_save.add(chain["anchor"].arquivo)

    try:
        referenced_backups = _referenced_backups_preserve(backups_to_save)
    except BackupError as e:
        logger.error("[BACKUP] Retenção abortada por segurança (manifest ilegível): %s", e)
        return []

    guardian_backups = backups_to_save | referenced_backups

    for filename in referenced_backups - backups_to_save:
        logger.warning(
            "[BACKUP] '%s' seria descartado pela política, "
            "mas ainda é referenciado por um backup ativo. Preservado.", filename
        )

    removed_backups = []
    for filename in os.listdir(LOCAL_BACKUP):
        if not BACKUP_FILENAME_REGEX.match(filename) or filename in guardian_backups:
            continue
        try:
            os.remove(os.path.join(LOCAL_BACKUP, filename))
            removed_backups.append(filename)
        except OSError as e:
            logger.error("[BACKUP] Falha ao remover arquivo de backup %s: %s", filename, e)

    return removed_backups


def check_backup(backup_path: str, deep: bool = False) -> BackupVerificacao:
    manifest = load_manifest(backup_path)
    manifest_files = manifest["arquivos"]

    per_origins: dict[str, dict] = {}
    base_name = os.path.basename(backup_path)

    for arcname, data in manifest_files.items():
        origins = data["origem"]
        if not deep and origins != base_name:
            continue
        per_origins.setdefault(origins, {})[arcname] = data

    verified = 0
    origins = base_name  # fallback caso per_origins esteja vazio
    with tempfile.TemporaryDirectory(prefix="startbig_bkp_check_") as tmpdir:
        for origins, origin_files in per_origins.items():
            zip_path = os.path.join(LOCAL_BACKUP, origins)
            if not os.path.isfile(zip_path):
                raise BackupError(f"Arquivo de backup não encontrado: {zip_path}")

            with zipfile.ZipFile(zip_path, "r") as zf:
                if zf.testzip() is not None:
                    raise BackupError(f"Falha na verificação de integridade do arquivo ZIP: {zip_path}")

                for arcname, data in origin_files.items():
                    try:
                        zf.extract(arcname, path=tmpdir)
                    except KeyError:
                        raise BackupError(f"Arquivo {arcname} não encontrado no backup {origins}")

                    extracted_path = os.path.join(tmpdir, *arcname.split("/"))
                    if _sha256(extracted_path) != data["sha256"]:
                        raise BackupError(
                            f"Falha na verificação de integridade do arquivo {arcname} no backup {origins}"
                        )
                    verified += 1

        if not _verify_integrity(os.path.join(tmpdir, DB_NAME)):
            raise BackupError(f"Falha na verificação de integridade do banco de dados no backup {origins}")

    return BackupVerificacao(
        arquivo=backup_path,
        criado_em=manifest.get("criado_em"),
        valido=True,
        modo="profundo" if deep else "raso",
        arquivos_verificados=verified,
        total_no_manifest=len(manifest_files),
    )
