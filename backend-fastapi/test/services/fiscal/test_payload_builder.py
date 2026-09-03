# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/test_payload_builder.py
# DESCRIÇÃO: Testes de montagem do payload de NF-e a partir de uma venda.
#
# Os modelos ORM são instanciados soltos (sem sessão): o builder só lê
# atributos, então nada aqui toca o banco.
#
# INVARIANTE CENTRAL: sum(vPag) − vTroco == vNF.
# É a regra do grupo <pag> auditada nas Rejeições 767 e 391.
# ---------------------------------------------------------------------------

from decimal import Decimal

import pytest

from app.core.enum import State
from app.db.models.cliente import ClientePF, ClientePJ
from app.db.models.empresa import Empresa
from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings
from app.db.models.endereco import Endereco
from app.db.models.forma_pagamento import FormaPagamento
from app.db.models.produto import Produto
from app.db.models.produto_fiscal import ProdutoFiscal
from app.db.models.venda import Venda
from app.db.models.venda_pagamento import PagamentoVenda
from app.db.models.venda_produto import ProdutoVenda
from app.services.fiscal.payload_builder import montar_payload_nfe
from app.services.fiscal.tax_engine.engine import calcular_impostos
from app.services.fiscal.tax_engine.types import DadosNota, ItemEntrada

from .conftest import d


# =========================
# Fábricas de cenário
# =========================

def _empresa(regime="Lucro Presumido"):
    return Empresa(
        id=1,
        documento="11222333000181",
        razao_social="Loja Teste Comercio LTDA",
        nome_fantasia="Loja Teste",
        inscricao_estadual="110042490114",
        inscricao_municipal="12345",
        regime_tributario=regime,
    )


def _endereco_empresa():
    return Endereco(
        logradouro="Rua das Flores",
        numero="100",
        complemento="Sala 2",
        bairro="Centro",
        cidade="Sao Paulo",
        estado=State.SAO_PAULO,
        cep="01001000",
    )


def _fiscal_settings():
    return EmpresaFiscalSettings(empresa_id=1, serie_nfe=1, ultimo_numero_nfe=42)


def _produto(id_produto=1, nome="Teclado Mecanico", codigo_barras="7891234567895"):
    produto = Produto(
        id=id_produto,
        nome=nome,
        codigo_produto=f"P{id_produto:04d}",
        unidade_medida="UN",
        codigo_barras=codigo_barras,
    )
    produto.fiscal = ProdutoFiscal(
        produto_id=id_produto,
        ncm="84716052",
        cfop_padrao="5102",
        origem_mercadoria=0,
        unidade_tributavel="UN",
        cst_icms="00",
        csosn="102",
        aliquota_icms=1800,
        aliquota_pis=165,
        aliquota_cofins=760,
        cst_pis="01",
        cst_cofins="01",
    )
    return produto


def _item_venda(numero, produto, quantidade=1, valor_unitario=10000, desconto=0):
    return ProdutoVenda(
        id=numero,
        produto_id=produto.id,
        produto=produto,
        quantidade=quantidade,
        valor_unitario=valor_unitario,
        subtotal=quantidade * valor_unitario,
        desconto=desconto,
    )


def _pagamento(valor, codigo_sefaz="01", nome="Dinheiro"):
    return PagamentoVenda(
        valor=valor,
        forma_pagamento=FormaPagamento(id=1, nome=nome, codigo_sefaz=codigo_sefaz),
    )


def _venda(itens, pagamentos, entrega=0, acrescimo=0, cliente=None):
    """
    Monta a venda e calcula `total` pela mesma fórmula do finish_sale:
    (subtotal + entrega) − descontos + acrescimo.
    """
    subtotal = sum(i.subtotal for i in itens)
    descontos = sum(i.desconto for i in itens)

    venda = Venda(
        id=1,
        numero_venda=1001,
        cliente=cliente,
        subtotal=subtotal,
        entrega=entrega,
        acrescimo=acrescimo,
        total=subtotal + entrega - descontos + acrescimo,
    )
    venda.itens = itens
    venda.pagamentos = pagamentos
    return venda


def _calcular(venda, simples=False, outras_despesas=None):
    """
    Roda o tax_engine sobre a venda, espelhando o que o resolver monta.

    Por padrão o acréscimo vira vOutro, exatamente como em
    resolver.resolver_aliquotas_venda.
    """
    if outras_despesas is None:
        outras_despesas = d(venda.acrescimo or 0) / 100
    itens = [
        ItemEntrada(
            numero_item=idx,
            produto_id=iv.produto_id,
            descricao=iv.produto.nome,
            quantidade=d(iv.quantidade),
            valor_unitario=d(iv.valor_unitario) / 100,
            valor_bruto=d(iv.subtotal) / 100,
            desconto_item=d(iv.desconto) / 100,
            ncm=iv.produto.fiscal.ncm,
            cfop=iv.produto.fiscal.cfop_padrao,
            origem_mercadoria=0,
            cst_icms=iv.produto.fiscal.cst_icms,
            csosn=iv.produto.fiscal.csosn,
            aliquota_icms=d("18"),
            aliquota_pis=d("1.65"),
            aliquota_cofins=d("7.60"),
        )
        for idx, iv in enumerate(venda.itens, start=1)
    ]
    dados = DadosNota(
        uf_emitente="SP",
        simples_nacional=simples,
        frete=d(venda.entrega) / 100,
        seguro=Decimal("0"),
        outras_despesas=d(outras_despesas),
        desconto_nota=Decimal("0"),
    )
    return calcular_impostos(itens, dados)


def _montar(venda, simples=False, outras_despesas=None):
    return montar_payload_nfe(
        empresa=_empresa("Simples Nacional" if simples else "Lucro Presumido"),
        endereco_empresa=_endereco_empresa(),
        fiscal_settings=_fiscal_settings(),
        venda=venda,
        nota_fiscal=None,
        resultado_calculo=_calcular(venda, simples, outras_despesas),
    )


# =========================
# 1. Golden test — venda representativa
# =========================

@pytest.fixture
def venda_simples():
    """Dois itens, R$ 100,00 e R$ 50,00, pagamento exato em dinheiro."""
    itens = [
        _item_venda(1, _produto(1, "Teclado Mecanico"), quantidade=1, valor_unitario=10000),
        _item_venda(2, _produto(2, "Mouse Optico"), quantidade=1, valor_unitario=5000),
    ]
    return _venda(itens, [_pagamento(15000)])


def test_payload_traz_os_grupos_obrigatorios(venda_simples):
    payload = _montar(venda_simples)

    assert set(payload) >= {
        "natureza_operacao", "tipo_documento", "finalidade_emissao",
        "numero", "serie", "emitente", "destinatario",
        "items", "formas_pagamento", "totais",
    }
    assert payload["tipo_documento"] == 1
    assert payload["numero"] == 43       # ultimo_numero_nfe (42) + 1
    assert payload["serie"] == 1


def test_itens_saem_numerados_e_com_valores_em_reais(venda_simples):
    payload = _montar(venda_simples)
    primeiro, segundo = payload["items"]

    assert primeiro["numero_item"] == 1
    assert primeiro["descricao"] == "Teclado Mecanico"
    assert primeiro["valor_unitario_comercial"] == 100.00
    assert primeiro["valor_bruto"] == 100.00
    assert primeiro["ncm"] == "84716052"
    assert primeiro["cfop"] == "5102"
    assert segundo["numero_item"] == 2
    assert segundo["valor_bruto"] == 50.00


def test_totais_batem_com_a_soma_dos_itens(venda_simples):
    payload = _montar(venda_simples)

    assert payload["totais"]["valor_produtos"] == 150.00
    assert payload["totais"]["valor_total"] == 150.00
    assert payload["totais"]["icms_valor_total"] == 27.00  # 150 × 18%


def test_regime_normal_usa_cst_e_simples_usa_csosn(venda_simples):
    normal = _montar(venda_simples, simples=False)
    simples = _montar(venda_simples, simples=True)

    assert normal["items"][0]["icms_situacao_tributaria"] == "00"
    assert simples["items"][0]["icms_situacao_tributaria"] == "102"


# =========================
# 2. O invariante do grupo <pag>
# =========================

def _somar_pagamentos(payload):
    return round(sum(p["valor_pagamento"] for p in payload["formas_pagamento"]), 2)


def test_pagamento_exato_fecha_com_o_total_da_nota(venda_simples):
    """INVARIANTE: sum(vPag) − vTroco == vNF. Caso base, sem troco nem juros."""
    payload = _montar(venda_simples)

    assert _somar_pagamentos(payload) - payload.get("valor_troco", 0.0) == payload["totais"]["valor_total"]


def test_frete_entra_no_total_e_mantem_o_fechamento():
    itens = [_item_venda(1, _produto(1), quantidade=1, valor_unitario=10000)]
    venda = _venda(itens, [_pagamento(11500)], entrega=1500)

    payload = _montar(venda)

    assert payload["totais"]["valor_frete"] == 15.00
    assert payload["totais"]["valor_total"] == 115.00
    assert _somar_pagamentos(payload) - payload.get("valor_troco", 0.0) == payload["totais"]["valor_total"]


def test_venda_com_troco_fecha_o_grupo_de_pagamentos():
    """R$ 150,00 de nota, R$ 200,00 em dinheiro, R$ 50,00 de troco."""
    itens = [_item_venda(1, _produto(1), quantidade=1, valor_unitario=15000)]
    venda = _venda(itens, [_pagamento(20000)])

    payload = _montar(venda)

    assert venda.troco == 5000
    assert payload["valor_troco"] == 50.00
    assert _somar_pagamentos(payload) - payload["valor_troco"] == payload["totais"]["valor_total"]


def test_acrescimo_de_cartao_entra_no_total_da_nota():
    """R$ 100,00 em 3x com R$ 9,00 de juros: a nota tem que fechar em R$ 109,00."""
    itens = [_item_venda(1, _produto(1), quantidade=1, valor_unitario=10000)]
    venda = _venda(itens, [_pagamento(10900, codigo_sefaz="03", nome="Cartao de Credito")],
                   acrescimo=900)

    payload = _montar(venda)

    assert venda.total == 10900
    assert payload["totais"]["valor_total"] == 109.00
    assert _somar_pagamentos(payload) - payload.get("valor_troco", 0.0) == payload["totais"]["valor_total"]


def test_acrescimo_mapeado_para_outras_despesas_fecha_a_nota():
    """
    Demonstra a correção da Fase 1: com o acréscimo entrando como vOutro,
    o total da nota bate com Venda.total e o grupo <pag> fecha.
    """
    itens = [_item_venda(1, _produto(1), quantidade=1, valor_unitario=10000)]
    venda = _venda(itens, [_pagamento(10900, codigo_sefaz="03")], acrescimo=900)

    payload = _montar(venda)

    assert payload["totais"]["valor_outras_despesas"] == 9.00
    assert payload["totais"]["valor_total"] == 109.00
    assert _somar_pagamentos(payload) == payload["totais"]["valor_total"]


def test_multiplos_pagamentos_saem_com_o_codigo_sefaz_de_cada_forma():
    itens = [_item_venda(1, _produto(1), quantidade=1, valor_unitario=10000)]
    venda = _venda(itens, [
        _pagamento(6000, codigo_sefaz="01", nome="Dinheiro"),
        _pagamento(4000, codigo_sefaz="03", nome="Cartao de Credito"),
    ])

    payload = _montar(venda)

    assert payload["formas_pagamento"] == [
        {"forma_pagamento": "01", "valor_pagamento": 60.00},
        {"forma_pagamento": "03", "valor_pagamento": 40.00},
    ]
    assert _somar_pagamentos(payload) == payload["totais"]["valor_total"]


# =========================
# 3. Destinatário
# =========================

def test_venda_sem_cliente_sai_como_consumidor_final(venda_simples):
    payload = _montar(venda_simples)

    assert payload["destinatario"] == {"nome": "CONSUMIDOR FINAL"}


def test_cliente_pf_sai_com_cpf_e_indicador_de_nao_contribuinte():
    itens = [_item_venda(1, _produto(1), quantidade=1, valor_unitario=10000)]
    cliente = ClientePF(id=7, nome="Maria Souza", cpf="52998224725")
    cliente.endereco = []
    venda = _venda(itens, [_pagamento(10000)], cliente=cliente)

    payload = _montar(venda)

    assert payload["destinatario"]["cpf"] == "52998224725"
    assert payload["destinatario"]["nome"] == "Maria Souza"
    assert payload["destinatario"]["indicador_ie"] == "9"


def test_cliente_pj_com_ie_sai_como_contribuinte():
    itens = [_item_venda(1, _produto(1), quantidade=1, valor_unitario=10000)]
    cliente = ClientePJ(id=8, razao_social="Compradora LTDA",
                        cnpj="11222333000181", ie="110042490114")
    cliente.endereco = []
    venda = _venda(itens, [_pagamento(10000)], cliente=cliente)

    payload = _montar(venda)

    assert payload["destinatario"]["cnpj"] == "11222333000181"
    assert payload["destinatario"]["indicador_ie"] == "1"


def test_razao_social_com_caractere_invalido_para_xml_e_sanitizada():
    itens = [_item_venda(1, _produto(1), quantidade=1, valor_unitario=10000)]
    cliente = ClientePJ(id=9, razao_social='Silva & Cia <Matriz>', cnpj="11222333000181")
    cliente.endereco = []
    venda = _venda(itens, [_pagamento(10000)], cliente=cliente)

    payload = _montar(venda)

    assert payload["destinatario"]["razao_social"] == "Silva Cia Matriz"


# =========================
# 4. Guardas do builder
# =========================

def test_item_avulso_sem_produto_e_recusado():
    itens = [_item_venda(1, _produto(1), quantidade=1, valor_unitario=10000)]
    itens[0].produto = None
    venda = _venda(itens, [_pagamento(10000)])

    with pytest.raises(ValueError, match="avulso"):
        montar_payload_nfe(
            empresa=_empresa(),
            endereco_empresa=_endereco_empresa(),
            fiscal_settings=_fiscal_settings(),
            venda=venda,
            nota_fiscal=None,
            resultado_calculo=None,
        )


def test_produto_sem_codigo_de_barras_sai_como_sem_gtin():
    itens = [_item_venda(1, _produto(1, codigo_barras=None), quantidade=1, valor_unitario=10000)]
    venda = _venda(itens, [_pagamento(10000)])

    payload = _montar(venda)

    assert payload["items"][0]["codigo_barras_comercial"] == "SEM GTIN"
