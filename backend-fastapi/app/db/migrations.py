"""
Módulo de migrações automáticas via Alembic.

Aplica migrações pendentes automaticamente na inicialização do app.

O Alembic NÃO é a única autoridade sobre o schema nesta branch: o
`create_all()` do startup roda ANTES daqui e cria as tabelas que faltam a
partir dos models. As migrações precisam conviver com isso -- por isso a
cadeia é aplicada uma a uma e há uma reconciliação de colunas no fim.
"""
import logging
import logging.config
import re
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
    """Retorna UMA revisão atual do banco, ou None se não houver.

    Usa `get_current_heads()` e não `get_current_revision()`: este último
    levanta CommandError quando o banco está carimbado em mais de uma ponta,
    que é um estado legitimo aqui (ver `_revisoes_atuais`). Serve para log e
    para decidir o caminho em `aplicar_migracoes`; quem precisa do conjunto
    completo usa `_revisoes_atuais()`.
    """
    heads = _revisoes_atuais()
    return heads[0] if heads else None


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


def _e_erro_de_schema_ja_existente(exc: Exception) -> bool:
    """
    Distingue "a migração tentou criar algo que o create_all já criou" de uma
    falha real de migração. Só o primeiro caso pode ser carimbado e seguido.
    """
    msg = str(exc).lower()
    return "already exists" in msg or "duplicate column" in msg


def _revisoes_atuais() -> tuple:
    """Heads gravadas em alembic_version. Tolera o estado de MULTIPLAS heads.

    O banco desta branch fica legitimamente carimbado em mais de uma ponta: o
    historico tem raizes independentes (baseline do master e a cadeia do PDV) e
    `_corrigir_branches_inacessiveis` carimba cada uma. `get_current_revision()`
    levanta CommandError nesse estado -- por isso usamos `get_current_heads()`.
    """
    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        return tuple(sorted(context.get_current_heads()))


def _normalizar_heads(alembic_cfg: Config) -> tuple:
    """Remove de alembic_version as revisoes que sao ANCESTRAIS de outra ali.

    O Alembic recusa um alvo quando as revisoes gravadas se sobrepoem
    ("Requested revision X overlaps with other requested revisions Y"), e o
    boot inteiro morre nisso. O estado aparece quando varios `stamp` sucessivos
    acumulam linhas -- na suite de testes, porque `drop_all()` apaga as tabelas
    dos models mas NAO a alembic_version, entao o lifespan carimba de novo a
    cada TestClient; numa loja, por sequencias de upgrade/stamp de versoes
    antigas.

    Manter so as pontas e seguro: quem descende de uma revisao ja a inclui.
    """
    atuais = _revisoes_atuais()
    if len(atuais) < 2:
        return atuais

    script = ScriptDirectory.from_config(alembic_cfg)

    def e_ancestral(descendente: str, candidato: str) -> bool:
        if descendente == candidato:
            return False
        try:
            list(script.iterate_revisions(descendente, candidato))
            return True
        except Exception:
            return False

    redundantes = set()
    for ponta in atuais:
        if ponta in redundantes:
            continue
        for outra in atuais:
            if outra not in redundantes and e_ancestral(ponta, outra):
                redundantes.add(outra)

    if not redundantes:
        return atuais

    logger.info(
        "alembic_version tinha %d revisao(oes) redundante(s) (%s). "
        "Mantendo apenas as pontas.",
        len(redundantes), ", ".join(sorted(redundantes)),
    )
    with engine.begin() as conn:
        for rev in redundantes:
            conn.execute(
                text("DELETE FROM alembic_version WHERE version_num = :v"),
                {"v": rev},
            )
    return _revisoes_atuais()


class _CapturaRevisaoEmCurso(logging.Handler):
    """Anota qual revisao o Alembic comecou a aplicar por ultimo.

    O Alembic loga "Running upgrade <de> -> <para>, <titulo>" imediatamente
    ANTES de executar cada migracao. Quando uma delas estoura, este handler e a
    forma confiavel de saber QUAL foi -- necessario para carimbar so ela e
    seguir. Nao da para deduzir pelo alembic_version: numa falha ele nao avanca.
    """

    PADRAO = re.compile(r"Running upgrade\s*(\S*)\s*->\s*([0-9a-zA-Z_]+)")

    def __init__(self):
        super().__init__()
        self.ultima = None

    def emit(self, record):
        try:
            achado = self.PADRAO.search(record.getMessage())
            if achado:
                self.ultima = achado.group(2)
        except Exception:
            pass


def _aplicar_uma_a_uma(alembic_cfg: Config) -> None:
    """
    Leva o banco ate as heads SEM PULAR migracoes.

    Por que nao um `upgrade("heads")` e pronto: o create_all roda ANTES das
    migracoes e ja cria, a partir dos models, as TABELAS que faltavam. Quando o
    upgrade chega numa migracao com `op.create_table` daquela mesma tabela, o
    banco responde "already exists".

    A versao antiga tratava isso com um `stamp("head")` -- que carimba a cadeia
    inteira sem executar nada. Toda migracao pendente dali em diante era PULADA,
    incluindo as de `add_column`. E `add_column` e justamente o que o create_all
    nao conserta: ele cria tabela que falta, nunca coluna que falta em tabela
    que ja existe. Resultado: banco carimbado na head com coluna faltando -- foi
    o `no such column: configuracoes_licenca.em_carencia` da loja em 24/08/2026.

    Aqui, a cada colisao, so a revisao CULPADA e carimbada e o laco recomeca --
    as seguintes continuam sendo executadas de verdade.
    """
    # Sem isto, um alembic_version com revisao + ancestral faz o Alembic
    # recusar qualquer alvo e derruba o boot.
    _normalizar_heads(alembic_cfg)

    logger_alembic = logging.getLogger("alembic.runtime.migration")
    captura = _CapturaRevisaoEmCurso()
    logger_alembic.addHandler(captura)

    # Teto de seguranca: no pior caso uma revisao e carimbada por passada.
    try:
        maximo = len(list(ScriptDirectory.from_config(alembic_cfg).walk_revisions())) + 5
    except Exception:
        maximo = 200

    try:
        for _ in range(maximo):
            antes = _revisoes_atuais()
            captura.ultima = None
            try:
                command.upgrade(alembic_cfg, "heads")
                return
            except OperationalError as exc:
                if not _e_erro_de_schema_ja_existente(exc):
                    raise

                culpada = captura.ultima
                if not culpada:
                    logger.warning(
                        "Colisao com o schema do create_all (%s), mas nao foi "
                        "possivel identificar a revisao. Carimbando nas heads.",
                        exc,
                    )
                    command.stamp(alembic_cfg, "heads")
                    return

                logger.warning(
                    "Migracao %s encontrou schema que o create_all ja criou (%s). "
                    "Carimbando so esta revisao e seguindo para as proximas.",
                    culpada, exc,
                )
                command.stamp(alembic_cfg, culpada)

                if _revisoes_atuais() == antes:
                    logger.warning(
                        "O carimbo de %s nao avancou o banco (%s); interrompendo "
                        "para nao repetir a mesma migracao para sempre.",
                        culpada, antes,
                    )
                    return
            except SQLAlchemyError:
                raise

        logger.warning(
            "Limite de passadas atingido em _aplicar_uma_a_uma; "
            "verifique a cadeia de migracoes."
        )
    finally:
        logger_alembic.removeHandler(captura)


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
    1. DB novo (sem tabelas): create_all já criou o schema; stamp nos heads.
    2. DB existente sem alembic_version: DB legado criado por create_all.
       Stamp na baseline, depois aplica a cadeia UMA A UMA.
    3. DB existente com alembic_version válido: aplica pendentes uma a uma.
    4. Revisão desconhecida (DB de versão mais nova do app / downgrade):
       Stamp no head. Schema está à frente, colunas extras são inofensivas no SQLite.

    Em todos os casos, termina reconciliando as colunas contra os models.

    ATENÇÃO -- por que `_aplicar_uma_a_uma` e não `upgrade("head")` direto: o
    create_all roda ANTES daqui e já cria as TABELAS que faltavam. Um upgrade
    direto trava na primeira migração que recria uma dessas tabelas, e tratar
    isso com `stamp("head")` PULA todas as migrações seguintes -- inclusive os
    `add_column`, que o create_all não conserta. Foi o
    `no such column: configuracoes_licenca.em_carencia` da loja em 24/08/2026.
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
            _aplicar_uma_a_uma(alembic_cfg)
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
            # Caso normal: aplica migrações pendentes, uma a uma. A colisão com
            # o create_all é carimbada SOZINHA dentro do laço, então as
            # migrações seguintes continuam sendo executadas.
            _corrigir_branches_inacessiveis(alembic_cfg, revisao_atual)
            _aplicar_uma_a_uma(alembic_cfg)
        revisao_nova = _obter_revisao_atual()
        if revisao_nova != revisao_atual:
            logger.info("Banco atualizado: %s -> %s", revisao_atual, revisao_nova)
        else:
            logger.info("Banco já está na revisão mais recente: %s", revisao_nova)

    # Rede de segurança final: um banco pode chegar aqui carimbado na head e
    # ainda assim estar sem colunas (herança dos stamps cegos das versões
    # anteriores). Só acrescenta coluna; nunca remove nem altera dado.
    reconciliar_colunas()

    # O fileConfig() do alembic/env.py sobrescreve o root logger (level=WARNING,
    # handler próprio), silenciando logs INFO/DEBUG da aplicação. Restauramos o
    # estado original para que o basicConfig do main.py continue valendo.
    _restaurar_logging_config(_estado_logging)
