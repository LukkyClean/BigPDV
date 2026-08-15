"""
Módulo de migrações automáticas via Alembic.

Aplica migrações pendentes automaticamente na inicialização do app.
O Alembic é a única autoridade sobre o schema do banco de dados.
"""
import logging
import os
import sys

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.db.session import engine

logger = logging.getLogger(__name__)


def _criar_alembic_config() -> Config:
    """
    Cria um objeto alembic.Config programaticamente,
    apontando para o alembic.ini e sobrescrevendo a URL do banco.
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller: arquivos empacotados ficam em sys._MEIPASS
        backend_dir = sys._MEIPASS
    else:
        backend_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

    ini_path = os.path.join(backend_dir, "alembic.ini")
    alembic_cfg = Config(ini_path)
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    alembic_cfg.set_main_option(
        "script_location", os.path.join(backend_dir, "alembic")
    )
    return alembic_cfg


def _banco_tem_tabela_alembic_version() -> bool:
    """Verifica se a tabela alembic_version existe no banco."""
    insp = inspect(engine)
    return "alembic_version" in insp.get_table_names()


def _obter_revisao_atual() -> str | None:
    """Retorna a revisão atual do banco, ou None se não houver."""
    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        return context.get_current_revision()


def _revisao_existe_no_script(alembic_cfg: Config, revisao: str) -> bool:
    """Verifica se a revisão armazenada no banco existe nos scripts de migração."""
    script = ScriptDirectory.from_config(alembic_cfg)
    try:
        script.get_revision(revisao)
        return True
    except Exception:
        return False


def _obter_revisao_baseline(alembic_cfg: Config) -> str:
    """Retorna o ID da primeira migração (baseline, sem down_revision)."""
    script = ScriptDirectory.from_config(alembic_cfg)
    bases = list(script.get_bases())
    if not bases:
        raise RuntimeError("Nenhuma migração encontrada no diretório de versões.")
    return bases[0]


def aplicar_migracoes():
    """
    Aplica migrações Alembic automaticamente na inicialização.

    Cenários:
    1. DB novo (sem tabelas): upgrade("head") cria tudo via migrações.
    2. DB existente sem alembic_version: DB legado criado por create_all.
       Stamp na baseline, depois upgrade("head") para migrações adicionais.
    3. DB existente com alembic_version válido: upgrade("head") aplica pendentes.
    4. Revisão desconhecida (DB de versão mais nova do app / downgrade):
       Stamp no head. Schema está à frente, colunas extras são inofensivas no SQLite.
    """
    alembic_cfg = _criar_alembic_config()
    baseline = _obter_revisao_baseline(alembic_cfg)

    if not _banco_tem_tabela_alembic_version():
        insp = inspect(engine)
        tabelas_existentes = [
            t for t in insp.get_table_names() if t != "alembic_version"
        ]

        if len(tabelas_existentes) == 0:
            # DB completamente novo: upgrade cria tudo desde a baseline
            logger.info("Banco novo detectado. Aplicando migrações desde o início...")
            command.upgrade(alembic_cfg, "head")
        else:
            # DB legado (criado por create_all): schema já existe
            logger.info(
                "Banco legado detectado (sem alembic_version, %d tabelas). "
                "Registrando na baseline e aplicando migrações pendentes...",
                len(tabelas_existentes),
            )
            command.stamp(alembic_cfg, baseline)
            command.upgrade(alembic_cfg, "head")
    else:
        revisao_atual = _obter_revisao_atual()
        logger.info("Revisão atual do banco: %s", revisao_atual)

        if revisao_atual and not _revisao_existe_no_script(alembic_cfg, revisao_atual):
            # DB provavelmente vem de uma versão mais nova do app (downgrade).
            # Stamp no head para evitar recriar tabelas que já existem.
            # Colunas extras no SQLite são inofensivas (SQLAlchemy ignora).
            logger.warning(
                "Revisão %s não encontrada nos scripts de migração. "
                "Provavelmente o banco vem de uma versão mais recente do app. "
                "Registrando no head atual para evitar conflitos...",
                revisao_atual,
            )
            command.stamp(alembic_cfg, "head", purge=True)
        else:
            # Caso normal: aplica migrações pendentes
        try:
            command.upgrade(alembic_cfg, "head")
        except OperationalError as exc:
            # create_all roda ANTES das migrações e já cria o schema completo a
            # partir dos models. Quando o histórico tem galhos unidos depois
            # (ex.: merge de heads oficina/vendas), o upgrade pode tentar recriar
            # tabelas/colunas que o create_all já criou -> "already exists". Nesse
            # caso o schema já está correto; basta registrar o banco na head, do
            # mesmo jeito que já fazemos para bancos sem alembic_version. Qualquer
            # outro erro sobe (não mascaramos falha real de migração).
            msg = str(exc).lower()
            if "already exists" in msg or "duplicate column" in msg:
                logger.warning(
                    "Upgrade encontrou schema já existente (create_all): %s. "
                    "Registrando o banco na head via stamp.",
                    exc,
                )
                command.stamp(alembic_cfg, "head")
            else:
                raise
        revisao_nova = _obter_revisao_atual()
        if revisao_nova != revisao_atual:
            logger.info("Banco atualizado: %s -> %s", revisao_atual, revisao_nova)
        else:
            logger.info("Banco já está na revisão mais recente: %s", revisao_nova)
