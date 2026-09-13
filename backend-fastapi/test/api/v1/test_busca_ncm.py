# ---------------------------------------------------------------------------
# ARQUIVO: test_busca_ncm.py
# DESCRIÇÃO: Achar o NCM pela descrição, sem internet.
#
# Fase 4 do `docs/cadastro-produto-plano.md`. O NCM era um `<input>` de 8
# dígitos, e quem cadastra mouse não decora 8471.60.53. Errar não é detalhe: o
# NCM determina o imposto, o CEST e o valor aproximado dos tributos que sai
# impresso na nota.
# ---------------------------------------------------------------------------

import pytest
from fastapi.testclient import TestClient

from app.db.models.ncm import Ncm

TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"
TEST_HWID = "test-terminal-hwid"

ROTA = "/api/v1/fiscal/ncm"


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
def tabela_ncm(db_session):
    """Uma amostra com os casos que importam, incluindo acento e hierarquia."""
    db_session.query(Ncm).delete()
    db_session.add_all([
        Ncm(
            codigo="96081000",
            descricao="Canetas esferográficas",
            descricao_completa=(
                "Obras diversas. / Canetas esferográficas; canetas e marcadores, "
                "com ponta de feltro / Canetas esferográficas"
            ),
        ),
        Ncm(
            codigo="84716053",
            descricao="Teclados",
            descricao_completa=(
                "Máquinas automáticas para processamento de dados / Unidades de "
                "entrada / Teclados"
            ),
        ),
        Ncm(
            codigo="40111000",
            descricao="Dos tipos utilizados em automóveis de passageiros",
            descricao_completa="Pneumáticos novos, de borracha / Dos tipos utilizados em automóveis",
        ),
    ])
    db_session.commit()


def _buscar(client, headers, termo):
    return client.get(ROTA, params={"buscar": termo}, headers=headers)


# =========================
# O que o lojista digita
# =========================

def test_acha_pela_descricao(client, header_with_token, licenca_com_nfe, tabela_ncm):
    """O caso que originou a fase: digitar 'caneta' em vez de 9608.10.00."""
    corpo = _buscar(client, header_with_token, "caneta").json()

    codigos = [r["codigo"] for r in corpo["resultados"]]
    assert "96081000" in codigos


def test_acha_sem_acento(client, header_with_token, licenca_com_nfe, tabela_ncm):
    """Ninguém digita 'esferográficas' com acento no balcão."""
    corpo = _buscar(client, header_with_token, "esferograficas").json()

    assert "96081000" in [r["codigo"] for r in corpo["resultados"]]


def test_acha_pela_hierarquia_e_nao_so_pela_descricao_propria(
    client, header_with_token, licenca_com_nfe, tabela_ncm
):
    """
    A descrição própria do 4011.10.00 é "Dos tipos utilizados em automóveis de
    passageiros" — a palavra "pneu" só existe no ancestral. Sem varrer a
    descrição completa, procurar "pneu" não acharia nada.
    """
    corpo = _buscar(client, header_with_token, "pneumaticos").json()

    assert "40111000" in [r["codigo"] for r in corpo["resultados"]]


def test_acha_pelo_codigo_com_e_sem_pontos(
    client, header_with_token, licenca_com_nfe, tabela_ncm
):
    """Quem copia do fornecedor traz com pontos; o banco guarda sem."""
    com_pontos = _buscar(client, header_with_token, "9608.10.00").json()
    sem_pontos = _buscar(client, header_with_token, "96081000").json()

    assert [r["codigo"] for r in com_pontos["resultados"]] == ["96081000"]
    assert [r["codigo"] for r in sem_pontos["resultados"]] == ["96081000"]


def test_codigo_parcial_lista_a_familia(
    client, header_with_token, licenca_com_nfe, tabela_ncm
):
    """Digitar '8471' enquanto procura deve listar o capítulo, não zero."""
    corpo = _buscar(client, header_with_token, "8471").json()

    assert "84716053" in [r["codigo"] for r in corpo["resultados"]]


def test_duas_palavras_exigem_as_duas(
    client, header_with_token, licenca_com_nfe, tabela_ncm
):
    """
    É a regra do motor de busca da casa: "azul tinta" acha "Tinta azul", e
    "azul" sozinho não traz a base inteira.
    """
    corpo = _buscar(client, header_with_token, "canetas marcadores").json()

    assert "96081000" in [r["codigo"] for r in corpo["resultados"]]

    vazio = _buscar(client, header_with_token, "canetas geladeira").json()
    assert vazio["resultados"] == []


# =========================
# Bordas
# =========================

def test_busca_vazia_nao_devolve_a_base_inteira(
    client, header_with_token, licenca_com_nfe, tabela_ncm
):
    """10 mil linhas numa combo travariam a tela."""
    corpo = client.get(ROTA, headers=header_with_token).json()

    assert corpo["resultados"] == []
    assert corpo["total_na_base"] == 3


def test_resultado_traz_a_descricao_completa(
    client, header_with_token, licenca_com_nfe, tabela_ncm
):
    """É o que o lojista lê para ter certeza de que escolheu o código certo."""
    corpo = _buscar(client, header_with_token, "teclados").json()
    primeiro = corpo["resultados"][0]

    assert primeiro["descricao"] == "Teclados"
    assert "Unidades de entrada" in primeiro["descricao_completa"]
