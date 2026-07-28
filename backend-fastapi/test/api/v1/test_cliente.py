# ---------------------------------------------------------------------------
# ARQUIVO: test_cliente.py
# DESCRIÇÃO: Testes de integração para o domínio de Clientes.
# PADRÃO: Arrange (Preparar), Act (Agir), Assert (Validar).
# ---------------------------------------------------------------------------

import pytest
from fastapi.testclient import TestClient
from starlette import status

# --- Constantes de Teste ---
TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"
TEST_HWID = "test-terminal-hwid"

# =========================
# Fixtures (Preparação de Dados)
# =========================

@pytest.fixture(scope="function")
def header_with_token(client: TestClient, db_session, create_test_empresa) -> dict:
    """Autentica o usuário e retorna o header Authorization."""
    login_data = {"username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": TEST_HWID}
    response = client.post("/api/v1/auth/login", data=login_data)
    
    # Fail fast se o login não funcionar
    assert response.status_code == 200, "Falha ao logar no setup do teste"
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def valid_pf_payload():
    """Retorna um dicionário com dados válidos para criar um Cliente PF."""
    return {
        "nome": "João Pedro Silva",
        "cpf": "98765432101",
        "rg": "12345678",
        "genero": "MASCULINO",
        "data_nascimento": "1995-12-15",
        "email": "joao.silva@meu-pdv.com",
        "celular": "11987654321",
        "observacoes": "Cliente novo.",
        "tipo": "PF",
        "endereco": [
            {
                "logradouro": "Rua das Flores",
                "numero": "100",
                "bairro": "Centro",
                "cidade": "Campinas",
                "estado": "SP",
                "cep": "13010-000"
            }
        ]
    }

@pytest.fixture
def valid_pj_payload():
    """Retorna um dicionário com dados válidos para criar um Cliente PJ."""
    return {
        "razao_social": "Tech Solutions LTDA",
        "cnpj": "12345678000199",
        "nome_fantasia": "Tech Soluções",
        "ie": "123456789",
        "responsavel": "Ana Gerente",
        "email": "contato@tech.com",
        "telefone": "1155554444",
        "tipo": "PJ",
        "endereco": [
            {
                "logradouro": "Av. Empresarial",
                "numero": "200",
                "bairro": "Distrito Ind.",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "04000-000"
            }
        ]
    }

# =========================
# Testes: Criação (POST)
# =========================

def test_criar_cliente_pf_sucesso(client: TestClient, header_with_token, valid_pf_payload):
    """Testa a criação bem-sucedida de um cliente PF."""
    # Act
    response = client.post("/api/v1/clientes/cliente_pf", json=valid_pf_payload, headers=header_with_token)
    
    # Assert
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["nome"] == valid_pf_payload["nome"]
    assert data["cpf"] == valid_pf_payload["cpf"]
    assert data["id"] is not None
    assert data["ativo"] is True

def test_criar_cliente_pj_sucesso(client: TestClient, header_with_token, valid_pj_payload):
    """Testa a criação bem-sucedida de um cliente PJ."""
    # Act
    response = client.post("/api/v1/clientes/cliente_pj", json=valid_pj_payload, headers=header_with_token)
    
    # Assert
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["cnpj"] == valid_pj_payload["cnpj"]
    assert data["tipo"] == "PJ"

def test_erro_criar_cliente_duplicado(client: TestClient, header_with_token, valid_pf_payload):
    """Testa a regra de negócio que impede dois clientes com mesmo CPF."""
    # Arrange: Cria o primeiro cliente
    client.post("/api/v1/clientes/cliente_pf", json=valid_pf_payload, headers=header_with_token)
    
    # Act: Tenta criar o segundo cliente com os MESMOS dados
    response = client.post("/api/v1/clientes/cliente_pf", json=valid_pf_payload, headers=header_with_token)
    
    # Assert
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "já cadastrado" in response.json()["detail"][0]["mensagem"]

def test_erro_validacao_cpf_invalido(client: TestClient, header_with_token, valid_pf_payload):
    """Testa se o Pydantic bloqueia CPF com formato errado (menos digitos)."""
    # Arrange
    valid_pf_payload["cpf"] = "123" # CPF inválido
    
    # Act
    response = client.post("/api/v1/clientes/cliente_pf", json=valid_pf_payload, headers=header_with_token)
    
    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

# =========================
# Testes: Leitura/Busca (GET)
# =========================

def test_buscar_cliente_por_cpf(client: TestClient, header_with_token, valid_pf_payload):
    """Testa a busca polimórfica usando um CPF."""
    # Arrange
    client.post("/api/v1/clientes/cliente_pf", json=valid_pf_payload, headers=header_with_token)
    target_cpf = valid_pf_payload["cpf"]
    
    # Act
    response = client.get(f"/api/v1/clientes/?buscar={target_cpf}", headers=header_with_token)
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    results = response.json()["items"]
    assert len(results) == 1
    assert results[0]["cpf"] == target_cpf

def test_buscar_todos_clientes(client: TestClient, header_with_token, valid_pf_payload, valid_pj_payload):
    """Testa se a busca vazia retorna a lista completa."""
    # Arrange: Cria 1 PF e 1 PJ
    client.post("/api/v1/clientes/cliente_pf", json=valid_pf_payload, headers=header_with_token)
    client.post("/api/v1/clientes/cliente_pj", json=valid_pj_payload, headers=header_with_token)
    
    # Act
    response = client.get("/api/v1/clientes/", headers=header_with_token)
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    results = response.json()["items"]
    # Verifica se pelo menos os 2 criados retornaram (pode haver outros do setup do banco)
    assert len(results) >= 2 

# =========================
# Testes: Atualização (PUT)
# =========================

def test_atualizar_cliente_e_enderecos(client: TestClient, header_with_token, valid_pf_payload):
    """
    Testa atualização de dados cadastrais e manipulação complexa de endereços:
    1. Atualiza um endereço existente.
    2. Adiciona um novo endereço (sem ID).
    """
    # Arrange: Cria cliente
    res_create = client.post("/api/v1/clientes/cliente_pf", json=valid_pf_payload, headers=header_with_token)
    created_client = res_create.json()
    cliente_id = created_client["id"]
    endereco_id = created_client["endereco"][0]["id"]
    
    # Prepara payload de atualização
    update_payload = {
        "nome": "André",
        "tipo": "PF",
        "endereco": ...
    }
    
    # Modifica endereço existente e adiciona um novo
    update_payload["endereco"] = [
        {
            "id": endereco_id, # ID existente -> Update
            "logradouro": "Rua Editada",
            "numero": "999",
            "bairro": "Centro",
            "cidade": "Campinas",
            "estado": "SP",
            "cep": "13010-000"
        },
        {
            # Sem ID -> Create (Novo Endereço)
            "logradouro": "Rua Nova Adicionada",
            "numero": "10",
            "bairro": "Bairro Novo",
            "cidade": "Campinas",
            "estado": "SP",
            "cep": "13010-100"
        }
    ]

    # Act
    response = client.put(f"/api/v1/clientes/{cliente_id}", json=update_payload, headers=header_with_token)
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["nome"] == "André"
    assert len(data["endereco"]) == 2 # Deve ter 2 endereços agora
    
    # Verifica se um dos endereços é o editado
    addr_names = [end["logradouro"] for end in data["endereco"]]
    assert "Rua Editada" in addr_names
    assert "Rua Nova Adicionada" in addr_names

def test_erro_atualizar_cliente_inexistente(client: TestClient, header_with_token, valid_pf_payload):
    """Testa tentativa de update em ID que não existe (404)."""
    # Arrange
    valid_pf_payload["tipo"] = "PF"
    
    # Act
    response = client.put("/api/v1/clientes/99999", json=valid_pf_payload, headers=header_with_token)
    
    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND

# =========================
# Testes: Toggle Ativo/Inativo (Soft Delete)
# =========================

def test_toggle_status_cliente(client: TestClient, header_with_token, valid_pf_payload):
    """
    Testa o ciclo de vida lógico:
    Ativo -> Desativar -> Inativo -> Ativar -> Ativo
    """
    # Arrange: Cria cliente (nasce Ativo=True)
    res = client.post("/api/v1/clientes/cliente_pf", json=valid_pf_payload, headers=header_with_token)
    cliente_id = res.json()["id"]
    assert res.json()["ativo"] is True
    
    # Act 1: Desativar
    res_disable = client.put(f"/api/v1/clientes/toggle_ativo/{cliente_id}", headers=header_with_token)
    
    # Assert 1
    assert res_disable.status_code == status.HTTP_200_OK
    assert res_disable.json()["ativo"] is False
    
    # Verificação extra: Cliente desativado não deve aparecer na busca padrão com only_active=true
    res_search = client.get(f"/api/v1/clientes/?buscar={valid_pf_payload['cpf']}&only_active=true", headers=header_with_token)
    assert len(res_search.json()["items"]) == 0 # Não deve achar pois está inativo

    # Act 2: Reativar
    res_enable = client.put(f"/api/v1/clientes/toggle_ativo/{cliente_id}", headers=header_with_token)
    
    # Assert 2
    assert res_enable.status_code == status.HTTP_200_OK
    assert res_enable.json()["ativo"] is True