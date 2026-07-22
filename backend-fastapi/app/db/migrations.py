"""
Módulo de migrações automáticas via Alembic.

Aplica migrações pendentes automaticamente na inicialização do app,
substituindo o antigo sistema manual de _aplicar_migracoes().
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


def aplicar_migracoes():
    """
    Aplica migrações Alembic automaticamente na inicialização.

    Cenários:
    1. DB novo (sem tabelas): create_all já foi chamado antes,
       então basta fazer stamp("head").
    2. DB existente sem alembic_version: foi criado por create_all.
       Stamp em "head" pois create_all cria o schema completo.
    3. DB existente com alembic_version: upgrade("head") aplica
       apenas as migrações pendentes.
    """
    alembic_cfg = _criar_alembic_config()

    if not _banco_tem_tabela_alembic_version():
        logger.info(
            "Tabela alembic_version não encontrada. "
            "Registrando banco na revisão head..."
        )
        command.stamp(alembic_cfg, "head")
        logger.info("Banco registrado na revisão head com sucesso.")
    else:
        revisao_atual = _obter_revisao_atual()
        logger.info("Revisão atual do banco: %s", revisao_atual)

        # Se a revisão armazenada no banco não existe nos scripts de migração
        # (ex: o código voltou para uma versão anterior), re-stampa para head.
        if revisao_atual and not _revisao_existe_no_script(alembic_cfg, revisao_atual):
            logger.warning(
                "Revisão %s não encontrada nos scripts de migração. "
                "Re-stampando para head...",
                revisao_atual,
            )
            command.stamp(alembic_cfg, "head")
        else:
            try:
                command.upgrade(alembic_cfg, "head")
            except OperationalError as exc:
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
