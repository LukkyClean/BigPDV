# ---------------------------------------------------------------------------
# ARQUIVO: app/core/tempo.py
# DESCRIÇÃO: Fronteira entre o horário local da loja e o horário universal
#            usado no banco.
#
# REGRA DO SISTEMA
# ----------------
# 1. Carimbos de registro (quando algo aconteceu) são gravados em UTC.
#    Todos os modelos usam `func.now()`, que no SQLite é CURRENT_TIMESTAMP —
#    UTC, e devolvido pelo SQLAlchemy como datetime ingênuo (sem fuso).
#
# 2. Datas de calendário e horários de parede escolhidos por uma pessoa
#    (o dia consultado num relatório, o horário do backup, o prazo de uma OS)
#    são LOCAIS. É o que o lojista enxerga no relógio da parede.
#
# 3. A conversão acontece aqui, na fronteira. Sem ela, um dia local vira um
#    intervalo UTC deslocado e o movimento das últimas horas do expediente
#    cai no dia seguinte.
#
# O QUE NÃO PASSA POR AQUI
# ------------------------
# Subsistemas que vivem inteiramente em horário local e nunca comparam com
# colunas do banco — backup e diário de sincronização gravam o carimbo no
# próprio nome do arquivo e comparam local com local. São coerentes como
# estão; convertê-los faria o backup das 03:00 rodar em outro horário.
#
# Comparações de prazo (`data_previsao` de OS contra hoje) também ficam de
# fora: prazo é data de calendário definida por pessoa, e o critério correto
# é a data local.
# ---------------------------------------------------------------------------

from datetime import date, datetime, time, timedelta, timezone, tzinfo


def agora_utc() -> datetime:
    """
    Instante atual em UTC, ingênuo — no mesmo formato das colunas do banco.

    Substitui `datetime.utcnow()`, descontinuado desde o Python 3.12.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hoje_local() -> date:
    """Data de calendário da loja, pelo relógio do computador."""
    return datetime.now().date()


def local_para_utc(momento_local: datetime, fuso: tzinfo | None = None) -> datetime:
    """
    Converte um instante local ingênuo no equivalente em UTC, ingênuo.

    Sem `fuso`, usa `astimezone`, que aplica o deslocamento vigente no próprio
    instante convertido — respeita horário de verão sem precisar de tabela.
    É o caminho de produção.

    `fuso` existe para os testes fixarem um deslocamento conhecido sem depender
    do relógio da máquina onde a suíte roda. A aplicação nunca o informa.
    """
    if fuso is not None:
        return momento_local.replace(tzinfo=fuso).astimezone(timezone.utc).replace(tzinfo=None)
    return momento_local.astimezone(timezone.utc).replace(tzinfo=None)


def intervalo_utc(
    inicio: date, fim: date, fuso: tzinfo | None = None,
) -> tuple[datetime, datetime]:
    """
    Converte um intervalo de datas locais nos limites UTC correspondentes.

    Recebe as datas como o usuário as entende (dias do calendário da loja) e
    devolve o par de instantes para comparar com as colunas do banco.

    Exemplo em UTC-3: o dia 02/09 local vai de 02/09 03:00 a 03/09 02:59:59
    em UTC — que é exatamente onde estão as vendas daquele dia.
    """
    return (
        local_para_utc(datetime.combine(inicio, time.min), fuso),
        local_para_utc(datetime.combine(fim, time.max), fuso),
    )


def inicio_do_dia_utc(dia: date, fuso: tzinfo | None = None) -> datetime:
    """Primeiro instante de um dia local, expresso em UTC."""
    return local_para_utc(datetime.combine(dia, time.min), fuso)


def fim_do_dia_utc(dia: date, fuso: tzinfo | None = None) -> datetime:
    """Último instante de um dia local, expresso em UTC."""
    return local_para_utc(datetime.combine(dia, time.max), fuso)


def limite_utc_ha(dias: int = 0, horas: int = 0) -> datetime:
    """
    Instante de N dias/horas atrás, em UTC.

    Para regras de expiração que comparam contra colunas do banco. Usar
    `datetime.now()` aqui erraria pelo deslocamento do fuso.
    """
    return agora_utc() - timedelta(days=dias, hours=horas)
