import hashlib
import json
import logging
import os
from datetime import datetime

from app.core.config import BASE_DIR

logger = logging.getLogger(__name__)

JOURNAL_FILENAME = "cloud_backup_journal.json"
JOURNAL_PATH = os.path.join(BASE_DIR, JOURNAL_FILENAME)

STATUS_PENDENTE = "pendente"
STATUS_ENVIANDO = "enviando"
STATUS_ENVIADO = "enviado"
STATUS_FALHOU = "falhou"
STATUS_DESCARTADO = "descartado"


def code_content(file_manifest: dict) -> str:
    sha256 = hashlib.sha256()
    for arcname in sorted(file_manifest["arquivos"]):
        data = file_manifest["arquivos"][arcname]
        sha256.update(f"{arcname}\n{data['sha256']}\n".encode("utf-8"))
    return sha256.hexdigest()


def load_journal() -> dict:
    if not os.path.exists(JOURNAL_PATH):
        return {}
    try:
        with open(JOURNAL_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Journal não é um objeto JSON válido.")
        return data
    except (json.JSONDecodeError, ValueError, OSError) as e:
        corrupted = f"{JOURNAL_PATH}.corrupted-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            os.replace(JOURNAL_PATH, corrupted)
        except OSError:
            pass
        logger.warning(
            "[SYNC] Journal ilegível (%s). Preservado em '%s'; recomeçando com journal vazio.",
            e, corrupted,
        )
        return {}


def save_journal(journal: dict) -> None:
    tmp = JOURNAL_PATH + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(journal, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, JOURNAL_PATH)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise


def update_journal_entry(filename: str, **fields) -> dict:
    journal = load_journal()
    entry = journal.get(filename, {})
    entry.update(fields)
    entry["atualizado_em"] = datetime.now().isoformat()
    journal[filename] = entry
    save_journal(journal)
    return journal


def get_ciclos_enviados() -> list[dict]:
    """Agrega entradas do journal em ciclos, retornando apenas os enviados."""
    journal = load_journal()
    ciclos: dict[str, dict] = {}

    for filename, entry in journal.items():
        if entry.get("status") != STATUS_ENVIADO:
            continue
        ciclo = entry.get("ciclo")
        if not ciclo:
            continue

        if ciclo not in ciclos:
            ciclos[ciclo] = {
                "ciclo": ciclo,
                "quantidade_backups": 0,
                "ultimo_envio": "",
                "arquivos": [],
            }

        ciclos[ciclo]["quantidade_backups"] += 1
        ciclos[ciclo]["arquivos"].append(filename)

        confirmado_em = entry.get("confirmadoEm", "")
        if confirmado_em > ciclos[ciclo]["ultimo_envio"]:
            ciclos[ciclo]["ultimo_envio"] = confirmado_em

    return sorted(ciclos.values(), key=lambda c: c["ciclo"], reverse=True)
