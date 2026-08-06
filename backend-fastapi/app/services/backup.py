import hashlib
import json
import os
import re
import sqlite3
import tempfile
import zipfile

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from app.core.config import BASE_DIR, DB_NAME, database_path

LOCAL_BACKUP = os.path.join(BASE_DIR, "backups")
RESTORED_BACKUP = os.path.join(BASE_DIR, "restore_backups")

STATIC_DIR = os.path.join(BASE_DIR, "static")

FULL_TO_SAVE = 4

MIN_DAYS_TO_COMPLETE_SAVE = 7

BACKUP_PREFIX = "backup_"
BACKUP_SUFFIX = "(_full|_incr)?"
BACKUP_TIMESTAMP_FORMAT = "%Y-%m-%d_%H%M%S"

BACKUP_FILENAME_REGEX = re.compile(rf"^{BACKUP_PREFIX}(\d{{4}}-\d{{2}}-\d{{2}}_\d{{6}}){BACKUP_SUFFIX}\.zip$")

MANIFEST_FILENAME = "manifest.json"
STATIC_DIR_NO_ZIP = "static"

class BackupError(Exception):
    pass

@dataclass
class ManifestBuilder:
    
    manifest_version: int = 2
    tipo: str = "full"
    base: Optional[str] = None
    criado_em: str = field(default_factory=lambda: datetime.now().isoformat())
    app: str = "StartBigERP"
    integrity_check: str = "ok"
    arquivos: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def add_file(
        self,
        arcname: str,
        sha256: str,
        size: int,
        mtime_ns: int,
        origin: str  
    ) -> None:
        self.arquivos[arcname] = {
            "sha256": sha256,
            "tamanho": size,
            "mtime_ns": mtime_ns,
            "origem": origin
        }
        
    def to_dict(self) -> Dict[str, Any]:
        data = {
            "manifest_version": self.manifest_version,
            "tipo": self.tipo,
            "base": None,
            "criado_em": self.criado_em,
            "app": self.app,
            "integrity_check": self.integrity_check,
            "arquivos": self.arquivos
        }
        
        if self.base:
            data["base"] = self.base
            
        return data

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
        return result is not None and result[0] == "ok"
    finally:
        conn.close()
        
def _sha256(filepath: str) -> str:
    sha = hashlib.sha256()
    
    # Lemos em blocos de 1 MB para não carregar arquivos grandes na memória.
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()

def _parse_timestamp_from_filename(filename: str) -> Optional[datetime]:
    match = BACKUP_FILENAME_REGEX.match(filename)
    
    if not match:
        return None

    try:
        return datetime.strptime(match.group(1), BACKUP_TIMESTAMP_FORMAT)
    except ValueError:
        return None
    
def _find_current_anchor() -> Optional[dict]:
    backups = list_backups()
    
    if not backups:
        return None

    return next((b for b in backups if b["completo"]), None)

def _is_full_backup(last_anchor: Optional[dict]) -> bool:
    if last_anchor is None:
        return True
    
    last_anchor_date = datetime.fromisoformat(last_anchor["criado_em"])
    now = datetime.now()
    
    if now >= last_anchor_date + timedelta(days=MIN_DAYS_TO_COMPLETE_SAVE):
        return True
    
    return False

def _load_manifest(backup_path: str) -> dict:
    filepath = os.path.join(LOCAL_BACKUP, backup_path)
    
    with zipfile.ZipFile(filepath, "r") as zf:
        try:
            manifest = json.loads(zf.read(MANIFEST_FILENAME))
        except KeyError:
            raise BackupError(f"Manifesto não encontrado no backup: {MANIFEST_FILENAME}")
    return manifest

def _exists_file(file_in_manifest: Optional[dict], st_info) -> bool:
    if file_in_manifest is None:
        return False
    
    return (
        file_in_manifest["tamanho"] == st_info.st_size
        and file_in_manifest["mtime_ns"] == st_info.st_mtime_ns
    )        

def _referenced_backups_preserve(backups: set[str]) -> set[str]:
    
    referenced: set[str] = set()
    
    for b_path in backups:
        manifest = _load_manifest(b_path)
        for data in manifest["arquivos"].values():
            referenced.add(data["origem"])
        
    return referenced

def _join_incr_backups_to_full(backups: list[dict]) -> list[dict]:
    
    backup_chain = []
    
    for b in reversed(backups):
        if b["completo"]:
            backup_chain.append({"anchor": b, "incr": []})
        else:
            if backup_chain:
                backup_chain[-1]["incr"].append(b)
                
    backup_chain.reverse()
    
    return backup_chain
 
def list_backups() -> list[dict]:
    if not os.path.exists(LOCAL_BACKUP):
        return []

    backups = []
    for filename in os.listdir(LOCAL_BACKUP):
        ts = _parse_timestamp_from_filename(filename)
        
        if ts is None:
            continue
        
        filepath = os.path.join(LOCAL_BACKUP, filename)
        name, _ = os.path.splitext(filename)
        
        anchor = (name.endswith("_full"))
        
        backups.append({
            "arquivo": filename,
            "criado_em": ts.isoformat(),
            "tamanho_bytes": os.path.getsize(filepath),
            "completo": anchor
        })
    
    return sorted(backups, key=lambda b: b["criado_em"], reverse=True)

def get_last_backup() -> Optional[dict]:
    backups = list_backups()

    if not backups:
        return None
    return backups[0]

def create_backup(force_full: bool = False) -> dict[str, str | int]:
    os.makedirs(LOCAL_BACKUP, exist_ok=True)
    
    last_anchor = _find_current_anchor()
    
    is_full_backup = _is_full_backup(last_anchor) or force_full
    backup_type = "full" if is_full_backup else "incr"
    
    last_backup = get_last_backup() if not is_full_backup else None

    now = datetime.now()
    stored_filename = f"{BACKUP_PREFIX}{now.strftime(BACKUP_TIMESTAMP_FORMAT)}_{backup_type}.zip"
    
    stored_filepath = os.path.join(LOCAL_BACKUP, stored_filename)
    tmp_path = stored_filepath + ".tmp"
    
    # TemporaryDirectory cria uma pasta temporária e a APAGA sozinha
    with tempfile.TemporaryDirectory(prefix="startbig_bkp_") as tmpdir:
        print(f"[BACKUP] Criando snapshot do banco de dados em: {tmpdir}")
        snapshot_db_path = os.path.join(tmpdir, DB_NAME)
        _create_snapshot_db(snapshot_db_path)
        
        print(f"[BACKUP] Verificando integridade do snapshot...")
        if not _verify_integrity(snapshot_db_path):
            raise BackupError("Falha na verificação de integridade do snapshot do banco de dados.")

        print(f"[BACKUP] Empacotando snapshot e arquivos estáticos em: {stored_filename}")
        
        # O manifest guarda os metadados e checksums de cada arquivo.
        manifest = ManifestBuilder(tipo=backup_type, base= None if is_full_backup else last_backup["arquivo"])
        
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
                if os.path.isdir(STATIC_DIR):
                    
                    base_files = {}
                    if last_backup:
                       base_files = _load_manifest(last_backup["arquivo"])["arquivos"]
                    
                    # os.walk percorre a árvore de pastas recursivamente
                    for root, _, files in os.walk(STATIC_DIR):
                        for filename in files:
                            abs_path = os.path.join(root, filename)
                            rel = os.path.relpath(abs_path, STATIC_DIR)
                            arcname = os.path.join(STATIC_DIR_NO_ZIP, rel).replace(os.sep, "/")
                            st_info = os.stat(abs_path)
                            
                            data = base_files.get(arcname)
                            exists = _exists_file(data, st_info)
                            
                            if exists:
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
                
        except Exception as e:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
        
    delete_old_backups()    
        
    return {
        "arquivo": stored_filename,
        "criado_em": now.isoformat(),
        "tamanho_bytes": os.path.getsize(stored_filepath),
    }
        
def delete_old_backups() -> list[str]:
    backups = list_backups()
    if not backups:
        return []
    
    backups_chain = _join_incr_backups_to_full(backups)
    
    backups_to_save = set()

    if backups_chain:
        current = backups_chain[0]
        backups_to_save.add(current["anchor"]["arquivo"])
        for inc in current["incr"]:
            backups_to_save.add(inc["arquivo"]) 
                    
    for chain in backups_chain[1:FULL_TO_SAVE]:
        backups_to_save.add(chain["anchor"]["arquivo"])
        
    try:
        referenced_backups = _referenced_backups_preserve(backups_to_save)
    except BackupError as e:
        print(f"[BACKUP] Retenção abortada por segurança (manifest ilegível): {e}")
        return [] 
    
    guardian_backups = backups_to_save | referenced_backups
    
    for filename in referenced_backups - backups_to_save:
        print(f"[BACKUP] Aviso: '{filename}' seria descartado pela política, "
              f"mas ainda é referenciado por um backup ativo. Preservado.")
        
    removed_backups = []
    for filenames in os.listdir(LOCAL_BACKUP):
        if not BACKUP_FILENAME_REGEX.match(filenames):
            continue
        
        if filenames in guardian_backups:
            continue
        
        try:
            os.remove(os.path.join(LOCAL_BACKUP, filenames))
            removed_backups.append(filenames)
        except OSError as e:
            print(f"[BACKUP] Falha ao remover arquivo de backup {filenames}: {e}")    

    
    return removed_backups

def check_backup(backup_path: str, deep: bool = False) -> dict:    
    manifest = _load_manifest(backup_path)
    manifest_files = manifest["arquivos"]
    
    per_origins: dict[str, dict] = {}
    base_name = os.path.basename(backup_path)

    for arcname, data in manifest_files.items():
        origins = data["origem"]
        if not deep and origins != base_name:
            continue
        per_origins.setdefault(origins, {})[arcname] = data
        
    verified = 0
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
                        raise BackupError(f"Falha na verificação de integridade do arquivo {arcname} no backup {origins}")
                    
                    verified += 1
                
        if not _verify_integrity(os.path.join(tmpdir, DB_NAME)):
            raise BackupError(f"Falha na verificação de integridade do banco de dados no backup {origins}")
    return {
        "arquivo": backup_path,
        "criado_em": manifest.get("criado_em"),
        "valido": True,
        "modo": "profundo" if deep else "raso",
        "arquivos_verificados": verified,
        "total_no_manifest": len(manifest_files),
    }

def save_backup(cycle: str, filename: str, content: bytes) -> None:
    cycle_dir = os.path.join(RESTORED_BACKUP, cycle)
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
    cycle_dir = os.path.join(RESTORED_BACKUP, cycle)
    
    if target_dir is None:
        target_dir = os.path.join(cycle_dir, "_restored")
    
    os.makedirs(target_dir, exist_ok=True)
    
    last_zip_path = os.path.join(cycle_dir, ordered_filepaths[-1])
        
    if not os.path.isfile(last_zip_path):
        raise BackupError(f"Último arquivo de backup não encontrado: {last_zip_path}")
    
    zip_manifest = _load_manifest(last_zip_path)
    final_files = set(zip_manifest["arquivos"].keys())
    
    added_files = set()
    for filepath in ordered_filepaths:
        zip_filepath = os.path.join(cycle_dir, filepath)
        
        if not os.path.isfile(zip_filepath):
            raise BackupError(f"Arquivo de backup não encontrado: {zip_filepath}")
        
        with zipfile.ZipFile(zip_filepath, "r") as zf:
            if zf.testzip() is not None:
                raise BackupError(f"Falha na verificação de integridade do arquivo ZIP: {zip_filepath}")
            
            for member in zf.namelist():
                if member == MANIFEST_FILENAME:
                    continue
                if member not in final_files:
                    continue
                zf.extract(member, path=target_dir)
        added_files.add(filepath)