from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from starlette import status # Boa prática para usar status codes nominais

from app.db.models.usuario import Usuario as UsuarioModel
from app.core.security import hash_password

# Importação adicionada para a busca de clientes (GET)
from app.core.enum import EntityType 

# --- Constantes de Teste ---
TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"
TEST_HWID = "test-terminal-hwid"

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

# =========================
# Teste: Deletar Endereço
# =========================
def test_deletar_endereco(client: TestClient, header_with_token: dict):
    # --- ARRANGE (Preparação) ---
    # Define o payload (corpo da requisição JSON) para o novo cliente PF
    data_client = {
        "email": "joao.silva@meu-pdv.com",
        "contato": "11987654321",
        "observacoes": "Cliente novo, aceita e-mail marketing.",
        "endereco": [
            {
                "logradouro": "Rua das Flores",
                "numero": "456A",
                "complemento": "Casa",
                "bairro": "Jardim América",
                "cidade": "Campinas",
                "estado": "SP",
                "cep": "13010-000"
            },
            {
                "logradouro": "Av. Principal",
                "numero": "20",
                "complemento": "Escritório",
                "bairro": "Centro",
                "cidade": "Belo Horizonte",
                "estado": "MG",
                "cep": "30110-010"
            }
        ],
        "nome": "João Pedro Silva",
        "cpf": "98765432101",
        "rg": "12345678",
        "genero": "MASCULINO",
        "data_nascimento": "1995-12-15"
    }

    # --- ACT 1 & ASSERT 1 (Criação do Cliente com Endereços) ---
    # Envia a requisição POST para o endpoint de criação de PF
    create_response = client.post("/api/v1/clientes/cliente_pf", json=data_client, headers=header_with_token)
    
    # Verifica se a criação foi bem-sucedida (Status 201)
    assert create_response.status_code == status.HTTP_201_CREATED 
    client_data = create_response.json()
    
    # Salva os IDs para uso posterior
    id_endereco_a_deletar = client_data["endereco"][0]["id"]
    id_endereco_remanescente = client_data["endereco"][1]["id"]
    id_cliente = client_data["id"]

    # --- ACT 2 & ASSERT 2 (Deleção do Endereço Específico) ---
    # Monta a URL com Path Parameter (ID do Endereço) e Query Parameters (Contexto de Validação)
    delete_url = (
        f"/api/v1/enderecos/{id_endereco_a_deletar}"
        f"?entidade_id={id_cliente}"
        f"&tipo_entidade={EntityType.CLIENTE.value}" # Usa o valor da Enum (ex: 'CLIENTE')
    )
    
    delete_address_response = client.delete(delete_url, headers=header_with_token)
    
    # Verifica se a deleção retornou o status correto (204 No Content)
    assert delete_address_response.status_code == status.HTTP_204_NO_CONTENT