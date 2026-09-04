# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/test_tax_engine_consolidador.py
# DESCRIÇÃO: Testes da consolidação dos totais do cabeçalho e do fluxo
#            completo de calcular_impostos().
#
# INVARIANTE CENTRAL: para cada campo, cabeçalho == soma dos itens.
# É a regra que a SEFAZ audita nas Rejeições 531 e 610.
# ---------------------------------------------------------------------------

from decimal import Decimal

import pytest

from app.services.fiscal.tax_engine.engine import calcular_impostos

from .conftest import d, item, nota

ZERO = Decimal("0")


# =========================
# 1. O invariante do cabeçalho
# =========================

CENARIOS = {
    "nota simples de um item": (
        [item(1, valor_bruto="100.00")],
        nota(),
    ),
    "tres itens com frete e desconto": (
        [item(1, valor_bruto="33.33"), item(2, valor_bruto="66.67"), item(3, valor_bruto="10.00")],
        nota(frete="15.00", desconto_nota="7.77"),
    ),
    "valores globais todos preenchidos": (
        [item(1, valor_bruto="100.00"), item(2, valor_bruto="250.50")],
        nota(frete="40.00", seguro="8.00", outras_despesas="12.00", desconto_nota="20.00"),
    ),
    "descontos por item": (
        [item(1, valor_bruto="100.00", desconto_item="10.00"),
         item(2, valor_bruto="50.00", desconto_item="5.00")],
        nota(),
    ),
    "simples nacional com csosn 102": (
        [item(1, valor_bruto="100.00", csosn="102", cst_icms=None),
         item(2, valor_bruto="0.03", csosn="102", cst_icms=None)],
        nota(simples_nacional=True, frete="0.07"),
    ),
    "cst 20 com reducao de base": (
        [item(1, valor_bruto="199.99", cst_icms="20", reducao_base_icms=d("33.33"))],
        nota(outras_despesas="0.01"),
    ),
    "exclusao de icms da base pis cofins": (
        [item(1, valor_bruto="100.00"), item(2, valor_bruto="100.00")],
        nota(excluir_icms_base_pis_cofins=True),
    ),
    "centavos indivisiveis entre muitos itens": (
        [item(i, valor_bruto="1.00") for i in range(1, 8)],
        nota(frete="0.05", desconto_nota="0.03"),
    ),
}


@pytest.mark.parametrize("itens, dados", CENARIOS.values(), ids=list(CENARIOS))
def test_cabecalho_bate_com_a_soma_dos_itens(itens, dados):
    """INVARIANTE: cada total do cabeçalho == soma do campo nos itens."""
    resultado = calcular_impostos(itens, dados)
    t = resultado.totais

    assert t.valor_icms == sum(i.icms_valor for i in resultado.itens)
    assert t.base_calculo_icms == sum(i.icms_base_calculo for i in resultado.itens)
    assert t.valor_pis == sum(i.pis_valor for i in resultado.itens)
    assert t.valor_cofins == sum(i.cofins_valor for i in resultado.itens)
    assert t.valor_frete == sum(i.valor_frete for i in resultado.itens)
    assert t.valor_seguro == sum(i.valor_seguro for i in resultado.itens)
    assert t.valor_outras_despesas == sum(i.valor_outras_despesas for i in resultado.itens)
    assert t.valor_desconto == sum(i.valor_desconto for i in resultado.itens)


@pytest.mark.parametrize("itens, dados", CENARIOS.values(), ids=list(CENARIOS))
def test_valores_globais_da_nota_sao_integralmente_distribuidos(itens, dados):
    """
    INVARIANTE: o que foi informado como frete/seguro/despesas/desconto da nota
    reaparece inteiro no cabeçalho, sem centavo perdido no rateio.
    """
    resultado = calcular_impostos(itens, dados)
    t = resultado.totais

    assert t.valor_frete == dados.frete
    assert t.valor_seguro == dados.seguro
    assert t.valor_outras_despesas == dados.outras_despesas

    descontos_de_item = sum(i.desconto_item for i in itens)
    assert t.valor_desconto == dados.desconto_nota + descontos_de_item


@pytest.mark.parametrize("itens, dados", CENARIOS.values(), ids=list(CENARIOS))
def test_total_da_nota_segue_a_formula_oficial(itens, dados):
    """
    INVARIANTE: vNF = vProd + vFrete + vSeg + vOutro − vDesc.
    Impostos não entram: já estão embutidos no preço dos produtos.
    """
    resultado = calcular_impostos(itens, dados)
    t = resultado.totais

    esperado = (
        t.valor_total_produtos
        + t.valor_frete
        + t.valor_seguro
        + t.valor_outras_despesas
        - t.valor_desconto
    )
    assert t.valor_total_nota == esperado


@pytest.mark.parametrize("itens, dados", CENARIOS.values(), ids=list(CENARIOS))
def test_total_de_produtos_bate_com_o_bruto_dos_itens(itens, dados):
    resultado = calcular_impostos(itens, dados)

    assert resultado.totais.valor_total_produtos == sum(i.valor_bruto for i in itens)


# =========================
# 2. Alinhamento item a item
# =========================

def test_cada_item_de_entrada_gera_exatamente_um_item_de_imposto():
    itens = [item(i, valor_bruto="10.00") for i in range(1, 6)]

    resultado = calcular_impostos(itens, nota())

    assert len(resultado.itens) == len(itens)
    assert [i.numero_item for i in resultado.itens] == [1, 2, 3, 4, 5]


def test_desconto_do_item_soma_com_o_rateio_do_desconto_da_nota():
    itens = [
        item(1, valor_bruto="100.00", desconto_item="10.00"),
        item(2, valor_bruto="100.00", desconto_item="0"),
    ]

    resultado = calcular_impostos(itens, nota(desconto_nota="20.00"))

    # Rateio 50/50 do desconto da nota, somado ao desconto próprio de cada item
    assert resultado.itens[0].valor_desconto == d("20.00")
    assert resultado.itens[1].valor_desconto == d("10.00")


# =========================
# 3. IPI — não calculado para comércio
# =========================

def test_ipi_sai_como_nao_tributado_em_todos_os_itens():
    resultado = calcular_impostos([item(1), item(2)], nota())

    for imposto in resultado.itens:
        assert imposto.ipi_situacao_tributaria == "53"
        assert imposto.ipi_codigo_enquadramento == "999"
