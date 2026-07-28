# ---------------------------------------------------------------------------
# ARQUIVO: test_fornecedor.py
# DESCRIÇÃO: Testes de integração para os endpoints CRUD de Fornecedores.
# ---------------------------------------------------------------------------

from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.db.models.fornecedor import Fornecedor as FornecedorModel # Adicionado import do modelo para fixtures

# --- Constantes de Teste ---
TEST_CNPJ = "72345734000132"
TEST_NOME = "Alan Amorim ME"
TEST_IE = "123456789012"
TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"
TEST_HWID = "test-terminal-hwid"

# =========================
# Fixture de Autenticação (Mantido)
# =========================
@pytest.fixture(scope="function")
def header_with_token(client: TestClient, db_session: Session, create_test_empresa) -> dict:
    # ... (lógica de login) ...
    login_data = {"username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": TEST_HWID}
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200 
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# =========================
# Fixture de Dados de Criação
# =========================
@pytest.fixture
def base_fornecedor_data():
    """Retorna o payload base para criação de fornecedor."""
    return {
        "nome": TEST_NOME,
        "cnpj": TEST_CNPJ,
        "nome_fantasia": "BigTech",
        "ie": TEST_IE,
        "telefone": "8535667788",
        "representante": "Mauro Filho",
    }

# =========================
# Testes de Criação (Caminhos Felizes e Tristes)
# =========================
def test_criar_fornecedor_caminho_feliz(client: TestClient, header_with_token: dict, base_fornecedor_data: dict):
    """
    Testa a criação bem-sucedida de um Fornecedor.
    """
    response = client.post("/api/v1/fornecedores/", json=base_fornecedor_data, headers=header_with_token)
    
    assert response.status_code == 201
    assert response.json()["nome"] == TEST_NOME
    assert response.json()["cnpj"] == TEST_CNPJ

def test_criar_fornecedor_com_cnpj_duplicado(client: TestClient, header_with_token: dict, base_fornecedor_data: dict):
    """
    Testa a falha ao tentar criar um fornecedor com CNPJ já existente (caminho triste 409).
    """
    # Arrange 1: Cria o primeiro fornecedor
    client.post("/api/v1/fornecedores/", json=base_fornecedor_data, headers=header_with_token)
    
    # Arrange 2: Novo fornecedor com o mesmo CNPJ, mas nome diferente
    data_supplier_duplicate = {**base_fornecedor_data, "nome": "Outro Nome"}

    # Act: Tenta criar o duplicado
    response = client.post("/api/v1/fornecedores/", json=data_supplier_duplicate, headers=header_with_token)
    
    # Assert: Deve falhar com 409 CONFLICT
    assert response.status_code == 409
    assert "cnpj" in response.json()["detail"][0]["campo"]

def test_criar_fornecedor_com_cnpj_desativado(client: TestClient, header_with_token: dict, db_session: Session, base_fornecedor_data: dict):
    """
    Testa a falha ao tentar criar um fornecedor com CNPJ que pertence a um registro inativo.
    A API deve retornar uma mensagem específica de reativação.
    """
    # Arrange 1: Insere o registro diretamente no banco como INATIVO
    fornecedor_inativo = FornecedorModel(
        nome="Inativo Corp", 
        cnpj=TEST_CNPJ, 
        nome_fantasia="Inativo",
        ativo=False # Chave de teste
    )
    db_session.add(fornecedor_inativo)
    db_session.commit()
    db_session.refresh(fornecedor_inativo)

    # Act: Tenta criar um novo fornecedor com o mesmo CNPJ
    response = client.post("/api/v1/fornecedores/", json=base_fornecedor_data, headers=header_with_token)

    # Assert: Deve falhar com 409 e mensagem de reativação
    assert response.status_code == 409
    assert "desabilitado com este CPF/CNPJ" in response.json()["detail"]


# ... (test_criar_fornecedor_sem_token - Mantido) ...
def test_criar_fornecedor_sem_token(client: TestClient):
    # ... (lógica) ...
    response = client.post("/api/v1/fornecedores/", json={
        "nome": "X",
        "cnpj": "12345678000100"
    })
    assert response.status_code == 401

# =========================
# Testes de Busca
# =========================
def test_buscar_fornecedor_por_cnpj_parcial(client: TestClient, header_with_token: dict, base_fornecedor_data: dict):
    """
    Testa a busca parcial (search) por CNPJ.
    """
    # Arrange: Cria o Fornecedor
    client.post("/api/v1/fornecedores/", json=base_fornecedor_data, headers=header_with_token)

    # Act: Busca usando apenas os primeiros 5 dígitos do CNPJ
    search_cnpj_parcial = TEST_CNPJ[:5] 
    search_response = client.get(f"/api/v1/fornecedores/?buscar={search_cnpj_parcial}", headers=header_with_token)
    
    # Assert
    assert search_response.status_code == 200
    search_data = search_response.json()
    assert len(search_data) == 1
    assert search_data[0]["nome"] == TEST_NOME

# =========================
# Testes de Edição (PUT/Update)
# =========================
def test_editar_fornecedor_caminho_feliz(client: TestClient, header_with_token: dict, base_fornecedor_data: dict):
    """
    Testa a edição de um fornecedor existente.
    """
    # Arrange 1: Cria o Fornecedor
    create_response = client.post("/api/v1/fornecedores/", json=base_fornecedor_data, headers=header_with_token)
    fornecedor_id = create_response.json()["id"]

    # Arrange 2: Payload para atualização (apenas o nome fantasia)
    update_payload = {"nome_fantasia": "BigTech Editada S/A"}

    # Act: Enviar a Requisição de Edição (PUT)
    update_response = client.put(f"/api/v1/fornecedores/{fornecedor_id}", json=update_payload, headers=header_with_token)
    
    # Assert
    assert update_response.status_code == 200
    assert update_response.json()["nome_fantasia"] == "BigTech Editada S/A"
    assert update_response.json()["nome"] == TEST_NOME # Nome original deve ser mantido

def test_editar_fornecedor_nao_encontrado(client: TestClient, header_with_token: dict):
    """
    Testa a falha ao tentar editar um fornecedor com ID inexistente.
    """
    inexistent_id = 99999
    update_payload = {"nome_fantasia": "Inexistente"}

    response = client.put(f"/api/v1/fornecedores/{inexistent_id}", json=update_payload, headers=header_with_token)
    
    assert response.status_code == 404
    assert "Fornecedor não encontrado" in response.json()["detail"]


# =========================
# Testes de Ativação/Desativação (Toggle Ativo)
# =========================
def test_toggle_status_desativar_e_ativar(client: TestClient, header_with_token: dict, base_fornecedor_data: dict):
    """
    Testa o ciclo completo de desativação (ativo=False) e reativação (ativo=True).
    """
    # 1. Arrange: Criar o Fornecedor (ativo=True)
    create_response = client.post("/api/v1/fornecedores/", json=base_fornecedor_data, headers=header_with_token)
    fornecedor_id = create_response.json()["id"]
    assert create_response.json()["ativo"] is True

    # 2. Act 1: Desativar (toggle ativo)
    disable_response = client.put(f"/api/v1/fornecedores/toggle_ativo/{fornecedor_id}", headers=header_with_token)
    
    # 3. Assert 1: Deve desativar
    assert disable_response.status_code == 200
    assert disable_response.json()["ativo"] is False

    # 4. Act 2: Ativar (toggle ativo novamente)
    enable_response = client.put(f"/api/v1/fornecedores/toggle_ativo/{fornecedor_id}", headers=header_with_token)

    # 5. Assert 2: Deve reativar
    assert enable_response.status_code == 200
    assert enable_response.json()["ativo"] is True

# O endpoint DELETE é um Update Lógico (toggle_ativo), então o teste DELETE original
# não é necessário. Se fosse implementado o DELETE Hard, o teste seria o seguinte:

# def test_delete_fornecedor_hard_delete(...) - Seria implementado se houvesse a rota DELETE /fornecedores/{id}