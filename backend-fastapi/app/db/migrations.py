"""
Módulo de migrações automáticas via Alembic.

Aplica migrações pendentes automaticamente na inicialização do app.
O Alembic é a única autoridade sobre o schema do banco de dados.
"""
import logging
import logging.config
import os
import sys

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine

logger = logging.getLogger(__name__)


def _salvar_logging_config():
    """Salva o estado dos loggers antes do Alembic sobrescrevê-los.

    O fileConfig() do alembic/env.py usa disable_existing_loggers=True (padrão),
    o que desabilita TODOS os loggers existentes que não estão no alembic.ini
    (incluindo uvicorn, uvicorn.error, uvicorn.access e os loggers da app).
    """
    root = logging.getLogger()
    manager = root.manager
    # Salva o estado de todos os loggers existentes
    loggers_estado = {}
    for name, lg in manager.loggerDict.items():
        if isinstance(lg, logging.Logger):
            loggers_estado[name] = lg.disabled
    return {
        "level": root.level,
        "handlers": list(root.handlers),
        "loggers_disabled": loggers_estado,
    }


def _restaurar_logging_config(estado):
    """Restaura os loggers ao estado salvo (desfaz o fileConfig do Alembic)."""
    root = logging.getLogger()
    root.setLevel(estado["level"])
    root.handlers = estado["handlers"]
    # Re-habilita loggers que foram desabilitados pelo fileConfig
    for name, was_disabled in estado["loggers_disabled"].items():
        lg = logging.getLogger(name)
        lg.disabled = was_disabled


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
    """Retorna o ID da baseline canônica (nova baseline, criada em 07/08/2026).

    O diretório versions pode conter chains antigas (51db61228566, 5cf42db01be6)
    que foram substituídas por esta baseline. get_bases() retornaria múltiplas
    raízes, então usamos o ID fixo da baseline canônica.
    """
    return "b386f0ba5efd"


def _corrigir_branches_inacessiveis(alembic_cfg: Config, revisao_atual: str | None) -> None:
    """Registra via stamp branches que não são acessíveis a partir da revisão atual.

    Cenário típico: dois conjuntos de migrations de branches git diferentes foram
    unidos por merge sem um merge migration alembic. O create_all() do startup já
    criou o schema completo (incluindo colunas das migrations inacessíveis), então
    o stamp é seguro — apenas sincroniza o alembic_version com a realidade.

    Verifica apenas os parents diretos do(s) head(s) atual(is), que é onde o
    problema se manifesta (merge migrations com parent em branch inacessível).
    """
    if not revisao_atual:
        return

    script = ScriptDirectory.from_config(alembic_cfg)
    heads = list(script.get_heads())

    for head_id in heads:
        rev = script.get_revision(head_id)
        parents = rev.down_revision
        if not parents:
            continue
        if isinstance(parents, str):
            parents = (parents,)

        for parent_id in parents:
            # Verifica se parent_id e revisao_atual estão na mesma chain de
            # ancestralidade (qualquer direção). Se estiverem, o upgrade normal
            # é suficiente — sem necessidade de stamp.
            na_mesma_chain = False
            for upper, lower in [(parent_id, revisao_atual), (revisao_atual, parent_id)]:
                try:
                    list(script.iterate_revisions(upper, lower))
                    na_mesma_chain = True
                    break
                except Exception:
                    pass

            if not na_mesma_chain:
                logger.info(
                    "Branch '%s' não é acessível a partir de '%s'. "
                    "Registrando via stamp (schema já criado pelo create_all).",
                    parent_id,
                    revisao_atual,
                )
                command.stamp(alembic_cfg, parent_id)


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
    _estado_logging = _salvar_logging_config()

    if not _banco_tem_tabela_alembic_version():
        insp = inspect(engine)
        tabelas_existentes = [
            t for t in insp.get_table_names() if t != "alembic_version"
        ]

        if len(tabelas_existentes) == 0:
            # DB completamente novo: create_all() já criou o schema completo.
            # Stamp em todos os heads para evitar re-executar migrations que
            # criariam tabelas que já existem; depois upgrade aplica apenas o
            # merge migration (no-op) que une as chains.
            logger.info("Banco novo detectado. Registrando heads e aplicando merge...")
            command.stamp(alembic_cfg, "heads")
            command.upgrade(alembic_cfg, "head")
        else:
            # DB legado (criado por create_all): schema já existe
            logger.info(
                "Banco legado detectado (sem alembic_version, %d tabelas). "
                "Registrando na baseline e aplicando migrações pendentes...",
                len(tabelas_existentes),
            )
            command.stamp(alembic_cfg, baseline)
            _corrigir_branches_inacessiveis(alembic_cfg, baseline)
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
            _corrigir_branches_inacessiveis(alembic_cfg, revisao_atual)
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

    # O fileConfig() do alembic/env.py sobrescreve o root logger (level=WARNING,
    # handler próprio), silenciando logs INFO/DEBUG da aplicação. Restauramos o
    # estado original para que o basicConfig do main.py continue valendo.
    _restaurar_logging_config(_estado_logging)
