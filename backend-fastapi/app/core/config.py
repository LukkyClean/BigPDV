# ---------------------------------------------------------------------------
# ARQUIVO: app/core/config.py
# DESCRIÇÃO: Configurações globais da aplicação via variáveis de ambiente.
# ---------------------------------------------------------------------------

import os
import platform
import secrets
from pydantic_settings import BaseSettings
from cryptography.fernet import Fernet

APP_NAME = "StartBigERP"
DB_NAME = "start_big.db"

# Diretório raiz do backend (backend-fastapi), calculado a partir deste arquivo:
# config.py -> core -> app -> backend-fastapi
# NAO REMOVER: app/main.py importa BACKEND_DIR daqui — sem ele o backend nem sobe
# (ImportError no import de app.main, antes de qualquer rota existir).
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# .db path — BIGPDV_DATA_DIR fixa o caminho quando o processo roda como SYSTEM
_override = os.getenv("BIGPDV_DATA_DIR")
if _override:
    data_dir = _override
    BASE_DIR = os.path.dirname(data_dir)
else:
    if platform.system() == "Windows":
        BASE_DIR = os.path.join(os.getenv("LOCALAPPDATA"), APP_NAME)
    else:
        BASE_DIR = os.path.join(os.path.expanduser("~"), f".{APP_NAME.lower()}")
    data_dir = os.path.join(BASE_DIR, "data")
os.makedirs(data_dir, exist_ok=True)

database_path = os.path.join(data_dir, DB_NAME)
sql_url = f"sqlite:///{database_path}"

secure_dir = os.path.join(data_dir, "secure")
os.makedirs(secure_dir, exist_ok=True)

def _load_or_create_encryption_key(path: str) -> bytes:
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read().strip()
        
    key = Fernet.generate_key()
    
    with open(path, "wb") as f:
        f.write(key)
    
    return key

def _load_or_create_secret_key(path: str) -> str:
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read().strip()
    key = secrets.token_urlsafe(32)
    with open(path, "w") as f:
        f.write(key)
    return key

_secret_key_value = _load_or_create_secret_key(os.path.join(data_dir, "secret.key"))
_fernet_key_value = _load_or_create_encryption_key(os.path.join(secure_dir, "fernet.key"))

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
    
    # Configurações de criptografia
    FERNET_KEY: bytes = _fernet_key_value

    # Fiscal — mock habilitado permite testar sem API real
    FISCAL_MOCK_ENABLED: bool = False

# Instância única (Singleton)
settings = Settings()