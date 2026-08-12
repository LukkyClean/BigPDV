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
        BASE_DIR = os.path.join(os.getenv("LOCALAPPDATA"), app_name)
    else:
        BASE_DIR = os.path.join(os.path.expanduser("~"), f".{app_name.lower()}")
    data_dir = os.path.join(BASE_DIR, "data")
os.makedirs(data_dir, exist_ok=True)

# NOME CANONICO DO BANCO: start_big.db. Nao renomeie sem deixar o nome antigo na
# lista de legados abaixo.
#
# O commit 7b8d129 gravou "startbig.db" (sem underscore) no master e o exe gerado
# a partir dali passou a procurar esse nome. Como o startup roda
# Base.metadata.create_all() (app/core/tarefas.py), um nome que nao existe nao da
# erro: ele CRIA um banco vazio ao lado do de verdade. O sintoma nao parece perda de
# banco, parece que o sistema "nao reconhece mais o usuario e a senha" — foi o que
# derrubou o servidor da loja em 28/07/2026.
#
# O fallback abaixo nao move nem copia arquivo: so aponta a URL para o banco legado.
# Nao ha backup automatico antes das migracoes, entao mexer no arquivo do cliente e
# risco desnecessario.
DB_FILENAME = "start_big.db"
LEGACY_DB_FILENAMES = ("startbig.db",)

# Alias do nome canonico. O modulo de backup (services/backup.py, vindo do
# master) importa DB_NAME e o usa como arcname do banco DENTRO do zip e como
# nome do arquivo esperado no staging da restauracao.
#
# E de proposito que ele nao aponte para o basename de `database_path`: se a
# loja ainda estiver no banco legado, o zip continua sendo gravado com o nome
# canonico, e a restauracao escreve por cima de `database_path` (o caminho
# real, legado ou nao). Amarrar DB_NAME ao legado propagaria o nome errado
# para dentro dos backups e para a nuvem.
DB_NAME = DB_FILENAME

database_path = os.path.join(data_dir, DB_FILENAME)

if not os.path.exists(database_path):
    for _legado in LEGACY_DB_FILENAMES:
        _caminho_legado = os.path.join(data_dir, _legado)
        if os.path.exists(_caminho_legado):
            print(f"[config] Banco canonico '{DB_FILENAME}' nao encontrado; usando banco legado '{_legado}'.")
            database_path = _caminho_legado
            break


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


# Precedencia: .env/DATABASE_URL (so existe em dev) > BIGPDV_DATA_DIR > LOCALAPPDATA.
# No app instalado nao ha .env dentro do bundle (run.spec nao o empacota), entao o
# caminho efetivo e sempre o data_dir — que o --data-dir fixa quando a tarefa roda
# como SYSTEM.
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