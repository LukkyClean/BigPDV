import hashlib
import json
import os
import re
import sqlite3
import tempfile
import zipfile

from datetime import datetime, date
from typing import Optional

from app.core.config import BASE_DIR, DB_NAME, database_path

BACKUP_DIR = os.path.join(BASE_DIR, "backups")

STATIC_DIR = os.path.join(BASE_DIR, "static")

LAST_DAYS_TO_SAVE = 7
LAST_WEEKS_TO_SAVE = 4

BACKUP_PREFIX = "backup_"
BACKUP_TIMESTAMP_FORMAT = "%Y-%m-%d_%H%M%S"
BACKUP_FILENAME_REGEX = re.compile(r"^backup_(\d{4}-\d{2}-\d{2}_\d{6})\.zip$")

MANIFEST_FILENAME = "manifest.json"
STATIC_DIR_NO_ZIP = "static"

class BackupError(Exception):
    pass

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
    
def list_backups() -> list[dict]:
    if not os.path.exists(BACKUP_DIR):
        return []

    backups = []
    for filename in os.listdir(BACKUP_DIR):
        ts = _parse_timestamp_from_filename(filename)
        
        if ts is None:
            continue
        
        filepath = os.path.join(BACKUP_DIR, filename)
        backups.append({
            "arquivo": filename,
            "criado_em": ts.isoformat(),
            "tamanho_bytes": os.path.getsize(filepath),
        })
    
    return sorted(backups, key=lambda b: b["criado_em"], reverse=True)

def get_last_backup() -> Optional[datetime]:
    backups = list_backups()

    if not backups:
        return None
    return datetime.fromisoformat(backups[0]["criado_em"])

def create_backup() -> dict[str, str | int]:
    os.makedirs(BACKUP_DIR, exist_ok=True)

    now = datetime.now()
    stored_filename = f"{BACKUP_PREFIX}{now.strftime(BACKUP_TIMESTAMP_FORMAT)}.zip"
    
    stored_filepath = os.path.join(BACKUP_DIR, stored_filename)
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
        manifest = {
            "manifest_version": 1,
            "criado_em": now.isoformat(),
            "app": "StartBigERP",
            "integrity_check": "ok",
            "arquivos" : {}
        }
        
        try:
            # ZIP_DEFLATED = com compressão
            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(snapshot_db_path, arcname=DB_NAME)
                manifest["arquivos"][DB_NAME] = _sha256(snapshot_db_path)
                
                if os.path.isdir(STATIC_DIR):
                    # os.walk percorre a árvore de pastas recursivamente
                    for root, _, files in os.walk(STATIC_DIR):
                        for filename in files:
                            abs_path = os.path.join(root, filename)
                            rel = os.path.relpath(abs_path, STATIC_DIR)
                            arcname = os.path.join(STATIC_DIR_NO_ZIP, rel).replace(os.sep, "/")
                            zf.write(abs_path, arcname=arcname)
                            manifest["arquivos"][arcname] = _sha256(abs_path)
     
                zf.writestr(MANIFEST_FILENAME, json.dumps(manifest, indent=2, ensure_ascii=False))

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
    
    diary_cutoff = backups[:LAST_DAYS_TO_SAVE]
    rest_backups = backups[LAST_DAYS_TO_SAVE:]
    
    hold_weeks: dict[tuple[int, int], dict] = {}
    for b in rest_backups:
        date = datetime.fromisoformat(b["criado_em"])
        
        day_in_calendar = date.isocalendar()
        week_key = (day_in_calendar[0], day_in_calendar[1])  # (ano, semana)
        
        if week_key not in hold_weeks:
            hold_weeks[week_key] = b
            
    sorted_weeks = sorted(hold_weeks.keys(), reverse=True)
    week_backups = [hold_weeks[k] for k in sorted_weeks[:LAST_WEEKS_TO_SAVE]]
    
    hold_backups = {b["arquivo"] for b in diary_cutoff} | {b["arquivo"] for b in week_backups}
    
    removed_files = []

    for b in backups:
        if b["arquivo"] not in hold_backups:
            filepath = os.path.join(BACKUP_DIR, b["arquivo"])
            try:
                os.remove(filepath)
                removed_files.append(b["arquivo"])
                print(f"[BACKUP] Removido backup antigo: {b['arquivo']}")
            except OSError:
                print(f"[BACKUP] Falha ao remover backup antigo: {b['arquivo']}")
        
    for name in os.listdir(BACKUP_DIR):
        if name.endswith(".tmp"):
            tmp_path = os.path.join(BACKUP_DIR, name)
            try:
                os.remove(tmp_path)
                print(f"[BACKUP] Removido arquivo temporário: {name}")
            except OSError:
                print(f"[BACKUP] Falha ao remover arquivo temporário: {name}")
    
    return removed_files

def check_backup(backup_path: str) -> dict:
    path = os.path.join(BACKUP_DIR, backup_path)
    if not os.path.isfile(path):
        raise BackupError(f"Arquivo de backup não encontrado: {backup_path}")
    
    with zipfile.ZipFile(path, "r") as zf:
        broken = zf.testzip()
        
        if broken is not None:
            raise BackupError(f"Arquivo de backup corrompido: {broken}")
        
        try:
            manifest = json.loads(zf.read(MANIFEST_FILENAME))
        except KeyError:
            raise BackupError(f"Manifesto não encontrado no backup: {MANIFEST_FILENAME}")
        
        with tempfile.TemporaryDirectory(prefix="startbig_bkp_check_") as tmpdir:
            for arcname, expected_checksum in manifest["arquivos"].items():
                zf.extract(arcname, path=tmpdir)
                extracted_path = os.path.join(tmpdir, *arcname.split("/"))
                
                if _sha256(extracted_path) != expected_checksum:
                    raise BackupError(f"Falha na verificação de integridade do arquivo: {arcname}")

            # Fora do laço (roda 1x), mas DENTRO do 'with' do TemporaryDirectory:
            # a pasta temporária só existe enquanto este bloco estiver aberto.
            db_path = os.path.join(tmpdir, DB_NAME)
            if not _verify_integrity(db_path):
                raise BackupError("Falha na verificação de integridade do banco de dados extraído do backup.")
                
    return {
        "arquivo": backup_path,
        "criado_em": manifest.get("criado_em"),
        "valido": True,
        "total_arquivos": len(manifest["arquivos"]),
    }