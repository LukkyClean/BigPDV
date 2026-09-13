# ---------------------------------------------------------------------------
# ARQUIVO: test_validacao_produto_no_cadastro.py
# DESCRIÇÃO: O que a SEFAZ recusaria é recusado no CADASTRO, nomeando o campo.
#
# Fase 3 do `docs/cadastro-produto-plano.md`. A regra não é reescrita: o
# endpoint chama a MESMA função do gate de emissão, sobre um rascunho.
#
# Ter duas conferências seria a pior combinação possível — o cadastro
# aprovaria o que a emissão recusa, e o lojista descobriria na SEFAZ. Foi o que
# aconteceu em 12/09/2026.
# ---------------------------------------------------------------------------

import pytest
from fastapi.testclient import TestClient

from app.db.models.empresa import Empresa
from app.db.models.tributacao import RegraTributariaNcm, TributacaoPadrao

TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"
TEST_HWID = "test-terminal-hwid"

ROTA = "/api/v1/fiscal/validar/produto"


@pytest.fixture(scope="function")
def header_with_token(client: TestClient, db_session, create_test_empresa) -> dict:
    login = client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": TEST_HWID,
    })
    if login.status_code != 200:
        pytest.skip("Falha na autenticação do usuário de teste.")
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture
def licenca_com_nfe(monkeypatch):
    from app.core import modulos as modulos_mod
    monkeypatch.setattr(
        modulos_mod.licenca_service, "modulos_da_licenca", lambda db: ["NFE"]
    )


@pytest.fixture
def empresa_simples(db_session, header_with_token):
    """O regime das lojas em produção: Simples Nacional, CSOSN."""
    empresa = db_session.query(Empresa).first()
    empresa.regime_tributario = "Simples Nacional"
    empresa.crt = 1
    db_session.commit()
    return empresa


def _validar(client, headers, **campos):
    return client.post(ROTA, json=campos, headers=headers)


# =========================
# O caminho feliz e o incompleto
# =========================

def test_produto_completo_pode_emitir(client, header_with_token, licenca_com_nfe, empresa_simples):
    resposta = _validar(
        client, header_with_token,
        ncm="96081000", cfop_padrao="5102", origem_mercadoria=0, csosn="102",
    )

    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["pode_emitir"] is True
    assert resposta.json()["pendencias"] == []


def test_pendencia_vem_com_o_nome_do_campo(client, header_with_token, licenca_com_nfe, empresa_simples):
    """
    É a diferença entre "corrija o cadastro" e "falta o CFOP" — a tela precisa
    do campo para marcar o input certo.
    """
    resposta = _validar(client, header_with_token, ncm="96081000")

    corpo = resposta.json()
    assert corpo["pode_emitir"] is False
    campos = {p["campo"] for p in corpo["pendencias"]}
    assert "cfop_padrao" in campos
    assert "origem_mercadoria" in campos
    assert "csosn" in campos
    assert all(p["mensagem"] for p in corpo["pendencias"])


# =========================
# A cascata entra na conferência
# =========================

def test_so_com_ncm_passa_quando_a_loja_ja_respondeu(
    client, db_session, header_with_token, licenca_com_nfe, empresa_simples
):
    """
    Sem a cascata, um produto cadastrado só com NCM apareceria cheio de
    pendências — quando na verdade a loja já respondeu tudo na tributação
    padrão. A tela mostraria erro onde não há.
    """
    db_session.add(TributacaoPadrao(
        empresa_id=empresa_simples.id, csosn="102", cfop_padrao="5102", origem_mercadoria=0,
    ))
    db_session.commit()

    resposta = _validar(client, header_with_token, ncm="96081000")

    assert resposta.json()["pode_emitir"] is True


def test_procedencia_diz_de_onde_veio_cada_valor(
    client, db_session, header_with_token, licenca_com_nfe, empresa_simples
):
    """Campo preenchido sem explicação, num formulário fiscal, é pior que vazio."""
    db_session.add(TributacaoPadrao(
        empresa_id=empresa_simples.id, csosn="102", cfop_padrao="5102", origem_mercadoria=0,
    ))
    db_session.commit()

    corpo = _validar(client, header_with_token, ncm="96081000").json()

    assert corpo["procedencia"]["csosn"] == "padrao"
    assert corpo["procedencia"]["ncm"] == "produto"


# =========================
# As regras que só a SEFAZ dizia
# =========================

def test_st_exige_cest(client, header_with_token, licenca_com_nfe, empresa_simples):
    """
    O CSOSN 500 indica imposto já pago por substituição — e sem CEST a SEFAZ
    recusa. Antes isso só aparecia na emissão.
    """
    resposta = _validar(
        client, header_with_token,
        ncm="40111000", cfop_padrao="5405", origem_mercadoria=0, csosn="500",
    )

    corpo = resposta.json()
    assert corpo["pode_emitir"] is False
    assert "cest" in {p["campo"] for p in corpo["pendencias"]}


def test_regra_do_ncm_com_cest_resolve_o_produto(
    client, db_session, header_with_token, licenca_com_nfe, empresa_simples
):
    """Quem cadastrou a regra do NCM não precisa repetir o CEST em cada pneu."""
    db_session.add(RegraTributariaNcm(
        empresa_id=empresa_simples.id, ncm="40111000", csosn="500", cest="0100100",
    ))
    db_session.add(TributacaoPadrao(
        empresa_id=empresa_simples.id, cfop_padrao="5405", origem_mercadoria=0,
    ))
    db_session.commit()

    resposta = _validar(client, header_with_token, ncm="40111000")

    assert resposta.json()["pode_emitir"] is True


def test_codigo_que_o_motor_nao_calcula_e_recusado(
    client, header_with_token, licenca_com_nfe, empresa_simples
):
    """
    O CSOSN 900 existe na tabela da SEFAZ e o sistema não sabe calcular. Sem
    este aviso, ele salva no cadastro e é recusado só na emissão.
    """
    resposta = _validar(
        client, header_with_token,
        ncm="96081000", cfop_padrao="5102", origem_mercadoria=0, csosn="900",
    )

    corpo = resposta.json()
    assert corpo["pode_emitir"] is False
    mensagens = " ".join(p["mensagem"] for p in corpo["pendencias"])
    assert "900" in mensagens and "calculado" in mensagens


def test_formato_errado_e_apontado(client, header_with_token, licenca_com_nfe, empresa_simples):
    """NCM com menos de 8 dígitos é recusa na origem."""
    resposta = _validar(
        client, header_with_token,
        ncm="123", cfop_padrao="5102", origem_mercadoria=0, csosn="102",
    )

    # O schema já barra antes de chegar na regra — 422 com o campo nomeado.
    assert resposta.status_code == 422, resposta.text


# =========================
# Não confere o que este regime não usa
# =========================

def test_simples_nao_cobra_cst_de_pis_cofins(
    client, header_with_token, licenca_com_nfe, empresa_simples
):
    """
    No Simples o motor força CST 49 e ignora o cadastro. Exigir preenchimento
    de campo que será descartado é pedir digitação para nada — e era o que
    acontecia com a maioria dos lojistas.
    """
    corpo = _validar(
        client, header_with_token,
        ncm="96081000", cfop_padrao="5102", origem_mercadoria=0, csosn="102",
    ).json()

    campos = {p["campo"] for p in corpo["pendencias"]}
    assert "cst_pis" not in campos
    assert "cst_cofins" not in campos


def test_validar_nao_emite_nem_grava_nada(
    client, db_session, header_with_token, licenca_com_nfe, empresa_simples
):
    """
    É conferência, não cadastro. Nenhuma linha nova, nenhum número reservado.
    """
    from app.db.models.documento_fiscal import DocumentoFiscal

    antes = db_session.query(DocumentoFiscal).count()
    _validar(client, header_with_token, ncm="96081000")
    assert db_session.query(DocumentoFiscal).count() == antes
