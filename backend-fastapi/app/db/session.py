# ---------------------------------------------------------------------------
# ARQUIVO: session.py
# DESCRIÇÃO: Configura a conexão com o banco de dados e fornece um
#            gerador de sessão para ser usado como dependência no FastAPI.
# ---------------------------------------------------------------------------

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.core.config import settings # <-- Importa a instância das configurações
from app.core.busca import (
    FUNCAO_SQL_COMPACTAR,
    FUNCAO_SQL_NORMALIZAR,
    compactar,
    normalizar,
)

# --- INÍCIO DA MUDANÇA ---
# Precisamos do 'Engine' do SQLAlchemy para adicionar o listener
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Força a verificação de chaves estrangeiras no SQLite.
    Isso não afeta outros bancos de dados como PostgreSQL ou MySQL.
    """
    if dbapi_connection.__class__.__module__ == "sqlite3":
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

@event.listens_for(Engine, "connect")
def registrar_funcoes_busca(dbapi_connection, connection_record):
    """
    Ensina o SQLite a comparar texto ignorando caixa, acentos e pontuação.

    O LIKE do SQLite só é case-insensitive para ASCII e não sabe nada de
    acentos — "Açúcar" e "acucar" são strings sem relação para ele. Como não
    há extensão ICU no banco embarcado, registramos a normalização feita em
    Python como função SQL e a aplicamos dos dois lados da comparação
    (ver core/busca.py).

    O listener fica na classe Engine, e não na engine da aplicação, para
    valer também na engine em memória usada pelos testes.
    """
    if dbapi_connection.__class__.__module__ != "sqlite3":
        return

    for nome, funcao in (
        (FUNCAO_SQL_NORMALIZAR, normalizar),
        (FUNCAO_SQL_COMPACTAR, compactar),
    ):
        try:
            # 'deterministic' permite ao SQLite reaproveitar o resultado
            # dentro da mesma query; exige SQLite >= 3.8.3.
            dbapi_connection.create_function(nome, 1, funcao, deterministic=True)
        except Exception:
            dbapi_connection.create_function(nome, 1, funcao)
# --- FIM DA MUDANÇA ---

# 1. CRIAÇÃO DA ENGINE
# A 'engine' é o ponto central de comunicação com o banco de dados.
# Ela é configurada com a URL do banco, que é lida de forma segura a
# partir das variáveis de ambiente através do objeto 'settings'.
# O argumento 'connect_args={"check_same_thread": False}' é uma necessidade
# específica para o modo de operação padrão do SQLite, que não permite
# que o objeto de conexão seja compartilhado entre diferentes threads.
# FastAPI pode usar threads diferentes para uma mesma requisição,
# então esta configuração evita erros.
engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})

# 2. CRIAÇÃO DA FÁBRICA DE SESSÕES (SESSIONMAKER)
# 'SessionLocal' é uma "fábrica" de sessões. Quando chamada, ela cria
# uma nova instância de Session.
# - autocommit=False: As transações não serão comitadas automaticamente.
#   Isso nos dá controle explícito sobre quando salvar as mudanças (db.commit()).
# - autoflush=False: Os dados não serão enviados ao banco de dados
#   automaticamente antes de cada query.
# - bind=engine: Associa esta fábrica de sessões à nossa engine de banco de dados.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. DEPENDÊNCIA PARA OBTER A SESSÃO (GET_DB)
def get_db():
    """
    Função geradora que atua como uma dependência do FastAPI.
    Ela cria uma nova sessão de banco de dados para cada requisição,
    disponibiliza essa sessão para o endpoint e garante que a sessão
    seja fechada ao final da requisição, mesmo que ocorram erros.
    """
    db = SessionLocal()
    try:
        # 'yield' é o que torna esta função um gerador. Ele entrega a
        # sessão 'db' para o código do endpoint que a requisitou.
        # O código da requisição é executado aqui.
        yield db
    finally:
        # O bloco 'finally' é sempre executado após a conclusão da
        # requisição, seja ela bem-sucedida ou não.
        # Isso garante que a conexão com o banco de dados seja sempre fechada,
        # liberando os recursos.
        db.close()