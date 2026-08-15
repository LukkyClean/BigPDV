import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"
TEST_HWID = "test-terminal-hwid"

PREFIX = "/api/v1/cargos"

BASE_CARGO_DATA = {
    "nome": "Gerente",
    "permissioes": {
        "venda": True,
        "funcionario": True
    }
}

def create_test_cargo(client: TestClient, header_with_token: dict):
    request_url = f"{PREFIX}/"

    response = client.post(
        request_url,
        json=BASE_CARGO_DATA,
        headers=header_with_token
    )

    return response.json()


# =========================
# Fixture de Autenticação
# =========================
@pytest.fixture(scope="function")
def header_with_token(client: TestClient, db_session: Session, create_test_empresa) -> dict:

    login_data = {"username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": TEST_HWID}
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200 
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_criar_cargo_funcionario_com_sucesso(client: TestClient, header_with_token: dict):

    request_url = f"{PREFIX}/"

    response = client.post(
        request_url,
        json=BASE_CARGO_DATA,
        headers=header_with_token
    )

    assert response.status_code == status.HTTP_201_CREATED

def test_buscar_todos_os_cargos_no_sistema_com_sucesso(client: TestClient, header_with_token: dict):
    
    cargo_json = create_test_cargo(client, header_with_token)

    request_url = f"{PREFIX}/"

    response = client.get(
        request_url,
        headers=header_with_token
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1

def test_editar_um_cargo_no_sistema_com_sucesso(client: TestClient, header_with_token: dict):

    cargo_json = create_test_cargo(client, header_with_token)

    cargo_json["nome"] = "Vendedor"
    cargo_json["permissoes"]["funcionario"] = False

    request_url = f"{PREFIX}/{cargo_json["id"]}"

    response = client.put(
        request_url,
        json=cargo_json,
        headers=header_with_token
    )

    assert response.status_code == status.HTTP_200_OK
    cargo_updated_json = response.json()
    assert cargo_updated_json["nome"] == "Vendedor"
    assert cargo_updated_json["permissoes"]["funcionario"] == False

def test_excluir_um_cargo_no_sistema_com_sucesso(client: TestClient, header_with_token: dict):
    
    cargo_json = create_test_cargo(client, header_with_token)

    request_url = f"{PREFIX}/{cargo_json["id"]}"

    response = client.delete(
        request_url,
        headers=header_with_token
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    