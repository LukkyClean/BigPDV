# Arquivo de configuração para testes

import pytest # type: ignore
from fastapi.testclient import TestClient # type: ignore
from sqlalchemy import create_engine # type: ignore
from sqlalchemy.orm import sessionmaker # type: ignore
from sqlalchemy.pool import StaticPool # type: ignore

from app.main import app
from app.db.session import get_db
from app.db.base import Base

from app.db.models.usuario import Usuario

# Configuração do banco de dados de teste (SQLite em memória)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"
TEST_HWID = "test-terminal-hwid"

# Criando a engine de teste
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Criando a sessão de teste
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# get_db override para usar o banco de dados de teste
def get_db_override():
    db = TestingSessionLocal()
    try: 
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = get_db_override

# Fixture para o cliente de teste
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# Fixture para o banco de dados de teste
@pytest.fixture(scope="function")
def db_session():
    # Criar todas as tabelas
    Base.metadata.create_all(bind=engine)
    # Criar e fechar sessão após o teste
    session = TestingSessionLocal()
    yield session
    session.close()
    # Dropar todas as tabelas
    Base.metadata.drop_all(bind=engine)

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

@pytest.fixture(scope="function")
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
