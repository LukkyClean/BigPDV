# ---------------------------------------------------------------------------
# Regressao: o login exige HWID.
#
# O HWID identifica o terminal e e o que faz o limite da licenca valer. Antes,
# `hwid` tinha default "" no schema e o endpoint passava `hwid or ""` adiante:
# um cliente que simplesmente OMITISSE o campo logava com 200 sem ocupar vaga,
# porque a API externa de licenca aceita string vazia. Qualquer hwid real era
# recusado com 403 (LIMITE_TERMINAIS), mas o ausente entrava.
#
# Estes testes travam o contrato: sem hwid, sem login.
# ---------------------------------------------------------------------------

import pytest
from fastapi.testclient import TestClient

# --- Constantes de Teste (declaradas localmente, como nos demais arquivos:
#     importar de test.conftest carrega o conftest uma segunda vez e cria
#     outra engine, quebrando as fixtures) ---
TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"
TEST_HWID = "test-terminal-hwid"


@pytest.mark.parametrize(
    "payload_hwid, descricao",
    [
        ({}, "campo ausente"),
        ({"hwid": ""}, "string vazia"),
        ({"hwid": "   "}, "so espacos"),
    ],
)
def test_login_sem_hwid_e_recusado(
    client: TestClient, db_session, create_test_empresa, payload_hwid, descricao
):
    """Login sem HWID utilizavel deve ser recusado com 400 (era 200 + token)."""
    resposta = client.post(
        "/api/v1/auth/login",
        json={
            "email": TEST_USER_EMAIL,
            "senha": TEST_USER_PASSWORD,
            **payload_hwid,
        },
    )

    assert resposta.status_code == 400, (
        f"HWID '{descricao}' deveria ser recusado, veio {resposta.status_code}: "
        f"{resposta.text}"
    )
    assert "access_token" not in resposta.text


def test_login_com_hwid_funciona(client: TestClient, db_session, create_test_empresa):
    """O caminho feliz continua intacto: com HWID, o login emite o token."""
    resposta = client.post(
        "/api/v1/auth/login",
        json={
            "email": TEST_USER_EMAIL,
            "senha": TEST_USER_PASSWORD,
            "hwid": TEST_HWID,
        },
    )

    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["access_token"]


def test_login_form_data_sem_hwid_e_recusado(
    client: TestClient, db_session, create_test_empresa
):
    """O caminho form-data (Swagger) nao pode ser uma porta dos fundos."""
    resposta = client.post(
        "/api/v1/auth/login",
        data={"username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )

    assert resposta.status_code == 400, resposta.text
    assert "access_token" not in resposta.text
