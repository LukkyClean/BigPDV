# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/test_tax_engine_icms.py
# DESCRIÇÃO: Testes do calculador de ICMS por CST (regime normal) e
#            CSOSN (Simples Nacional).
#
# CSTs suportados hoje:   00, 20, 40, 41, 60
# CSOSNs suportados hoje: 101, 102, 500
# Qualquer outro código levanta CSTNaoSuportadoError e trava a emissão —
# comportamento deliberado enquanto a cobertura não for ampliada.
# ---------------------------------------------------------------------------

from decimal import Decimal

import pytest

from app.services.fiscal.tax_engine.calculators.icms import calcular_icms
from app.services.fiscal.tax_engine.exceptions import CSTNaoSuportadoError

from .conftest import d, item

ZERO = Decimal("0")


def calcular(item_entrada, vf="0", vs="0", vod="0", vd="0", simples=False):
    """Atalho: chama calcular_icms com os rateios já convertidos."""
    return calcular_icms(
        item=item_entrada,
        valor_frete=d(vf),
        valor_seguro=d(vs),
        valor_outras_despesas=d(vod),
        valor_desconto=d(vd),
        simples_nacional=simples,
    )


# =========================
# 1. Regime normal — CST 00 (tributada integralmente)
# =========================

def test_cst_00_tributa_a_base_cheia():
    resultado = calcular(item(valor_bruto="100.00", cst_icms="00", aliquota_icms=d("18")))

    assert resultado.situacao_tributaria == "00"
    assert resultado.base_calculo == d("100.00")
    assert resultado.aliquota == d("18")
    assert resultado.valor == d("18.00")


def test_cst_00_soma_frete_seguro_e_despesas_na_base_e_subtrai_desconto():
    """Base = produto + frete + seguro + despesas − desconto."""
    resultado = calcular(
        item(valor_bruto="100.00", aliquota_icms=d("18")),
        vf="10.00", vs="5.00", vod="5.00", vd="20.00",
    )

    assert resultado.base_calculo == d("100.00")  # 100 + 10 + 5 + 5 − 20
    assert resultado.valor == d("18.00")


def test_cst_00_arredonda_meio_centavo_para_cima():
    """ROUND_HALF_UP: 33,33 × 18% = 5,9994 → 6,00 não; 5,99 sim. Confere a borda."""
    resultado = calcular(item(valor_bruto="10.05", aliquota_icms=d("18")))

    # 10,05 × 18% = 1,809 → 1,81
    assert resultado.valor == d("1.81")


# =========================
# 2. Regime normal — CST 20 (redução de base)
# =========================

def test_cst_20_reduz_a_base_antes_de_aplicar_a_aliquota():
    resultado = calcular(item(
        valor_bruto="100.00",
        cst_icms="20",
        aliquota_icms=d("18"),
        reducao_base_icms=d("30"),
        codigo_beneficio_fiscal="SP800001",
    ))

    assert resultado.base_calculo == d("70.00")     # 100 × (100−30)/100
    assert resultado.valor == d("12.60")            # 70 × 18%
    assert resultado.reducao_base == d("30")
    assert resultado.codigo_beneficio_fiscal == "SP800001"


def test_cst_20_sem_reducao_equivale_a_base_cheia():
    resultado = calcular(item(valor_bruto="100.00", cst_icms="20", aliquota_icms=d("18")))

    assert resultado.base_calculo == d("100.00")
    assert resultado.valor == d("18.00")


# =========================
# 3. Regime normal — CSTs sem destaque
# =========================

@pytest.mark.parametrize("cst", ["40", "41", "60"])
def test_csts_sem_destaque_zeram_base_aliquota_e_valor(cst):
    """
    40/41 (isenta/não tributada) e 60 (ST cobrada anteriormente) não podem
    destacar ICMS, mesmo com alíquota cadastrada no produto.
    """
    resultado = calcular(item(valor_bruto="100.00", cst_icms=cst, aliquota_icms=d("18")))

    assert resultado.situacao_tributaria == cst
    assert resultado.base_calculo == ZERO
    assert resultado.aliquota == ZERO
    assert resultado.valor == ZERO


# =========================
# 4. Simples Nacional — CSOSN
# =========================

@pytest.mark.parametrize("csosn", ["102", "500"])
def test_csosn_sem_credito_e_st_nao_destacam_icms(csosn):
    """
    CSOSN 102 (sem permissão de crédito) e 500 (ST) são proibidos de
    destacar base e valor de ICMS. Vale mesmo com alíquota no cadastro.
    """
    resultado = calcular(
        item(valor_bruto="100.00", csosn=csosn, cst_icms=None, aliquota_icms=d("18")),
        simples=True,
    )

    assert resultado.situacao_tributaria == csosn
    assert resultado.base_calculo == ZERO
    assert resultado.aliquota == ZERO
    assert resultado.valor == ZERO


def test_csosn_101_calcula_credito_sem_destacar_imposto():
    resultado = calcular(
        item(valor_bruto="100.00", csosn="101", cst_icms=None, aliquota_icms=d("2.75")),
        simples=True,
    )

    assert resultado.situacao_tributaria == "101"
    assert resultado.aliquota == ZERO
    assert resultado.valor == ZERO
    assert resultado.aliquota_credito_simples == d("2.75")
    assert resultado.valor_credito_simples == d("2.75")


def test_csosn_101_nao_emite_base_de_calculo():
    resultado = calcular(
        item(valor_bruto="100.00", csosn="101", cst_icms=None, aliquota_icms=d("2.75")),
        simples=True,
    )

    assert resultado.base_calculo == ZERO


# =========================
# 5. Códigos fora da cobertura do motor
# =========================

@pytest.mark.parametrize("cst", ["10", "30", "51", "70", "90"])
def test_cst_fora_da_cobertura_levanta_erro_explicito(cst):
    with pytest.raises(CSTNaoSuportadoError) as exc:
        calcular(item(numero_item=3, cst_icms=cst))

    assert exc.value.campo == "cst_icms"
    assert exc.value.item == 3


@pytest.mark.parametrize("csosn", ["103", "201", "202", "203", "300", "400", "900"])
def test_csosn_fora_da_cobertura_levanta_erro_explicito(csosn):
    with pytest.raises(CSTNaoSuportadoError) as exc:
        calcular(item(numero_item=2, csosn=csosn, cst_icms=None), simples=True)

    assert exc.value.campo == "csosn"
    assert exc.value.item == 2


def test_cst_ausente_no_regime_normal_levanta_erro():
    with pytest.raises(CSTNaoSuportadoError) as exc:
        calcular(item(cst_icms=None))

    assert exc.value.campo == "cst_icms"


def test_csosn_ausente_no_simples_levanta_erro():
    with pytest.raises(CSTNaoSuportadoError) as exc:
        calcular(item(csosn=None, cst_icms=None), simples=True)

    assert exc.value.campo == "csosn"


# =========================
# 6. Origem da mercadoria atravessa o cálculo
# =========================

@pytest.mark.parametrize("origem", [0, 1, 2, 8])
def test_origem_da_mercadoria_e_preservada(origem):
    resultado = calcular(item(origem_mercadoria=origem))

    assert resultado.origem == origem
