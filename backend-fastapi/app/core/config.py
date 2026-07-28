# ---------------------------------------------------------------------------
# ARQUIVO: app/core/config.py
# DESCRIÇÃO: Configurações globais da aplicação via variáveis de ambiente.
# ---------------------------------------------------------------------------

import os
import platform
import secrets
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

app_name = "StartBigERP"

# Diretório raiz do backend (backend-fastapi), calculado a partir deste arquivo:
# config.py -> core -> app -> backend-fastapi
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# .db path

if platform.system() == "Windows":
    BASE_DIR = os.path.join(os.getenv("LOCALAPPDATA"), app_name)
else:
    BASE_DIR = os.path.join(os.path.expanduser("~"), f".{app_name.lower()}")

data_dir = os.path.join(BASE_DIR, "data")
os.makedirs(data_dir, exist_ok=True)

database_path = os.path.join(data_dir, "start_big.db")


def _resolve_sqlite_relative(url: str, base_dir: str) -> str:
    """Converte um caminho SQLite relativo (ex: sqlite:///./start_big.db) em
    absoluto, ancorado em base_dir. Assim o banco sempre cai no mesmo lugar,
    independentemente do diretório de onde a aplicação é executada."""
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return url
    path = url[len(prefix):]
    if path.startswith("./"):
        path = path[2:]
    if not os.path.isabs(path):
        path = os.path.normpath(os.path.join(base_dir, path))
    return f"{prefix}{path}"


def _load_database_url_override() -> str | None:
    """Lê SOMENTE a variável DATABASE_URL (do ambiente ou do .env do backend),
    sem carregar o restante do .env — evitando sobrescrever a SECRET_KEY gerada.

    Em desenvolvimento, o .env aponta para ./start_big.db, deixando o banco
    visível na pasta do backend. Em produção (sem .env), usa o LOCALAPPDATA."""
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")

    env_path = os.path.join(BACKEND_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DATABASE_URL=") and not line.startswith("#"):
                    valor = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return valor or None
    return None


_db_override = _load_database_url_override()
if _db_override:
    sql_url = _resolve_sqlite_relative(_db_override, BACKEND_DIR)
else:
    sql_url = f"sqlite:///{database_path}"


def _load_or_create_secret_key(path: str) -> str:
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read().strip()
    key = secrets.token_urlsafe(32)
    with open(path, "w") as f:
        f.write(key)
    return key

_secret_key_value = _load_or_create_secret_key(os.path.join(data_dir, "secret.key"))

class Settings(BaseSettings):
    """
    Carrega e valida as variáveis de ambiente (.env).
    """
    # Banco de Dados
    DATABASE_URL: str = sql_url

    # Ambiente
    DEBUG: bool = True

    # Segurança (JWT)
    SECRET_KEY: str = _secret_key_value
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 180

# Instância única (Singleton)
settings = Settings()