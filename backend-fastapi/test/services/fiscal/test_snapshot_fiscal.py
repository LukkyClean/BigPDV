# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/test_snapshot_fiscal.py
# DESCRIÇÃO: Snapshot dos itens no momento da emissão.
#
# O defeito que originou isto: DocumentoFiscal não guardava os itens, e a tela
# de detalhes os reconstruía AO VIVO de `item.produto.fiscal`. Trocar o NCM de
# um produto mudava o que uma nota JÁ AUTORIZADA exibia.
# ---------------------------------------------------------------------------

from app.db.models.documento_fiscal import DocumentoFiscal
from app.services.fiscal.snapshot import gravar_snapshot, montar_itens_snapshot


def _payload(**item_extra):
    item = {
        "numero_item": 1,
        "codigo_produto": "P1",
        "descricao": "Teclado Mecanico",
        "quantidade_comercial": 2.0,
        "valor_unitario_comercial": 150.00,
        "valor_bruto": 300.00,
        "unidade_comercial": "UN",
        "codigo_barras_comercial": "7891234567895",
        "ncm": "84716052",
        "cfop": "5102",
        "icms_origem": "0",
        "icms_situacao_tributaria": "00",
        "icms_base_calculo": 300.00,
        "icms_aliquota": 20.00,
        "icms_valor": 60.00,
        "valor_desconto": 0.0,
    }
    item.update(item_extra)
    return {"items": [item]}


class _ItemVendaFake:
    def __init__(self, produto_id):
        self.produto_id = produto_id


class _VendaFake:
    def __init__(self, *produto_ids):
        self.itens = [_ItemVendaFake(pid) for pid in produto_ids]


# =========================
# 1. Conversão de valores
# =========================

def test_valores_viram_centavos():
    """O payload fala em reais; o banco, em centavos, como todo o sistema."""
    item = montar_itens_snapshot(_payload())[0]

    assert item.valor_unitario == 15000
    assert item.valor_bruto == 30000
    assert item.base_icms == 30000
    assert item.valor_icms == 6000


def test_aliquota_vira_centesimos():
    item = montar_itens_snapshot(_payload())[0]

    assert item.aliquota_icms_centesimos == 2000  # 20,00% — alíquota interna do CE


def test_quantidade_vira_milesimos():
    """Fracionário é a razão de não guardar inteiro: 0,5 kg é venda comum."""
    item = montar_itens_snapshot(_payload(quantidade_comercial=0.5))[0]

    assert item.quantidade_milesimos == 500


def test_arredondamento_de_float_nao_perde_centavo():
    """
    `int(2.30 * 100)` dá 229 em ponto flutuante. É o tipo de erro que só
    aparece no fechamento do caixa.
    """
    item = montar_itens_snapshot(_payload(valor_unitario_comercial=2.30))[0]

    assert item.valor_unitario == 230


# =========================
# 2. Classificação fiscal congelada
# =========================

def test_classificacao_fiscal_e_congelada():
    item = montar_itens_snapshot(_payload())[0]

    assert item.ncm == "84716052"
    assert item.cfop == "5102"
    assert item.situacao_tributaria == "00"
    assert item.origem_mercadoria == "0"


def test_produto_id_vem_da_venda_e_nao_do_payload():
    """
    O id interno não viaja no payload (a SEFAZ não tem o que fazer com ele),
    mas a tela precisa dele para linkar de volta ao catálogo. O casamento é
    pela ordem.
    """
    itens = montar_itens_snapshot(_payload(), venda=_VendaFake(42))

    assert itens[0].produto_id == 42


def test_sem_venda_o_produto_id_fica_nulo():
    assert montar_itens_snapshot(_payload())[0].produto_id is None


# =========================
# 3. Tolerância — snapshot é registro, não pré-requisito da nota
# =========================

def test_payload_sem_itens_nao_quebra():
    assert montar_itens_snapshot({}) == []


def test_item_torto_e_ignorado_sem_derrubar_os_outros():
    payload = {"items": ["lixo", _payload()["items"][0]]}

    assert len(montar_itens_snapshot(payload)) == 1


def test_campos_ausentes_viram_zero_ou_nulo():
    """Uma nota antiga ou um payload mínimo não podem derrubar a emissão."""
    item = montar_itens_snapshot({"items": [{"descricao": "Item avulso"}]})[0]

    assert item.descricao == "Item avulso"
    assert item.ncm is None
    assert item.valor_bruto == 0


def test_gravar_snapshot_nunca_levanta():
    """
    Rede de segurança: a emissão já pode ter chegado à SEFAZ quando isto roda.
    Um snapshot ausente degrada a tela; uma exceção derrubaria a nota.
    """
    doc = DocumentoFiscal(tipo_documento="NFCE", origem_tipo="VENDA", status="PROCESSANDO")

    gravar_snapshot(doc, {"items": None})

    assert doc.itens == []


def test_texto_longo_e_truncado_no_limite_da_coluna():
    item = montar_itens_snapshot(_payload(descricao="X" * 400))[0]

    assert len(item.descricao) == 255
