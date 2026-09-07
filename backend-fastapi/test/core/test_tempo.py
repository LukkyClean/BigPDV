# ---------------------------------------------------------------------------
# ARQUIVO: test/core/test_tempo.py
# DESCRIÇÃO: Testes da fronteira entre horário local e horário universal.
#
# O fuso é FIXADO em cada teste que depende dele. Sem isso o resultado passa a
# depender da hora em que a suíte roda — foi exatamente assim que o defeito de
# fuso ficou escondido: os testes só falhavam entre 21h e meia-noite.
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
    para_utc,
)


@pytest.fixture
def fuso_brt(monkeypatch):
    """Fixa o fuso da loja em UTC-3 pela STARTBIG_TZ.

    Deslocamento fixo em vez de 'America/Sao_Paulo' de propósito: o Windows não
    traz o banco de fusos IANA, então o nome levantaria ZoneInfoNotFoundError na
    máquina de loja e o teste passaria por engano, caindo no fuso do sistema.
    O Brasil não tem horário de verão desde 2019, então '-03:00' é exato o ano
    inteiro.
    """
    monkeypatch.setenv("STARTBIG_TZ", "-03:00")


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
    diferenca = abs((agora_utc() - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds())

    assert diferenca < 5


def test_hoje_local_acompanha_o_calendario_da_maquina():
    """Sem STARTBIG_TZ, o fuso da loja é o do próprio sistema operacional."""
    assert hoje_local() == datetime.now().date()


def test_hoje_local_segue_o_fuso_configurado(monkeypatch):
    """Com STARTBIG_TZ, o dia da loja e o daquele fuso, nao o da maquina."""
    monkeypatch.setenv("STARTBIG_TZ", "+14:00")
    fuso_alvo = timezone(timedelta(hours=14))

    assert hoje_local() == datetime.now(fuso_alvo).date()


# =========================
# 2. O caso que originou a correção
# =========================

def test_venda_das_21h30_entra_no_dia_local(fuso_brt):
    """
    Em UTC-3, uma venda às 21h30 do dia 02 é gravada como 00h30 do dia 03.
    Antes da correção ela ficava fora do intervalo consultado para o dia 02.
    """
    inicio, fim = intervalo_utc(date(2026, 9, 2), date(2026, 9, 2))
    venda_gravada_em = datetime(2026, 9, 3, 0, 30)   # UTC

    assert inicio <= venda_gravada_em <= fim


def test_venda_da_manha_continua_no_dia_certo(fuso_brt):
    inicio, fim = intervalo_utc(date(2026, 9, 2), date(2026, 9, 2))
    venda_gravada_em = datetime(2026, 9, 2, 13, 0)   # 10h local

    assert inicio <= venda_gravada_em <= fim


def test_venda_do_dia_anterior_fica_de_fora(fuso_brt):
    """A conversão não pode alargar o intervalo para trás."""
    inicio, fim = intervalo_utc(date(2026, 9, 2), date(2026, 9, 2))
    venda_do_dia_1 = datetime(2026, 9, 2, 2, 59)   # 23h59 do dia 01, local

    assert not (inicio <= venda_do_dia_1 <= fim)


def test_venda_do_dia_seguinte_fica_de_fora(fuso_brt):
    inicio, fim = intervalo_utc(date(2026, 9, 2), date(2026, 9, 2))
    venda_do_dia_3 = datetime(2026, 9, 3, 3, 1)   # 00h01 do dia 03, local

    assert not (inicio <= venda_do_dia_3 <= fim)


def test_limites_do_dia_em_utc_sao_deslocados_pelo_fuso(fuso_brt):
    dia = date(2026, 9, 2)

    assert inicio_do_dia_utc(dia) == datetime(2026, 9, 2, 3, 0)
    assert fim_do_dia_utc(dia).replace(microsecond=0) == datetime(2026, 9, 3, 2, 59, 59)


# =========================
# 3. Propriedades do intervalo
# =========================

def test_intervalo_cobre_exatamente_24_horas_por_dia(fuso_brt):
    inicio, fim = intervalo_utc(date(2026, 9, 2), date(2026, 9, 2))

    assert (fim - inicio).total_seconds() == pytest.approx(86400, abs=1)


def test_intervalo_de_varios_dias_cobre_o_periodo_inteiro(fuso_brt):
    inicio, fim = intervalo_utc(date(2026, 9, 1), date(2026, 9, 30))

    assert (fim - inicio).days == 29
    assert inicio == datetime(2026, 9, 1, 3, 0)


def test_intervalo_de_um_unico_dia_nao_e_vazio(fuso_brt):
    inicio, fim = intervalo_utc(date(2026, 9, 2), date(2026, 9, 2))

    assert inicio < fim


def test_dias_consecutivos_nao_se_sobrepoem(fuso_brt):
    """Uma venda não pode aparecer em dois dias diferentes."""
    _, fim_dia_2 = intervalo_utc(date(2026, 9, 2), date(2026, 9, 2))
    inicio_dia_3, _ = intervalo_utc(date(2026, 9, 3), date(2026, 9, 3))

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
# 5. O fuso configurado é respeitado
# =========================

def test_conversao_usa_o_fuso_configurado(fuso_brt):
    """
    Não há cadastro de fuso na aplicação: o sistema roda na máquina da loja.
    A STARTBIG_TZ existe para corrigir uma máquina com fuso errado sem
    reinstalar nada — e é o que fixa o deslocamento aqui.
    """
    meio_dia_local = datetime(2026, 9, 2, 12, 0)

    assert para_utc(meio_dia_local) == datetime(2026, 9, 2, 15, 0)


def test_conversao_nao_devolve_fuso_anexado():
    assert para_utc(datetime(2026, 9, 2, 12, 0)).tzinfo is None
