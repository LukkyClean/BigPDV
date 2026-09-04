# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/conftest.py
# DESCRIÇÃO: Fábricas compartilhadas dos testes do FiscalTaxEngine.
#            São testes de unidade: não tocam o banco nem a rede.
# ---------------------------------------------------------------------------

from decimal import Decimal

import pytest

from app.services.fiscal.tax_engine.types import DadosNota, ItemEntrada


def d(valor) -> Decimal:
    """Atalho para Decimal a partir de str/int — nunca de float."""
    return Decimal(str(valor))


def item(
    numero_item: int = 1,
    valor_bruto="100.00",
    quantidade="1",
    valor_unitario=None,
    desconto_item="0",
    **kwargs,
) -> ItemEntrada:
    """
    Monta um ItemEntrada com defaults de regime normal tributado (CST 00, 18%).

    Sobrescreva pelo kwargs o que o caso de teste precisar variar.
    """
    campos = {
        "numero_item": numero_item,
        "descricao": f"Produto {numero_item}",
        "quantidade": d(quantidade),
        "valor_unitario": d(valor_unitario if valor_unitario is not None else valor_bruto),
        "valor_bruto": d(valor_bruto),
        "desconto_item": d(desconto_item),
        "ncm": "84713012",
        "cfop": "5102",
        "origem_mercadoria": 0,
        "cst_icms": "00",
        "aliquota_icms": d("18"),
        "aliquota_pis": d("1.65"),
        "aliquota_cofins": d("7.60"),
        "cst_pis": "01",
        "cst_cofins": "01",
    }
    campos.update(kwargs)
    return ItemEntrada(**campos)


def nota(
    uf_emitente: str = "SP",
    simples_nacional: bool = False,
    frete="0",
    seguro="0",
    outras_despesas="0",
    desconto_nota="0",
    excluir_icms_base_pis_cofins: bool = False,
) -> DadosNota:
    """Monta um DadosNota com todos os valores globais zerados por padrão."""
    return DadosNota(
        uf_emitente=uf_emitente,
        simples_nacional=simples_nacional,
        frete=d(frete),
        seguro=d(seguro),
        outras_despesas=d(outras_despesas),
        desconto_nota=d(desconto_nota),
        excluir_icms_base_pis_cofins=excluir_icms_base_pis_cofins,
    )


@pytest.fixture
def fabrica_item():
    return item


@pytest.fixture
def fabrica_nota():
    return nota
