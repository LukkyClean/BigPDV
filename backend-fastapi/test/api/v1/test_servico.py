# ---------------------------------------------------------------------------
# ARQUIVO: test_servico.py
# DESCRIÇÃO: Testes de integração (API) para os endpoints de /servicos.
#            Cobre Create, Read, Update, Soft-Delete e validações de Erro.
# ---------------------------------------------------------------------------

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# =========================
# Configurações e Fixtures
# =========================

# Constantes para facilitar manutenção
TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"
TEST_HWID = "test-terminal-hwid"

@pytest.fixture(scope="function")
def header_with_token(client: TestClient, db_session: Session, create_test_empresa) -> dict:
    """Autentica um usuário e retorna o header Authorization."""
    login_data = {"username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": TEST_HWID}
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200 
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# =========================
# TESTES: CRIAÇÃO (CREATE)
# =========================

def test_criar_novo_servico_sucesso(client: TestClient, header_with_token: dict):
    """Happy Path: Testa a criação bem-sucedida de um novo serviço."""
    data_service = {
        "descricao": "Troca de tela do Iphone 16",
        "valor": 120000
    }

    response = client.post("/api/v1/servicos/", json=data_service, headers=header_with_token)
    
    assert response.status_code == 201
    assert response.json()["descricao"] == data_service["descricao"]
    assert response.json()["ativo"] is True

def test_erro_criar_servico_duplicado(client: TestClient, header_with_token: dict):
    """Sad Path: Tenta criar um serviço com descrição já existente (deve retornar 409)."""
    # 1. Cria o primeiro serviço
    data_service = {
        "descricao": "Limpeza de Hardware",
        "valor": 5000
    }
    client.post("/api/v1/servicos/", json=data_service, headers=header_with_token)

    # 2. Tenta criar o segundo com a MESMA descrição
    response_duplicate = client.post("/api/v1/servicos/", json=data_service, headers=header_with_token)

    assert response_duplicate.status_code == 409
    assert response_duplicate.json()["detail"] == "Serviço já cadastrado no sistema"

# =========================
# TESTES: LEITURA (READ)
# =========================

def test_buscar_servico_por_termo(client: TestClient, header_with_token: dict):
    """Happy Path: Busca serviço por termo específico."""
    # Arrange
    data_service = {"descricao": "Manutenção GPU", "valor": 75000}
    client.post("/api/v1/servicos/", json=data_service, headers=header_with_token)

    # Act
    search = "Manutenção"
    response = client.get(f"/api/v1/servicos/?search={search}", headers=header_with_token)
    
    # Assert
    assert response.status_code == 200
    results = response.json()["items"]
    assert len(results) >= 1
    assert any(s["descricao"] == "Manutenção GPU" for s in results)

def test_listar_todos_ativos(client: TestClient, header_with_token: dict):
    """Happy Path: Busca sem termo deve retornar todos os ativos."""
    client.post("/api/v1/servicos/", json={"descricao": "Serviço A", "valor": 10}, headers=header_with_token)
    
    response = client.get("/api/v1/servicos/", headers=header_with_token)
    assert response.status_code == 200
    assert isinstance(response.json()["items"], list)

# =========================
# TESTES: EDIÇÃO (UPDATE)
# =========================

def test_editar_servico_sucesso(client: TestClient, header_with_token: dict):
    """Happy Path: Atualiza valor e descrição de um serviço existente."""
    # Arrange
    create_resp = client.post("/api/v1/servicos/", json={"descricao": "Formatacao", "valor": 50}, headers=header_with_token)
    service_id = create_resp.json()["id"]

    # Act
    update_data = {"descricao": "Formatação Completa", "valor": 80}
    response = client.put(f"/api/v1/servicos/{service_id}", json=update_data, headers=header_with_token)
    
    # Assert
    assert response.status_code == 200
    assert response.json()["descricao"] == "Formatação Completa"
    assert response.json()["valor"] == 80

def test_erro_editar_servico_conflito(client: TestClient, header_with_token: dict):
    """Sad Path: Tenta renomear um serviço para um nome que já existe em OUTRO serviço."""
    # Arrange: Cria Serviço A e Serviço B
    client.post("/api/v1/servicos/", json={"descricao": "Serviço A", "valor": 10}, headers=header_with_token)
    resp_b = client.post("/api/v1/servicos/", json={"descricao": "Serviço B", "valor": 20}, headers=header_with_token)
    id_b = resp_b.json()["id"]

    # Act: Tenta atualizar B para ter o nome de A
    update_data = {"descricao": "Serviço A"} # Conflito!
    response = client.put(f"/api/v1/servicos/{id_b}", json=update_data, headers=header_with_token)

    # Assert
    assert response.status_code == 409
    assert response.json()["detail"] == "Serviço já cadastrado no sistema"

def test_erro_editar_servico_inexistente(client: TestClient, header_with_token: dict):
    """Sad Path: Tenta editar um ID que não existe."""
    response = client.put("/api/v1/servicos/99999", json={"valor": 100}, headers=header_with_token)
    assert response.status_code == 404
    assert response.json()["detail"] == "Serviço não encontrado no sistema"

# =========================
# TESTES: DESATIVAR (TOGGLE/DELETE)
# =========================

def test_desativar_servico(client: TestClient, header_with_token: dict):
    """
    Testa o Soft Delete (Toggle).
    Ao deletar, o serviço não deve ser destruído do banco, mas sim ter 'ativo' setado para False.
    """
    # Arrange
    create_resp = client.post("/api/v1/servicos/", json={"descricao": "Serviço Temporário", "valor": 100}, headers=header_with_token)
    service_id = create_resp.json()["id"]

    # Act 1: Desativar (DELETE)
    # Nota: Dependendo da sua controller, pode retornar 200 (objeto atualizado) ou 204 (no content)
    # Assumindo comportamento padrão de toggle que retorna o objeto:
    delete_response = client.put(f"/api/v1/servicos/toggle_ativo/{service_id}", headers=header_with_token)
    
    # Verificação Flexível (200 ou 204)
    assert delete_response.status_code in [200, 204]
    
    # Se retornar o objeto, verifica se ativo == False
    if delete_response.status_code == 200:
        assert delete_response.json()["ativo"] is False

    # Act 2: Tentar buscar na lista padrão (que filtra apenas ativos) com active=true
    # O serviço NÃO deve aparecer aqui
    search_response = client.get("/api/v1/servicos/?search=Serviço Temporário&active=true", headers=header_with_token)
    results = search_response.json()["items"]
    
    # Assert: A lista deve estar vazia pois o item está inativo
    assert len(results) == 0

def test_erro_desativar_servico_inexistente(client: TestClient, header_with_token: dict):
    """Sad Path: Tenta desativar um ID que não existe."""
    response = client.put("/api/v1/servicos/toggle_ativo/99999", headers=header_with_token)
    assert response.status_code == 404