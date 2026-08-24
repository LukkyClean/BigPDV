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
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.core.config import settings
from app.db.base import Base
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


def _e_erro_de_schema_ja_existente(exc: Exception) -> bool:
    """
    Distingue "a migração tentou criar algo que o create_all já criou" de uma
    falha real de migração. Só o primeiro caso pode ser carimbado e seguido.
    """
    msg = str(exc).lower()
    return "already exists" in msg or "duplicate column" in msg


def _aplicar_uma_a_uma(alembic_cfg: Config) -> None:
    """
    Avança a cadeia de migrações UMA POR VEZ.

    Por que não um `upgrade("head")` direto: o create_all roda ANTES das
    migrações e já cria, a partir dos models, as TABELAS que faltavam. Quando o
    upgrade chega numa migração com `op.create_table` daquela mesma tabela, o
    banco responde "already exists".

    A versão antiga tratava isso com um `stamp("head")` -- que carimba a cadeia
    inteira sem executar nada. Toda migração pendente dali em diante era PULADA,
    incluindo as de `add_column`. E `add_column` é justamente o que o create_all
    nao conserta: ele cria tabela que falta, nunca coluna que falta em tabela
    que ja existe. Resultado: banco carimbado na head com coluna faltando -- foi
    o `no such column: configuracoes_licenca.em_carencia` da loja em 24/08/2026.

    Aqui a migração que colide com o create_all é carimbada SOZINHA (`stamp +1`)
    e o boot segue aplicando as seguintes.
    """
    while True:
        antes = _obter_revisao_atual()

        try:
            command.upgrade(alembic_cfg, "+1")
        except OperationalError as exc:
            if not _e_erro_de_schema_ja_existente(exc):
                raise
            logger.warning(
                "Migração encontrou schema que o create_all já criou (%s). "
                "Carimbando só esta revisão e seguindo para as próximas.",
                exc,
            )
            command.stamp(alembic_cfg, "+1")
        except SQLAlchemyError:
            raise
        except Exception as exc:
            # "+1" sem destino: chegamos na head. Alembic sinaliza isso com
            # CommandError, que não é erro de banco.
            logger.info("Fim da cadeia de migrações (%s).", exc)
            return

        depois = _obter_revisao_atual()
        if depois == antes:
            # Trava de segurança: sem avanço, o laço seria infinito.
            logger.warning(
                "Migração não avançou a partir de %s; interrompendo o laço.", antes
            )
            return


def _ddl_da_coluna(coluna) -> str | None:
    """
    Monta o `ADD COLUMN` para uma coluna ausente, respeitando os limites do
    SQLite: nada de PRIMARY KEY/UNIQUE, e NOT NULL só com default constante.

    Devolve None quando a coluna não pode ser acrescentada com segurança --
    nesse caso o chamador registra e deixa para decisão humana.
    """
    if coluna.primary_key or coluna.unique:
        return None

    tipo = coluna.type.compile(engine.dialect)
    ddl = '"{}" {}'.format(coluna.name, tipo)

    padrao = None
    if coluna.server_default is not None:
        texto = getattr(coluna.server_default, "arg", None)
        padrao = str(getattr(texto, "text", texto)) if texto is not None else None
    elif coluna.default is not None and getattr(coluna.default, "is_scalar", False):
        valor = coluna.default.arg
        if isinstance(valor, bool):
            padrao = "1" if valor else "0"
        elif isinstance(valor, (int, float)):
            padrao = str(valor)
        elif isinstance(valor, str):
            escapado = valor.replace("'", "''")
            padrao = "'{}'".format(escapado)

    if padrao is not None:
        ddl += " DEFAULT {}".format(padrao)

    if not coluna.nullable and padrao is None:
        # SQLite recusa ADD COLUMN NOT NULL sem default constante.
        return None

    # NOT NULL é omitido de propósito: a coluna nasce vazia nas linhas antigas.
    return ddl


def reconciliar_colunas() -> None:
    """
    Rede de segurança: compara os models com o schema real e acrescenta as
    colunas que faltarem.

    Existe porque um banco pode chegar aqui já carimbado na head e mesmo assim
    estar sem colunas -- resultado do `stamp("head")` cego que esta versão
    removeu. Sem isto, esses bancos só se consertariam com ALTER TABLE na mão,
    máquina por máquina.

    SÓ ACRESCENTA. Nunca remove coluna, nunca altera tipo, nunca toca em dado.
    Falhar aqui não derruba o boot: o app sobe e o erro fica no log.
    """
    try:
        insp = inspect(engine)
        tabelas = set(insp.get_table_names())

        pendentes = []
        for tabela in Base.metadata.sorted_tables:
            if tabela.name not in tabelas:
                # Tabela ausente é assunto do create_all, não daqui.
                continue
            reais = {c["name"] for c in insp.get_columns(tabela.name)}
            for coluna in tabela.columns:
                if coluna.name not in reais:
                    pendentes.append((tabela.name, coluna))

        if not pendentes:
            logger.info("Reconciliação: schema em dia com os models.")
            return

        logger.warning(
            "Reconciliação: %d coluna(s) ausente(s) no banco. Acrescentando...",
            len(pendentes),
        )

        adicionadas, manuais = 0, []
        for nome_tabela, coluna in pendentes:
            ddl = _ddl_da_coluna(coluna)
            if ddl is None:
                manuais.append("{}.{}".format(nome_tabela, coluna.name))
                continue
            try:
                with engine.begin() as conn:
                    conn.execute(
                        text('ALTER TABLE "{}" ADD COLUMN {}'.format(nome_tabela, ddl))
                    )
                logger.warning(
                    "Reconciliação: %s.%s criada.", nome_tabela, coluna.name
                )
                adicionadas += 1
            except SQLAlchemyError as exc:
                manuais.append("{}.{}".format(nome_tabela, coluna.name))
                logger.error(
                    "Reconciliação: falhou em %s.%s: %s",
                    nome_tabela,
                    coluna.name,
                    exc,
                )

        logger.warning("Reconciliação: %d coluna(s) acrescentada(s).", adicionadas)
        if manuais:
            logger.error(
                "Reconciliação: %d coluna(s) exigem decisão manual (NOT NULL sem "
                "default, PK ou UNIQUE): %s",
                len(manuais),
                ", ".join(manuais),
            )
    except Exception as exc:
        # Nunca impedir o boot por causa da rede de segurança.
        logger.error("Reconciliação de colunas falhou: %s", exc)


def aplicar_migracoes():
    """
    Aplica migrações Alembic automaticamente na inicialização.

    Cenários:
    1. DB novo (sem tabelas): create_all já foi chamado antes,
       então basta fazer stamp("head").
    2. DB existente sem alembic_version: foi criado por create_all.
       Stamp em "head" pois create_all cria o schema completo.
    3. DB existente com alembic_version: aplica as migrações pendentes,
       uma a uma (ver _aplicar_uma_a_uma).

    Em todos os casos, termina reconciliando as colunas contra os models.
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

        if revisao_atual and not _revisao_existe_no_script(alembic_cfg, revisao_atual):
            # Banco de outra linhagem (ex.: baseline do master). Andar a cadeia
            # daqui é impossível; o create_all já garantiu as tabelas e a
            # reconciliação abaixo cuida das colunas.
            logger.warning(
                "Revisão %s não existe nos scripts desta versão. "
                "Registrando na head e deixando o resto para a reconciliação.",
                revisao_atual,
            )
            command.stamp(alembic_cfg, "head")
        else:
            _aplicar_uma_a_uma(alembic_cfg)

        revisao_nova = _obter_revisao_atual()
        if revisao_nova != revisao_atual:
            logger.info("Banco atualizado: %s -> %s", revisao_atual, revisao_nova)
        else:
            logger.info("Banco já está na revisão mais recente: %s", revisao_nova)

    reconciliar_colunas()
