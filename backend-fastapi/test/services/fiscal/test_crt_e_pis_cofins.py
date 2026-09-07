# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/test_crt_e_pis_cofins.py
# DESCRIÇÃO: Testes do CRT (achados C7 e C18) e do PIS/COFINS do Simples (A5).
#
# O erro que originou isto: `"simples" in regime.lower()` casava também com
# "Simples Nacional (Excesso de Sublimite)" — que é CRT 2 e usa CST, não CSOSN.
# ---------------------------------------------------------------------------

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.aliquota_uf import AliquotaUF
from app.db.models.empresa import Empresa
from app.db.models.produto import Produto
from app.db.models.produto_fiscal import ProdutoFiscal
from app.db.models.venda import Venda
from app.db.models.venda_produto import ProdutoVenda
from app.services.fiscal.helpers import (
    CRT_MEI,
    CRT_REGIME_NORMAL,
    CRT_SIMPLES_EXCESSO,
    CRT_SIMPLES_NACIONAL,
    crt_do_rotulo,
    crt_efetivo,
    obter_crt,
    pis_cofins_por_fora,
    regime_apuracao,
    usa_csosn,
)
from app.services.fiscal.tax_engine.resolver import resolver_aliquotas_venda

ZERO = Decimal("0")


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    sessao = Session()
    # Fora do Simples o resolver exige AliquotaUF cadastrada para a UF.
    sessao.add(AliquotaUF(
        uf="SP", aliquota_icms_interna=1800,
        aliquota_pis_padrao=165, aliquota_cofins_padrao=760,
    ))
    sessao.commit()
    yield sessao
    sessao.close()


# =========================
# 1. Tradução de rótulo para CRT
# =========================

@pytest.mark.parametrize("rotulo, esperado", [
    ("Simples Nacional", CRT_SIMPLES_NACIONAL),
    ("Simples Nacional (Excesso de Sublimite)", CRT_SIMPLES_EXCESSO),
    ("Regime Normal", CRT_REGIME_NORMAL),
    ("MEI", CRT_MEI),
    ("  simples nacional  ", CRT_SIMPLES_NACIONAL),   # espaços e caixa
    ("SIMPLES NACIONAL", CRT_SIMPLES_NACIONAL),
    # Presumido e Real são os dois sabores do Regime Normal: ambos CRT 3.
    # O que os separa é o regime de apuração do PIS/COFINS, não o CRT.
    ("Lucro Presumido", CRT_REGIME_NORMAL),
    ("Lucro Real", CRT_REGIME_NORMAL),
    ("Microempreendedor Individual", CRT_MEI),
    ("", None),
    (None, None),
    ("Coisa Que Não Existe", None),
])
def test_traduz_rotulo_da_interface_para_crt(rotulo, esperado):
    assert crt_do_rotulo(rotulo) == esperado


# =========================
# 1b. CRT a persistir no save — o MEI que ninguém conseguia cadastrar
# =========================

@pytest.mark.parametrize("regime, natureza, esperado", [
    # O rótulo manda quando é reconhecido.
    ("Simples Nacional", None, CRT_SIMPLES_NACIONAL),
    ("MEI", None, CRT_MEI),
    ("Lucro Real", None, CRT_REGIME_NORMAL),
    # Sem rótulo útil, a natureza jurídica ainda revela o MEI.
    (None, "MEI", CRT_MEI),
    ("", "mei", CRT_MEI),
    ("Coisa Que Não Existe", "MEI", CRT_MEI),
    # O rótulo tem precedência sobre a natureza jurídica.
    ("Simples Nacional", "MEI", CRT_SIMPLES_NACIONAL),
    # Sem nenhum dos dois, Regime Normal.
    (None, None, CRT_REGIME_NORMAL),
    (None, "LTDA", CRT_REGIME_NORMAL),
])
def test_crt_efetivo_no_momento_do_save(regime, natureza, esperado):
    """
    Regressão do achado que motivou esta fase: a coluna `crt` existia e nenhum
    serviço a escrevia, então todo MEI caía em Regime Normal e emitia com CST
    no lugar de CSOSN.
    """
    assert crt_efetivo(regime, natureza) == esperado


# =========================
# 2. CRT efetivo da empresa
# =========================

def _empresa(crt=None, regime=None):
    return Empresa(
        id=1, razao_social="Loja Teste", documento="11222333000181",
        is_cnpj=True, crt=crt, regime_tributario=regime,
    )


def test_coluna_crt_tem_precedencia_sobre_o_texto():
    """Se os dois discordam, vale a coluna — o texto é só rótulo de tela."""
    empresa = _empresa(crt=CRT_REGIME_NORMAL, regime="Simples Nacional")

    assert obter_crt(empresa) == CRT_REGIME_NORMAL


def test_cai_no_texto_enquanto_a_coluna_estiver_vazia():
    assert obter_crt(_empresa(regime="Simples Nacional")) == CRT_SIMPLES_NACIONAL


def test_sem_crt_e_sem_rotulo_conhecido_assume_regime_normal():
    """
    Padrão seguro: destacar ICMS a mais se corrige por carta de correção;
    usar CSOSN sem ser do Simples é rejeição na origem.
    """
    assert obter_crt(_empresa(regime="Lucro Presumido")) == CRT_REGIME_NORMAL
    assert obter_crt(_empresa()) == CRT_REGIME_NORMAL
    assert obter_crt(None) == CRT_REGIME_NORMAL


@pytest.mark.parametrize("crt_invalido", [0, 5, 99, -1, "1"])
def test_crt_fora_da_faixa_e_ignorado(crt_invalido):
    empresa = _empresa(crt=crt_invalido, regime="Simples Nacional")

    assert obter_crt(empresa) == CRT_SIMPLES_NACIONAL  # cai no rótulo


# =========================
# 3. Quem usa CSOSN — o achado C18
# =========================

@pytest.mark.parametrize("crt, esperado", [
    (CRT_SIMPLES_NACIONAL, True),
    (CRT_MEI, True),
    (CRT_SIMPLES_EXCESSO, False),   # o caso que estava errado
    (CRT_REGIME_NORMAL, False),
])
def test_apenas_crt_1_e_4_usam_csosn(crt, esperado):
    assert usa_csosn(crt) is esperado


def test_excesso_de_sublimite_nao_e_tratado_como_simples():
    """
    Achado C18: `"simples" in regime.lower()` dava True aqui e mandava a nota
    com CSOSN. CRT 2 tributa o excedente pelo regime normal e usa CST.
    """
    empresa = _empresa(regime="Simples Nacional (Excesso de Sublimite)")

    assert obter_crt(empresa) == CRT_SIMPLES_EXCESSO
    assert usa_csosn(obter_crt(empresa)) is False
    assert pis_cofins_por_fora(obter_crt(empresa)) is False


# =========================
# 4. PIS/COFINS por regime — o achado A5
# =========================

def _montar_venda(cst_pis="01", cst_cofins="01", aliquota_pis=165,
                  aliquota_cofins=760, acrescimo=0, com_fiscal=True):
    """
    Venda em memória, sem persistir.

    O resolver só lê atributos (itens, cliente, entrega, acrescimo) e usa a
    sessão apenas para buscar AliquotaUF — não precisa de linhas no banco,
    o que evita arrastar Funcionario, Cliente e as FKs de uma venda real.
    """
    produto = Produto(id=1, nome="Teclado", codigo_produto="P1", unidade_medida="UN")
    produto.fiscal = ProdutoFiscal(
        produto_id=1, ncm="84716052", cfop_padrao="5102", origem_mercadoria=0,
        cst_icms="00", csosn="102", aliquota_icms=1800,
        aliquota_pis=aliquota_pis, aliquota_cofins=aliquota_cofins,
        cst_pis=cst_pis, cst_cofins=cst_cofins,
    ) if com_fiscal else None

    item = ProdutoVenda(
        id=1, produto_id=1, quantidade=1,
        valor_unitario=10000, subtotal=10000, desconto=0,
    )
    item.produto = produto

    venda = Venda(
        id=1, numero_venda=1001, subtotal=10000,
        total=10000 + acrescimo, entrega=0, acrescimo=acrescimo,
    )
    venda.itens = [item]
    venda.pagamentos = []
    venda.cliente = None
    return venda


def test_simples_nacional_sai_com_cst_49_e_zerado(db):
    """
    No Simples o PIS/COFINS está na guia única. Destacar alíquota na nota
    gera bitributação aparente — era o que o resolver fazia por default.
    """
    venda = _montar_venda()

    itens, _ = resolver_aliquotas_venda(db, venda, "SP", simples_nacional=True)

    assert itens[0].cst_pis == "49"
    assert itens[0].cst_cofins == "49"
    assert itens[0].aliquota_pis == ZERO
    assert itens[0].aliquota_cofins == ZERO


def test_simples_ignora_aliquota_cadastrada_no_produto(db):
    """Mesmo com alíquota no cadastro, o Simples não destaca."""
    venda = _montar_venda(aliquota_pis=165)

    itens, _ = resolver_aliquotas_venda(db, venda, "SP", simples_nacional=True)

    assert itens[0].aliquota_pis == ZERO


def test_regime_normal_mantem_aliquotas_do_cadastro(db):
    venda = _montar_venda(aliquota_pis=165)

    itens, _ = resolver_aliquotas_venda(db, venda, "SP", simples_nacional=False)

    assert itens[0].cst_pis == "01"
    assert itens[0].aliquota_pis == Decimal("1.65")
    assert itens[0].aliquota_cofins == Decimal("7.60")


def test_sem_cadastro_o_default_vem_do_regime_de_apuracao(db):
    """
    Correção de 05/09/2026: o default era 1,65/7,60 para todo mundo, rotulado
    como "Lucro Presumido cumulativo" — que é justamente o regime onde esses
    números NÃO valem. Cumulativo é 0,65/3,00.
    """
    venda = _montar_venda(cst_pis=None, cst_cofins=None,
                          aliquota_pis=None, aliquota_cofins=None)

    itens, _ = resolver_aliquotas_venda(
        db, venda, "SP", simples_nacional=False, regime_apuracao="CUMULATIVO",
    )

    assert itens[0].cst_pis == "01"
    assert itens[0].aliquota_pis == Decimal("0.65")
    assert itens[0].aliquota_cofins == Decimal("3.00")


def test_lucro_real_usa_as_aliquotas_nao_cumulativas(db):
    venda = _montar_venda(cst_pis=None, cst_cofins=None,
                          aliquota_pis=None, aliquota_cofins=None)

    itens, _ = resolver_aliquotas_venda(
        db, venda, "SP", simples_nacional=False,
        regime_apuracao="NAO_CUMULATIVO",
    )

    assert itens[0].aliquota_pis == Decimal("1.65")
    assert itens[0].aliquota_cofins == Decimal("7.60")


def test_default_do_resolver_e_o_cumulativo(db):
    """Sem informar o regime, assume-se o mais conservador (Presumido)."""
    venda = _montar_venda(cst_pis=None, cst_cofins=None,
                          aliquota_pis=None, aliquota_cofins=None)

    itens, _ = resolver_aliquotas_venda(db, venda, "SP", simples_nacional=False)

    assert itens[0].aliquota_pis == Decimal("0.65")


def test_aliquota_uf_nao_manda_mais_em_pis_cofins(db):
    """
    A armadilha desta correção: enquanto o resolver consultava
    `aliquota_uf.aliquota_pis_padrao`, trocar a constante não surtia efeito
    nenhum — as 27 UFs estavam semeadas em 165/760 e o valor semeado vencia.

    A fixture semeia SP com 165/760 de propósito. Se este teste voltar a ver
    1,65, é porque alguém religou a leitura por UF.
    """
    venda = _montar_venda(cst_pis=None, cst_cofins=None,
                          aliquota_pis=None, aliquota_cofins=None)

    itens, _ = resolver_aliquotas_venda(
        db, venda, "SP", simples_nacional=False, regime_apuracao="CUMULATIVO",
    )

    assert itens[0].aliquota_pis == Decimal("0.65")   # regime, não os 165 da UF


@pytest.mark.parametrize("regime, esperado", [
    ("Lucro Real", "NAO_CUMULATIVO"),
    ("lucro real", "NAO_CUMULATIVO"),
    ("Lucro Presumido", "CUMULATIVO"),
    ("Regime Normal", "CUMULATIVO"),     # rótulo antigo, genérico
    ("Simples Nacional", "CUMULATIVO"),  # não chega a ser usado (CST 49)
    (None, "CUMULATIVO"),
    ("", "CUMULATIVO"),
])
def test_regime_de_apuracao_por_rotulo(regime, esperado):
    assert regime_apuracao(_empresa(regime=regime)) == esperado


def test_acrescimo_da_venda_vira_outras_despesas(db):
    """Regressão da Fase 1: o acréscimo precisa continuar virando vOutro."""
    venda = _montar_venda(acrescimo=900)

    _, dados = resolver_aliquotas_venda(db, venda, "SP", simples_nacional=True)

    assert dados.outras_despesas == Decimal("9.00")
