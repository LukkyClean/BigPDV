# ---------------------------------------------------------------------------
# ARQUIVO: app/core/tempo.py
# DESCRICAO: Conversao entre o dia da LOJA e o instante gravado no banco.
# ---------------------------------------------------------------------------

# O PROBLEMA QUE ESTE ARQUIVO RESOLVE
# ===========================================================================
# O banco grava timestamps em UTC (`func.now()` no SQLite e CURRENT_TIMESTAMP,
# que e UTC). Ja a pergunta que o usuario faz e sempre sobre o dia DELE:
# "quanto vendi hoje?" quer dizer o dia do calendario da loja, nao o dia UTC.
#
# Enquanto os dois coincidem, ninguem percebe. No Brasil (UTC-3) eles deixam de
# coincidir todo dia as 21h: uma venda feita as 21h30 de 15/08 e gravada como
# 00h30 de 16/08. Filtrar "15/08" sem converter perde essa venda -- e ela
# reaparece no relatorio do dia seguinte. Na pratica, ~3h de faturamento saem
# do dia certo todas as noites.
#
# A regra deste modulo: as BORDAS do dia sao definidas no fuso da loja e
# convertidas para UTC antes de irem ao banco.
#
# ATENCAO -- nem toda coluna de data e um instante:
#   * `criado_em`, `data_criacao`, `data_pagamento`  -> INSTANTE em UTC.
#     Comparar sempre com valores convertidos daqui.
#   * `data_previsao`                                -> DATA PURA de calendario,
#     escolhida por uma pessoa. NAO converter: 20/08 e 20/08 em qualquer fuso.
#     Para essas, usar `hoje_local()` direto.

import os
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from typing import Optional, Tuple
from zoneinfo import ZoneInfo


def _offset_fixo(valor: str) -> Optional[tzinfo]:
    """Interpreta '-03:00', '+05:30', '-3' como deslocamento fixo."""
    texto = valor.strip()
    if not texto or texto[0] not in "+-":
        return None
    sinal = -1 if texto[0] == "-" else 1
    corpo = texto[1:]
    try:
        if ":" in corpo:
            horas_txt, minutos_txt = corpo.split(":", 1)
            horas, minutos = int(horas_txt), int(minutos_txt)
        else:
            horas, minutos = int(corpo), 0
    except ValueError:
        return None
    if not (0 <= horas <= 14 and 0 <= minutos < 60):
        return None
    return timezone(sinal * timedelta(hours=horas, minutes=minutos))


def _fuso_configurado() -> Optional[tzinfo]:
    """Fuso vindo da variavel STARTBIG_TZ, quando houver.

    Existe por dois motivos: permitir corrigir uma maquina de loja com fuso de
    sistema errado sem reinstalar nada, e permitir que o teste reproduza o
    horario da noite (que e quando o bug aparece) sem depender do relogio da
    maquina que roda a suite.

    Aceita DUAS formas, e a ordem importa:
      1. Deslocamento fixo: '-03:00'. Funciona em qualquer maquina.
      2. Nome IANA: 'America/Sao_Paulo'. So funciona se o banco de fusos
         estiver disponivel -- e o WINDOWS NAO O TRAZ. Sem o pacote `tzdata`,
         `ZoneInfo` levanta ZoneInfoNotFoundError em toda maquina de loja.
    Por isso o deslocamento fixo vem primeiro e e a forma recomendada: o Brasil
    nao tem horario de verao desde 2019, entao '-03:00' e exato o ano inteiro e
    nao custa uma dependencia nova no instalador.
    """
    valor = os.getenv("STARTBIG_TZ")
    if not valor:
        return None
    fixo = _offset_fixo(valor)
    if fixo is not None:
        return fixo
    try:
        return ZoneInfo(valor)
    except Exception:
        # Fuso invalido nao pode derrubar relatorio: cai no fuso do sistema.
        return None


def fuso_local() -> tzinfo:
    """Fuso da loja. Padrao: o do proprio servidor, que fica dentro da loja."""
    return _fuso_configurado() or (datetime.now().astimezone().tzinfo or timezone.utc)


def para_utc(dt_local: datetime) -> datetime:
    """datetime ingenuo no fuso da loja -> datetime ingenuo em UTC.

    Devolve ingenuo (sem tzinfo) de proposito: e assim que as colunas do banco
    estao gravadas, e misturar aware com naive numa comparacao do SQLAlchemy
    levanta TypeError.
    """
    configurado = _fuso_configurado()
    if configurado is not None:
        return dt_local.replace(tzinfo=configurado).astimezone(timezone.utc).replace(tzinfo=None)
    # Sem override, `astimezone` interpreta o ingenuo como hora local do
    # sistema -- e usa o deslocamento correto para AQUELA data, nao o de hoje.
    return dt_local.astimezone(timezone.utc).replace(tzinfo=None)


def hoje_local() -> date:
    """O dia de hoje no calendario da loja."""
    return datetime.now(fuso_local()).date()


def agora_utc() -> datetime:
    """Instante atual em UTC, ingenuo -- comparavel com as colunas do banco."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def inicio_do_dia_utc(dia: date) -> datetime:
    """00:00:00 do dia na loja, expresso em UTC."""
    return para_utc(datetime.combine(dia, time.min))


def fim_do_dia_utc(dia: date) -> datetime:
    """23:59:59.999999 do dia na loja, expresso em UTC."""
    return para_utc(datetime.combine(dia, time.max))


def intervalo_utc(inicio: date, fim: date) -> Tuple[datetime, datetime]:
    """Intervalo fechado [inicio, fim] em dias da loja, convertido para UTC.

    E a funcao que os relatorios usam: eles recebem duas datas do frontend (que
    sao datas locais) e precisam de duas bordas em UTC.
    """
    return inicio_do_dia_utc(inicio), fim_do_dia_utc(fim)


def data_local_sql(coluna):
    """Expressao SQL que extrai a DATA LOCAL de uma coluna gravada em UTC.

    Para agrupar por dia -- `GROUP BY func.date(coluna)` -- nao basta ter
    convertido as bordas do periodo. `date()` no SQLite le a coluna como esta
    gravada, ou seja em UTC, e a venda das 22:30 de 09/03 (01:30 UTC de 10/03)
    e agrupada em 10/03.

    O efeito era estranho de diagnosticar, porque o total do periodo saia
    CERTO: a janela ja era convertida pelo `intervalo_utc`. Errada era so a
    quebra por dia, e as duas viajavam na MESMA resposta -- o numero grande nao
    batia com a soma das linhas logo abaixo dele.

    Vale para o relatorio de faturamento e para o grafico da Home.

    LIMITE CONHECIDO: usa o deslocamento vigente no momento da consulta, e o
    aplica a todo o periodo. O Brasil nao tem mais horario de verao, entao aqui
    isso nao muda nada; num fuso que tenha, um relatorio que atravesse a virada
    erraria por uma hora nas linhas da fronteira. Resolver de verdade exigiria
    converter linha a linha, o que o SQLite nao faz sem tabela de fusos.
    """
    from sqlalchemy import func

    offset = datetime.now(fuso_local()).utcoffset() or timedelta(0)
    minutos = int(offset.total_seconds() // 60)
    # SQLite aceita modificadores como '-180 minutes' direto no date().
    return func.date(coluna, f"{minutos} minutes")
