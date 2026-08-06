from datetime import datetime
import hashlib

import json
import os

from app.core.config import BASE_DIR

JOURNAL_FILENAME = "cloud_backup_journal.json"

STATUS_PENDENTE = "pendente"
STATUS_ENVIANDO = "enviando"
STATUS_ENVIADO = "enviado"
STATUS_FALHOU = "falhou"
STATUS_DESCARTADO = "descartado"

def _journal_path() -> str:
    return os.path.join(BASE_DIR, JOURNAL_FILENAME)


def code_content(file_manifest: dict) -> str:
    sha256 = hashlib.sha256()
    
    for arcname in sorted(file_manifest["arquivos"]):
        data = file_manifest["arquivos"][arcname]
        sha256.update(f"{arcname}\n{data['sha256']}\n".encode("utf-8"))
    return sha256.hexdigest()

def load_journal() -> dict:
    filepath = _journal_path()
    
    if not os.path.exists(filepath):
        return {}
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if not isinstance(data, dict):
            raise ValueError("Journal não é um objeto JSON válido.")
        return data
    except (json.JSONDecodeError, ValueError, OSError) as e:
        q = f"{filepath}.corrupted-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        try:
            os.replace(filepath, q)
        except OSError:
            pass
        print(f"[SYNC] Journal ilegível ({e}). Preservado em "
              f"'{q}'; recomeçando com journal vazio.")
        
        return {}

def save_journal(journal: dict) -> None:
    filepath = _journal_path()
    
    tmp = filepath + ".tmp"
    
    try:
        with open(tmp, "w", encoding="utf-8") as f:
                json.dump(journal, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
        os.replace(tmp, filepath)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise
    
def update_journal_entry(filename: str, **fields) -> None:
    journal = load_journal()
    
    entry = journal.get(filename, {})
    entry.update(fields)
    entry["atualizado_em"] = datetime.now().isoformat()
    journal[filename] = entry
    save_journal(journal)
    return journal
    