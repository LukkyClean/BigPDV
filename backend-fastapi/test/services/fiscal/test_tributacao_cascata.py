# ---------------------------------------------------------------------------
# ARQUIVO: test_tributacao_cascata.py
# DESCRIÇÃO: produto → regra por NCM → tributação padrão da loja.
#
# A propriedade mais importante deste arquivo é a última seção: sem nada
# configurado, a cascata é INERTE. Três lojas emitem hoje com o modelo antigo
# e nenhuma delas vai ter linha nas tabelas novas.
# Ver `docs/cadastro-produto-plano.md`, §4.D0.
# ---------------------------------------------------------------------------

from types import SimpleNamespace

from app.services.fiscal.tributacao import FiscalEfetivo, mesclar


def _fonte(**campos) -> SimpleNamespace:
    """Uma fonte da cascata (produto, regra de NCM ou padrão da loja)."""
    return SimpleNamespace(**campos)


# =========================
# Precedência
# =========================

def test_padrao_da_loja_preenche_o_que_o_produto_nao_diz():
    """O caso comum: produto só com NCM, todo o resto desce da loja."""
    efetivo = mesclar(
        produto_fiscal=_fonte(ncm="96081000"),
        padrao=_fonte(csosn="102", cfop_padrao="5102", origem_mercadoria=0),
    )

    assert efetivo.ncm == "96081000"
    assert efetivo.csosn == "102"
    assert efetivo.cfop_padrao == "5102"
    assert efetivo.procedencia["csosn"] == "padrao"
    assert efetivo.procedencia["ncm"] == "produto"


def test_regra_do_ncm_vence_o_padrao_da_loja():
    """O pneu tem ST; o resto da loja, não."""
    efetivo = mesclar(
        produto_fiscal=_fonte(ncm="40111000"),
        regra_ncm=_fonte(csosn="500", cest="0100100"),
        padrao=_fonte(csosn="102", cfop_padrao="5102"),
    )

    assert efetivo.csosn == "500"
    assert efetivo.cest == "0100100"
    assert efetivo.procedencia["csosn"] == "ncm"
    # O que a regra não diz continua descendo da loja.
    assert efetivo.cfop_padrao == "5102"
    assert efetivo.procedencia["cfop_padrao"] == "padrao"


def test_produto_vence_todo_mundo():
    """A exceção por produto é o nível mais forte — é o que preserva o que já está cadastrado."""
    efetivo = mesclar(
        produto_fiscal=_fonte(ncm="40111000", csosn="101"),
        regra_ncm=_fonte(csosn="500"),
        padrao=_fonte(csosn="102"),
    )

    assert efetivo.csosn == "101"
    assert efetivo.procedencia["csosn"] == "produto"


def test_vazio_nao_apaga_o_que_vem_de_baixo():
    """
    Vazio significa "não decido isto", nunca "apague". Um produto salvo com
    CSOSN em branco tem de continuar herdando o da loja.
    """
    efetivo = mesclar(
        produto_fiscal=_fonte(ncm="96081000", csosn="", cfop_padrao=None),
        padrao=_fonte(csosn="102", cfop_padrao="5102"),
    )

    assert efetivo.csosn == "102"
    assert efetivo.cfop_padrao == "5102"


# =========================
# Zero não é vazio
# =========================

def test_origem_zero_do_produto_nao_cai_para_o_padrao():
    """
    `0` é "Nacional", uma resposta — e a mais comum delas. Tratá-la como
    ausente faria o produto nacional herdar a origem de importado configurada
    na loja, e isso é nota aceita e errada.
    """
    efetivo = mesclar(
        produto_fiscal=_fonte(ncm="96081000", origem_mercadoria=0),
        padrao=_fonte(origem_mercadoria=1),
    )

    assert efetivo.origem_mercadoria == 0
    assert efetivo.procedencia["origem_mercadoria"] == "produto"


def test_aliquota_zero_e_uma_decisao_fiscal():
    """Alíquota zero é escolha legítima (monofásico, por exemplo), não omissão."""
    efetivo = mesclar(
        produto_fiscal=_fonte(aliquota_pis=0),
        padrao=_fonte(aliquota_pis=165),
    )

    assert efetivo.aliquota_pis == 0


# =========================
# Fronteiras: o que NÃO desce
# =========================

def test_ncm_e_gtin_nunca_vem_da_loja():
    """
    São do produto e de mais ninguém. Herdar NCM do padrão faria todo produto
    sem classificação sair na nota como se fosse outra mercadoria.
    """
    efetivo = mesclar(
        produto_fiscal=_fonte(ncm=None, gtin_tributavel=None),
        padrao=_fonte(ncm="99999999", gtin_tributavel="7891000000000"),
    )

    assert efetivo.ncm is None
    assert efetivo.gtin_tributavel is None


def test_cest_desce_do_ncm_mas_nunca_do_padrao_da_loja():
    """
    Quem determina a substituição tributária é o NCM. Um CEST no padrão da
    loja marcaria o catálogo inteiro como ST.
    """
    do_ncm = mesclar(produto_fiscal=_fonte(ncm="40111000"), regra_ncm=_fonte(cest="0100100"))
    assert do_ncm.cest == "0100100"
    assert do_ncm.procedencia["cest"] == "ncm"

    do_padrao = mesclar(produto_fiscal=_fonte(ncm="96081000"), padrao=_fonte(cest="0100100"))
    assert do_padrao.cest is None


# =========================
# A propriedade que permite subir isto em produção
# =========================

def test_sem_nenhuma_fonte_devolve_none():
    """Mantém a mensagem "produto sem dados fiscais" do gate de emissão."""
    assert mesclar() is None


def test_sem_padrao_e_sem_regra_o_resultado_e_o_proprio_produto():
    """
    Loja que nunca abriu a tela de tributação: todo campo sai do produto, com
    procedência "produto" — exatamente o comportamento de antes da cascata.
    """
    produto = _fonte(
        ncm="85171231", cfop_padrao="5102", origem_mercadoria=0,
        csosn="102", unidade_tributavel="UN",
    )

    efetivo = mesclar(produto_fiscal=produto)

    assert efetivo.ncm == "85171231"
    assert efetivo.cfop_padrao == "5102"
    assert efetivo.csosn == "102"
    assert efetivo.unidade_tributavel == "UN"
    assert set(efetivo.procedencia.values()) == {"produto"}


def test_efetivo_tem_os_mesmos_nomes_de_campo_do_produto_fiscal():
    """
    Quem lê (payload_builder, tax_engine, validators) não pode precisar saber
    se recebeu um `ProdutoFiscal` ou um `FiscalEfetivo`.
    """
    from app.db.models.produto_fiscal import ProdutoFiscal

    colunas = {c.name for c in ProdutoFiscal.__table__.columns}
    colunas -= {"id", "produto_id", "data_atualizacao"}
    atributos = set(FiscalEfetivo.__dataclass_fields__) - {"procedencia"}

    assert colunas <= atributos, f"faltam no FiscalEfetivo: {colunas - atributos}"
