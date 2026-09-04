# ---------------------------------------------------------------------------
# ARQUIVO: test/core/test_tempo.py
# DESCRIÇÃO: Testes da fronteira entre horário local e horário universal.
#
# O relógio é FIXADO em cada teste. Sem isso o resultado passa a depender da
# hora em que a suíte roda — foi exatamente assim que o defeito de fuso ficou
# escondido: os testes só falhavam entre 21h e meia-noite.
# ---------------------------------------------------------------------------

from datetime import date, datetime, timedelta, timezone

import pytest

from app.core.tempo import (
    agora_utc,
    fim_do_dia_utc,
    hoje_local,
    inicio_do_dia_utc,
    intervalo_utc,
    limite_utc_ha,
    local_para_utc,
)


# Deslocamento fixo de Brasília. O Brasil não tem horário de verão desde 2019,
# então um offset fixo descreve o fuso com precisão para estes testes — e roda
# em qualquer sistema operacional, sem depender de tzset nem do pacote tzdata.
#
# Fixar o fuso explicitamente é o ponto central: se o teste dependesse do
# relógio da máquina, ele só falharia entre 21h e meia-noite, que foi
# exatamente como o defeito passou despercebido.
BRT = timezone(timedelta(hours=-3))


# =========================
# 1. Conversão de instante
# =========================

def test_agora_utc_e_ingenuo_para_bater_com_as_colunas():
    """
    As colunas do banco vêm do SQLite como datetime sem fuso. Devolver um
    valor com fuso aqui faria toda comparação levantar TypeError.
    """
    assert agora_utc().tzinfo is None


def test_agora_utc_esta_proximo_do_relogio_universal():
    from datetime import timezone

    diferenca = abs((agora_utc() - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds())

    assert diferenca < 5


def test_hoje_local_acompanha_o_calendario_da_maquina():
    assert hoje_local() == datetime.now().date()


# =========================
# 2. O caso que originou a correção
# =========================

def test_venda_das_21h30_entra_no_dia_local():
    """
    Em UTC-3, uma venda às 21h30 do dia 02 é gravada como 00h30 do dia 03.
    Antes da correção ela ficava fora do intervalo consultado para o dia 02.
    """
    inicio, fim = intervalo_utc(date(2026, 9, 2), date(2026, 9, 2), fuso=BRT)
    venda_gravada_em = datetime(2026, 9, 3, 0, 30)   # UTC

    assert inicio <= venda_gravada_em <= fim


def test_venda_da_manha_continua_no_dia_certo():
    inicio, fim = intervalo_utc(date(2026, 9, 2), date(2026, 9, 2), fuso=BRT)
    venda_gravada_em = datetime(2026, 9, 2, 13, 0)   # 10h local

    assert inicio <= venda_gravada_em <= fim


def test_venda_do_dia_anterior_fica_de_fora():
    """A conversão não pode alargar o intervalo para trás."""
    inicio, fim = intervalo_utc(date(2026, 9, 2), date(2026, 9, 2), fuso=BRT)
    venda_do_dia_1 = datetime(2026, 9, 2, 2, 59)   # 23h59 do dia 01, local

    assert not (inicio <= venda_do_dia_1 <= fim)


def test_venda_do_dia_seguinte_fica_de_fora():
    inicio, fim = intervalo_utc(date(2026, 9, 2), date(2026, 9, 2), fuso=BRT)
    venda_do_dia_3 = datetime(2026, 9, 3, 3, 1)   # 00h01 do dia 03, local

    assert not (inicio <= venda_do_dia_3 <= fim)


def test_limites_do_dia_em_utc_sao_deslocados_pelo_fuso():
    dia = date(2026, 9, 2)

    assert inicio_do_dia_utc(dia, fuso=BRT) == datetime(2026, 9, 2, 3, 0)
    assert fim_do_dia_utc(dia, fuso=BRT).replace(microsecond=0) == datetime(2026, 9, 3, 2, 59, 59)


# =========================
# 3. Propriedades do intervalo
# =========================

def test_intervalo_cobre_exatamente_24_horas_por_dia():
    inicio, fim = intervalo_utc(date(2026, 9, 2), date(2026, 9, 2), fuso=BRT)

    assert (fim - inicio).total_seconds() == pytest.approx(86400, abs=1)


def test_intervalo_de_varios_dias_cobre_o_periodo_inteiro():
    inicio, fim = intervalo_utc(date(2026, 9, 1), date(2026, 9, 30), fuso=BRT)

    assert (fim - inicio).days == 29
    assert inicio == datetime(2026, 9, 1, 3, 0)


def test_intervalo_de_um_unico_dia_nao_e_vazio():
    inicio, fim = intervalo_utc(date(2026, 9, 2), date(2026, 9, 2), fuso=BRT)

    assert inicio < fim


def test_dias_consecutivos_nao_se_sobrepoem():
    """Uma venda não pode aparecer em dois dias diferentes."""
    _, fim_dia_2 = intervalo_utc(date(2026, 9, 2), date(2026, 9, 2), fuso=BRT)
    inicio_dia_3, _ = intervalo_utc(date(2026, 9, 3), date(2026, 9, 3), fuso=BRT)

    assert fim_dia_2 < inicio_dia_3


# =========================
# 4. Expiração por prazo
# =========================

def test_limite_ha_dias_recua_a_partir_do_horario_universal():
    limite = limite_utc_ha(dias=7)

    assert limite.tzinfo is None
    assert (agora_utc() - limite).total_seconds() == pytest.approx(7 * 86400, abs=5)


def test_limite_aceita_horas():
    limite = limite_utc_ha(horas=8)

    assert (agora_utc() - limite).total_seconds() == pytest.approx(8 * 3600, abs=5)


# =========================
# 5. O fuso do sistema é respeitado
# =========================

def test_conversao_usa_o_fuso_do_computador():
    """
    Não há cadastro de fuso: o sistema roda na máquina da loja, então o fuso
    do sistema operacional é o do estabelecimento.
    """
    meio_dia_local = datetime(2026, 9, 2, 12, 0)

    assert local_para_utc(meio_dia_local, fuso=BRT) == datetime(2026, 9, 2, 15, 0)


def test_conversao_nao_devolve_fuso_anexado():
    assert local_para_utc(datetime(2026, 9, 2, 12, 0)).tzinfo is None
