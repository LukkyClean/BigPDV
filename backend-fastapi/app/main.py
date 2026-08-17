import logging
import os
import sys

# Entrada do FastAPI

_APP_ENV = os.getenv("APP_ENV", "development").lower()
_LOG_LEVEL = logging.DEBUG if _APP_ENV == "development" else logging.INFO
logging.basicConfig(
    level=_LOG_LEVEL,
    format="%(levelname)-8s %(name)s — %(message)s",
)

from fastapi import FastAPI # type: ignore
from app.api.v1 import api
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.exceptions import setup_exception_handlers
from app.core.tarefas import lifespan
from app.core.config import BACKEND_DIR, data_dir
from app.core.migracoes_dir import migrar_estrutura_diretorios

migrar_estrutura_diretorios()

import app.db.models  # noqa: F401 — registra todos os modelos no Base.metadata

STATIC_DIR = os.path.join(data_dir, 'static')

if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)

# Diretorio do formulario mobile (extend-form)
# Em producao (PyInstaller --onefile): arquivos extraidos em sys._MEIPASS/form/
# Em dev: arquivos buildados em backend-fastapi/extend-form/dist/
if getattr(sys, 'frozen', False):
    FORM_DIR = os.path.join(sys._MEIPASS, 'form')
else:
    # os.path.dirname(__file__) e a pasta 'app/', nao a raiz do backend: apontava
    # para app/extend-form/dist, que nao existe, e o mount do /form caia calado
    # (o `if os.path.exists(FORM_DIR)` la embaixo engole o erro).
    FORM_DIR = os.path.join(BACKEND_DIR, 'extend-form', 'dist')
    
app = FastAPI(
    title="StartBig Backend API",
    description="StartBig ERP - API",
    version="1.0.0",
    lifespan=lifespan,
)

setup_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(api.router, prefix="/api/v1")

# Monta o formulario mobile APOS o include_router para nao interceptar rotas da API.
# html=True serve index.html para qualquer rota SPA que nao case com um arquivo.
if os.path.exists(FORM_DIR):
    app.mount("/form", StaticFiles(directory=FORM_DIR, html=True), name="form")

@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok"}