import io
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.db.models.empresa import Empresa
from app.db.models.usuario import Usuario

FILE_CONTENT_MOCK = b"GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"

TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"
TEST_HWID = "test-terminal-hwid"

# ===================================================================
# FIXTURES E DADOS AUXILIARES
# ===================================================================

@pytest.fixture(scope="function")
def header_with_token(client: TestClient, db_session, create_test_empresa) -> dict:
    """Autentica o usuário e retorna o header Authorization."""
    login_data = {"username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": TEST_HWID}
    response = client.post("/api/v1/auth/login", data=login_data)
    
    # Fail fast se o login não funcionar
    assert response.status_code == 200, "Falha ao logar no setup do teste"
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def get_empresa_payload_valido(cnpj_suffix="000199", email_prefix="admin"):
    """
    Gera um payload válido combinando dados da Empresa e do Usuário Master.
    Permite sufixos para criar dados únicos nos testes.
    """
    return {
        # --- Dados da Empresa (EmpresaCreate) ---
        "razao_social": f"Empresa Teste {cnpj_suffix} LTDA",
        "nome_fantasia": "Tech Teste",
        "is_cnpj": True,
        "documento": f"12345678{cnpj_suffix}", # Deve ter 14 dígitos (Regex)
        "regime_tributario": "Simples Nacional",
        "celular": "11999998888",
        # --- Endereço Inicial (Opcional) ---
        "endereco": [
            {
                "logradouro": "Av. Paulista",
                "numero": "1000",
                "bairro": "Bela Vista",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "01310-100"
            }
        ]
    }

def get_usuario_payload_valido():
    return {
        "nome": "Admin Master",
        "email": TEST_USER_EMAIL,
        "senha": TEST_USER_PASSWORD
    }

def create_test_empresa(client: TestClient):
    usuario_payload = get_usuario_payload_valido()
    empresa_payload = get_empresa_payload_valido()
    
    request_usuario_url = "/api/v1/usuarios/"
    request_empresa_url = "/api/v1/empresas/"

    usuario_response = client.post(
        request_usuario_url,
        json=usuario_payload
    )

    login_data = {"username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": TEST_HWID}
    response = client.post("/api/v1/auth/login", data=login_data)
    
    token = response.json()["access_token"]

    header_with_token = {"Authorization": f"Bearer {token}"}

    empresa_response = client.post(
        request_empresa_url,
        json=empresa_payload,
        headers=header_with_token
    )

    assert empresa_response.status_code == 201

    return empresa_response.json()["id"]

def test_criar_empresa_com_usuario_master_sucesso(client: TestClient, db_session: Session):
    """
    Testa o fluxo principal: Criar empresa, criar usuário master e vincular tudo.
    """
    usuario_payload = get_usuario_payload_valido()
    empresa_payload = get_empresa_payload_valido()
    
    request_usuario_url = "/api/v1/usuarios/"
    request_empresa_url = "/api/v1/empresas/"

    usuario_response = client.post(
        request_usuario_url,
        json=usuario_payload
    )

    login_data = {"username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": TEST_HWID}
    response = client.post("/api/v1/auth/login", data=login_data)
    
    token = response.json()["access_token"]

    header_with_token = {"Authorization": f"Bearer {token}"}

    empresa_response = client.post(
        request_empresa_url,
        json=empresa_payload,
        headers=header_with_token
    )

    assert empresa_response.status_code == 201

    data = empresa_response.json()
    
    # 3. Verifica retorno da API
    assert "id" in data
    assert data["documento"] == empresa_payload["documento"]
    assert data["ativo"] is True

    # 4. Verificação profunda no Banco de Dados (Garante a integridade)
    empresa_db = db_session.query(Empresa).filter(Empresa.documento == empresa_payload["documento"]).first()
    assert empresa_db is not None

def test_adiconar_imagem_a_uma_empresa_existente(client: TestClient, db_session: Session, header_with_token):
    
    file_mock = io.BytesIO(FILE_CONTENT_MOCK)
    file_payload = {
        "file": ("foto_test_principal.png", file_mock, "image/png")
    }

    request_url = f"/api/v1/empresas/imagem/"

    response = client.post(
        request_url,
        files=file_payload,
        headers=header_with_token
    )

    assert response.status_code == status.HTTP_201_CREATED


