# ---------------------------------------------------------------------------
# ARQUIVO: test_tributacao_padrao_no_gate.py
# DESCRIÇÃO: O produto cadastrado só com NCM emite, porque o resto desce da
#            tributação padrão da loja.
#
# É a prova de ponta da Fase 2 (`docs/cadastro-produto-plano.md`): o gate de
# emissão passou a conferir a tributação EFETIVA, não a linha isolada de
# `produto_fiscal`.
# ---------------------------------------------------------------------------

import pytest
from fastapi.testclient import TestClient

from app.db.models.empresa import Empresa
from app.db.models.produto import Produto
from app.db.models.produto_fiscal import ProdutoFiscal
from app.db.models.tributacao import RegraTributariaNcm, TributacaoPadrao
from app.services.fiscal.validators import verificar_produto_fiscal

TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"
TEST_HWID = "test-terminal-hwid"


@pytest.fixture(scope="function")
def header_with_token(client: TestClient, db_session, create_test_empresa) -> dict:
    login = client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": TEST_HWID,
    })
    if login.status_code != 200:
        pytest.skip("Falha na autenticação do usuário de teste.")
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture
def produto_so_com_ncm(client: TestClient, db_session, header_with_token) -> Produto:
    """O cadastro que queremos que baste: nome, preço e NCM."""
    criado = client.post("/api/v1/produtos/", json={
        "nome": "Caneta Esferográfica Azul",
        "codigo_produto": "CAN-CASCATA",
        "unidade_medida": "UN",
        "estoque": {"valor_varejo": 100, "quantidade": 10},
    }, headers=header_with_token)
    assert criado.status_code == 201, criado.text

    produto_id = criado.json()["id"]
    db_session.add(ProdutoFiscal(produto_id=produto_id, ncm="96081000"))
    db_session.commit()

    return db_session.query(Produto).filter(Produto.id == produto_id).first()


def _pendencias(db_session, produto, simples=True) -> list:
    pendencias: list = []
    verificar_produto_fiscal(db_session, produto, pendencias, simples_nacional=simples)
    return pendencias


def _campos(pendencias) -> set:
    return {p.campo for p in pendencias}


# =========================
# Antes e depois do padrão da loja
# =========================

def test_so_com_ncm_e_sem_padrao_o_gate_recusa(db_session, produto_so_com_ncm):
    """Sem tributação padrão, falta tudo — que é o comportamento de hoje."""
    campos = _campos(_pendencias(db_session, produto_so_com_ncm))

    assert "cfop_padrao" in campos
    assert "origem_mercadoria" in campos
    assert "csosn" in campos


def test_padrao_da_loja_faz_o_produto_so_com_ncm_passar(db_session, produto_so_com_ncm):
    """
    A mesma linha de `produto_fiscal`, intocada. O que mudou foi a loja ter
    respondido uma vez o que antes era perguntado em cada produto.
    """
    empresa = db_session.query(Empresa).first()
    db_session.add(TributacaoPadrao(
        empresa_id=empresa.id, csosn="102", cfop_padrao="5102", origem_mercadoria=0,
    ))
    db_session.commit()

    assert _pendencias(db_session, produto_so_com_ncm) == []


def test_regra_do_ncm_com_st_exige_o_cest(db_session, produto_so_com_ncm):
    """
    A regra por NCM marca o produto como ST, e o gate passa a cobrar o CEST —
    a mesma regra de antes, agora alcançando o que veio da cascata.
    """
    empresa = db_session.query(Empresa).first()
    db_session.add(TributacaoPadrao(
        empresa_id=empresa.id, csosn="102", cfop_padrao="5102", origem_mercadoria=0,
    ))
    db_session.add(RegraTributariaNcm(
        empresa_id=empresa.id, ncm="96081000", csosn="500", descricao="Sob ST",
    ))
    db_session.commit()

    campos = _campos(_pendencias(db_session, produto_so_com_ncm))
    assert "cest" in campos

    # Com o CEST na regra, o gate libera.
    regra = db_session.query(RegraTributariaNcm).first()
    regra.cest = "0100100"
    db_session.commit()

    assert _pendencias(db_session, produto_so_com_ncm) == []


def test_produto_continua_podendo_discordar_da_loja(db_session, produto_so_com_ncm):
    """
    A exceção por produto é o nível mais forte: é o que preserva tudo o que já
    está cadastrado nas lojas que emitem hoje.
    """
    empresa = db_session.query(Empresa).first()
    db_session.add(TributacaoPadrao(
        empresa_id=empresa.id, csosn="102", cfop_padrao="5102", origem_mercadoria=0,
    ))
    fiscal = db_session.query(ProdutoFiscal).filter(
        ProdutoFiscal.produto_id == produto_so_com_ncm.id
    ).first()
    fiscal.cfop_padrao = "6102"  # venda interestadual
    db_session.commit()

    from app.services.fiscal.tributacao import fiscal_efetivo

    efetivo = fiscal_efetivo(db_session, produto_so_com_ncm)
    assert efetivo.cfop_padrao == "6102"
    assert efetivo.procedencia["cfop_padrao"] == "produto"
    assert efetivo.csosn == "102"
    assert efetivo.procedencia["csosn"] == "padrao"


# =========================
# Não regredir quem emite hoje
# =========================

def test_sem_tabelas_configuradas_o_gate_e_o_de_antes(db_session, produto_so_com_ncm):
    """
    Nenhuma loja em produção tem linha nas tabelas novas. Para elas o gate
    precisa recusar e aprovar exatamente como antes — o produto completo
    passa, sem depender de configuração nenhuma.
    """
    fiscal = db_session.query(ProdutoFiscal).filter(
        ProdutoFiscal.produto_id == produto_so_com_ncm.id
    ).first()
    fiscal.cfop_padrao = "5102"
    fiscal.origem_mercadoria = 0
    fiscal.csosn = "102"
    db_session.commit()

    assert db_session.query(TributacaoPadrao).count() == 0
    assert db_session.query(RegraTributariaNcm).count() == 0
    assert _pendencias(db_session, produto_so_com_ncm) == []
