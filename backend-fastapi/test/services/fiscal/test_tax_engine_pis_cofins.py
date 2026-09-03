# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/test_tax_engine_pis_cofins.py
# DESCRIÇÃO: Testes do calculador de PIS e COFINS, incluindo a exclusão do
#            ICMS da base de cálculo (STF Tema 69).
# ---------------------------------------------------------------------------

from decimal import Decimal

import pytest

from app.services.fiscal.tax_engine.calculators.pis_cofins import calcular_pis_cofins

from .conftest import d

ZERO = Decimal("0")


def calcular(
    valor_bruto="100.00", vf="0", vs="0", vod="0", vd="0",
    aliq_pis="1.65", aliq_cofins="7.60",
    cst_pis="01", cst_cofins="01",
    icms_valor="0", excluir_icms=False,
):
    return calcular_pis_cofins(
        valor_bruto=d(valor_bruto),
        valor_frete=d(vf),
        valor_seguro=d(vs),
        valor_outras_despesas=d(vod),
        valor_desconto=d(vd),
        aliquota_pis=d(aliq_pis),
        aliquota_cofins=d(aliq_cofins),
        cst_pis=cst_pis,
        cst_cofins=cst_cofins,
        icms_valor=d(icms_valor),
        excluir_icms_base=excluir_icms,
    )


# =========================
# 1. Cálculo tributado (CST 01/02)
# =========================

def test_cst_01_aplica_aliquotas_do_lucro_presumido():
    resultado = calcular()

    assert resultado.pis_base == d("100.00")
    assert resultado.pis_aliquota == d("1.65")
    assert resultado.pis_valor == d("1.65")
    assert resultado.cofins_base == d("100.00")
    assert resultado.cofins_aliquota == d("7.60")
    assert resultado.cofins_valor == d("7.60")


@pytest.mark.parametrize("cst", ["01", "02"])
def test_ambos_os_csts_tributados_calculam_valor(cst):
    resultado = calcular(cst_pis=cst, cst_cofins=cst)

    assert resultado.pis_valor > ZERO
    assert resultado.cofins_valor > ZERO


def test_base_acompanha_frete_seguro_despesas_e_desconto():
    resultado = calcular(vf="10.00", vs="5.00", vod="5.00", vd="20.00")

    assert resultado.pis_base == d("100.00")  # 100 + 10 + 5 + 5 − 20


def test_pis_e_cofins_podem_ter_csts_diferentes():
    resultado = calcular(cst_pis="01", cst_cofins="07")

    assert resultado.pis_valor == d("1.65")
    assert resultado.pis_cst == "01"
    assert resultado.cofins_valor == ZERO
    assert resultado.cofins_cst == "07"


# =========================
# 2. CSTs isentos e desconhecidos
# =========================

@pytest.mark.parametrize("cst", ["04", "05", "06", "07", "08", "09"])
def test_csts_isentos_zeram_base_aliquota_e_valor(cst):
    resultado = calcular(cst_pis=cst, cst_cofins=cst)

    assert (resultado.pis_base, resultado.pis_aliquota, resultado.pis_valor) == (ZERO, ZERO, ZERO)
    assert (resultado.cofins_base, resultado.cofins_aliquota, resultado.cofins_valor) == (ZERO, ZERO, ZERO)


@pytest.mark.parametrize("cst", ["49", "99"])
def test_cst_de_outras_operacoes_zera_sem_levantar_erro(cst):
    """
    49/99 são os CSTs de saída do Simples Nacional. O motor ainda não os
    escolhe sozinho (achado A5, Fase 4), mas já os trata corretamente
    quando vêm do cadastro do produto.
    """
    resultado = calcular(cst_pis=cst, cst_cofins=cst)

    assert resultado.pis_valor == ZERO
    assert resultado.cofins_valor == ZERO
    assert resultado.pis_cst == cst
    assert resultado.cofins_cst == cst


# =========================
# 3. Exclusão do ICMS da base (STF Tema 69)
# =========================

def test_exclusao_do_icms_reduz_a_base_de_pis_e_cofins():
    resultado = calcular(icms_valor="18.00", excluir_icms=True)

    assert resultado.pis_base == d("82.00")
    assert resultado.pis_valor == d("1.35")     # 82 × 1,65% = 1,353
    assert resultado.cofins_base == d("82.00")
    assert resultado.cofins_valor == d("6.23")  # 82 × 7,60% = 6,232


def test_sem_a_flag_o_icms_permanece_na_base():
    resultado = calcular(icms_valor="18.00", excluir_icms=False)

    assert resultado.pis_base == d("100.00")


def test_exclusao_nunca_produz_base_negativa():
    resultado = calcular(valor_bruto="10.00", icms_valor="50.00", excluir_icms=True)

    assert resultado.pis_base == ZERO
    assert resultado.pis_valor == ZERO
