# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/test_tax_engine_rateio.py
# DESCRIÇÃO: Testes do rateio proporcional de valores globais da nota.
#
# A regra que importa: a soma dos valores rateados tem que bater EXATAMENTE
# com o valor global distribuído. Um centavo de sobra vira Rejeição 531/610.
# ---------------------------------------------------------------------------

from decimal import Decimal

import pytest

from app.services.fiscal.tax_engine.exceptions import RateioError
from app.services.fiscal.tax_engine.rateio import aplicar_rateio, ratear_valor

from .conftest import d, item


# =========================
# 1. Distribuição proporcional
# =========================

@pytest.mark.parametrize("valor_total, brutos, esperado", [
    # Divisão exata — sem resíduo
    ("1.00", ["10.00", "90.00"], ["0.10", "0.90"]),
    ("100.00", ["50.00", "50.00"], ["50.00", "50.00"]),
    # Item único absorve tudo
    ("7.77", ["100.00"], ["7.77"]),
    # Dízima: 10/3 por item, resíduo de 0,01 no primeiro (todos empatados)
    ("10.00", ["100.00", "100.00", "100.00"], ["3.34", "3.33", "3.33"]),
])
def test_ratear_valor_distribui_proporcionalmente(valor_total, brutos, esperado):
    itens = [item(numero_item=i + 1, valor_bruto=b) for i, b in enumerate(brutos)]

    resultado = ratear_valor(d(valor_total), itens)

    assert resultado == [d(e) for e in esperado]


def test_ratear_valor_joga_residuo_no_item_de_maior_valor():
    """
    O resíduo vai para o item de maior valor bruto, não para o último.
    Isso evita distorcer um item barato no fim da lista.
    """
    itens = [
        item(numero_item=1, valor_bruto="1.00"),
        item(numero_item=2, valor_bruto="1.00"),
        item(numero_item=3, valor_bruto="5.00"),
    ]

    resultado = ratear_valor(d("1.00"), itens)

    # 1/7 → 0,14 · 1/7 → 0,14 · 5/7 → 0,71 = 0,99; o centavo sobra no item 3
    assert resultado == [d("0.14"), d("0.14"), d("0.72")]


# =========================
# 2. Invariante de fechamento
# =========================

@pytest.mark.parametrize("valor_total", ["0.01", "0.07", "1.00", "13.33", "999.99"])
@pytest.mark.parametrize("brutos", [
    ["1.00", "1.00", "1.00"],
    ["0.01", "999.99"],
    ["33.33", "33.33", "33.34"],
    ["7.00", "11.00", "13.00", "17.00", "19.00"],
])
def test_soma_dos_rateados_bate_sempre_com_o_valor_distribuido(valor_total, brutos):
    """INVARIANTE: sum(rateados) == valor_total, em qualquer combinação."""
    itens = [item(numero_item=i + 1, valor_bruto=b) for i, b in enumerate(brutos)]

    resultado = ratear_valor(d(valor_total), itens)

    assert sum(resultado) == d(valor_total)


def test_valor_zero_nao_rateia_nada():
    itens = [item(numero_item=i + 1) for i in range(3)]

    assert ratear_valor(Decimal("0"), itens) == [Decimal("0")] * 3


# =========================
# 3. Entradas inválidas
# =========================

def test_lista_vazia_de_itens_levanta_erro():
    with pytest.raises(RateioError) as exc:
        ratear_valor(d("10.00"), [])

    assert exc.value.campo == "itens"


def test_total_bruto_zerado_levanta_erro():
    """Sem peso não há como ratear — melhor falhar que dividir por zero."""
    itens = [item(numero_item=1, valor_bruto="0.00")]

    with pytest.raises(RateioError) as exc:
        ratear_valor(d("10.00"), itens)

    assert exc.value.campo == "valor_bruto"


# =========================
# 4. aplicar_rateio — os quatro valores globais juntos
# =========================

def test_aplicar_rateio_distribui_os_quatro_valores():
    itens = [
        item(numero_item=1, valor_bruto="100.00"),
        item(numero_item=2, valor_bruto="300.00"),
    ]

    resultado = aplicar_rateio(
        itens,
        frete=d("40.00"),
        seguro=d("8.00"),
        outras_despesas=d("12.00"),
        desconto_nota=d("20.00"),
    )

    assert resultado[0] == {
        "valor_frete": d("10.00"),
        "valor_seguro": d("2.00"),
        "valor_outras_despesas": d("3.00"),
        "valor_desconto_nota": d("5.00"),
    }
    assert resultado[1] == {
        "valor_frete": d("30.00"),
        "valor_seguro": d("6.00"),
        "valor_outras_despesas": d("9.00"),
        "valor_desconto_nota": d("15.00"),
    }


def test_desconto_da_nota_maior_que_os_produtos_e_recusado():
    """Base negativa é rejeição certa — barrar antes de montar o payload."""
    itens = [item(numero_item=1, valor_bruto="100.00")]

    with pytest.raises(RateioError) as exc:
        aplicar_rateio(
            itens,
            frete=Decimal("0"),
            seguro=Decimal("0"),
            outras_despesas=Decimal("0"),
            desconto_nota=d("100.00"),
        )

    assert exc.value.campo == "desconto_nota"
