# ---------------------------------------------------------------------------
# ARQUIVO: test_funcionario.py
# DESCRIÇÃO: Suite de testes completa (Full Coverage) para Funcionários.
# COBERTURA: Sucesso, Validação, Conflitos, Not Found, Ciclo de Vida e Integração.
# ---------------------------------------------------------------------------

import pytest
import random
import string
from fastapi.testclient import TestClient
from starlette import status

# --- Constantes de Rotas ---
PREFIX = "/api/v1/funcionarios"
AUTH_PREFIX = "/api/v1/auth"
CARGO_PREFIX = "/api/v1/cargos"

# Dados fixos para autenticação (Setup inicial)
TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"
TEST_HWID = "test-terminal-hwid"

# ===========================================================================
# 1. FIXTURES (PREPARAÇÃO DE AMBIENTE)
# ===========================================================================

@pytest.fixture(scope="function")
def header_with_token(client: TestClient, db_session, create_test_empresa) -> dict:
    """Autentica o usuário admin e retorna o header Authorization."""
    login_data = {"username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": TEST_HWID}
    response = client.post(f"{AUTH_PREFIX}/login", data=login_data)
    assert response.status_code == 200, "Falha crítica: Login de setup falhou"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="function")
def cargo_id(client: TestClient, header_with_token: dict) -> int:
    """Cria um cargo auxiliar para testes de vínculo."""
    cargo_data = {
        "nome": f"Cargo QA {random.randint(1000, 9999)}",
        "permissioes": {"funcionario": True}
    }
    response = client.post(f"{CARGO_PREFIX}/", json=cargo_data, headers=header_with_token)
    return response.json()["id"]

@pytest.fixture(scope="function")
def funcionario_payload():
    """
    Factory que gera um payload com TODOS os campos únicos gerados aleatoriamente.
    Garante isolamento total entre os testes.
    """
    def _generate():
        suffix = random.randint(10000, 99999)
        # Gera documentos válidos em formato (mock simples de string numérica)
        cpf_mock = "".join(random.choices(string.digits, k=11))
        rg_mock = "".join(random.choices(string.digits, k=9))
        cnh_mock = "".join(random.choices(string.digits, k=10))
        ctps_mock = "".join(random.choices(string.digits, k=8))
        
        return {
            "nome": f"Funcionario Full {suffix}",
            "cpf": cpf_mock,
            "rg": rg_mock,
            "cnh": cnh_mock,
            "carteira_trabalho": ctps_mock,
            "email": f"func.{suffix}@empresa.com",
            "contato": "11999999999",
            "mae": "Mãe Teste",
            "pai": "Pai Teste",
            "banco": "Banco X",
            "agencia": "0001",
            "conta": "12345-6",
            "usuario": {
                "nome": f"user.{suffix}",
                "email": f"func.{suffix}@empresa.com", # Email deve bater com o do func para consistência
                "senha": "SenhaForte123!"
            },
            "endereco": [
                {
                    "logradouro": "Rua Teste Unitario",
                    "numero": "123",
                    "cep": "12345-678",
                    "bairro": "Centro",
                    "cidade": "Lab City",
                    "estado": "SP"
                }
            ]
        }
    return _generate

# ===========================================================================
# 2. CASOS DE SUCESSO (HAPPY PATH)
# ===========================================================================

def test_criar_funcionario_completo(client: TestClient, header_with_token, funcionario_payload):
    """Verifica a criação de toda a árvore de dados (Funcionario -> Usuario -> Endereco)."""
    payload = funcionario_payload()
    response = client.post(f"{PREFIX}/", json=payload, headers=header_with_token)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["nome"] == payload["nome"]
    assert data["usuario"]["email"] == payload["usuario"]["email"]
    assert len(data["endereco"]) == 1
    assert data["ativo"] is True

def test_buscar_funcionarios_com_filtro(client: TestClient, header_with_token, funcionario_payload):
    """Verifica a busca filtrada por CPF."""
    payload = funcionario_payload()
    client.post(f"{PREFIX}/", json=payload, headers=header_with_token)
    
    # Busca pelo CPF exato
    response = client.get(f"{PREFIX}/?buscar={payload['cpf']}", headers=header_with_token)
    
    assert response.status_code == status.HTTP_200_OK
    results = response.json()
    assert len(results) == 1
    assert results[0]["cpf"] == payload["cpf"]

def test_atualizar_dados_e_enderecos(client: TestClient, header_with_token, funcionario_payload):
    """Testa atualização de campos simples e lista de endereços."""
    # 1. Cria
    payload = funcionario_payload()
    res_create = client.post(f"{PREFIX}/", json=payload, headers=header_with_token)
    func_id = res_create.json()["id"]
    
    # 2. Atualiza (Muda nome e Adiciona Endereço)
    update_data = {
        "nome": "Nome Atualizado",
        "endereco": [
            {"logradouro": "Novo Endereço", "numero": "100", "bairro": "veneza", "cep": "00000000", "cidade": "X", "estado": "CE"}
        ]
    }
    res_update = client.put(f"{PREFIX}/{func_id}", json=update_data, headers=header_with_token)
    
    assert res_update.status_code == status.HTTP_200_OK
    data = res_update.json()
    assert data["nome"] == "Nome Atualizado"
    # O sistema deve ter substituído ou adicionado (depende da lógica do service de endereço), 
    # mas garantimos que o novo existe.
    logradouros = [e["logradouro"] for e in data["endereco"]]
    assert "Novo Endereço" in logradouros

# ===========================================================================
# 3. CASOS DE ERRO DE VALIDAÇÃO (PYDANTIC 422)
# ===========================================================================

def test_erro_cpf_invalido_formato(client: TestClient, header_with_token, funcionario_payload):
    """Testa se o Regex do CPF no Schema funciona."""
    payload = funcionario_payload()
    payload["cpf"] = "123" # CPF inválido (poucos dígitos)
    
    response = client.post(f"{PREFIX}/", json=payload, headers=header_with_token)
    
    # 422 Unprocessable Entity (Falha na validação do Pydantic)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_erro_campos_obrigatorios_faltando(client: TestClient, header_with_token):
    """Testa envio de JSON incompleto."""
    payload = {"nome": "Incompleto"} # Falta CPF, Usuario, etc.
    response = client.post(f"{PREFIX}/", json=payload, headers=header_with_token)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

# ===========================================================================
# 4. CASOS DE ERRO DE NEGÓCIO (CONFLITOS 409)
# ===========================================================================

@pytest.mark.parametrize("campo_duplicado", ["cpf", "email", "rg", "cnh", "carteira_trabalho"])
def test_erro_documentos_duplicados(client: TestClient, header_with_token, funcionario_payload, campo_duplicado):
    """
    Testa TODOS os campos únicos definidos no Service.
    Usa parametrize para rodar o teste 5 vezes, uma para cada campo.
    """
    # 1. Cria o primeiro funcionário (dono dos dados)
    payload_original = funcionario_payload()
    client.post(f"{PREFIX}/", json=payload_original, headers=header_with_token)
    
    # 2. Prepara o segundo funcionário (diferente), mas copia UM campo sensível
    payload_duplicado = funcionario_payload() # Gera dados novos
    
    # Força a duplicidade apenas do campo testado
    # Obs: Para 'email', precisamos ajustar tanto no func quanto no usuario
    if campo_duplicado == "email":
        payload_duplicado["email"] = payload_original["email"]
        payload_duplicado["usuario"]["email"] = payload_original["email"] # Usuario tbm valida
    else:
        payload_duplicado[campo_duplicado] = payload_original[campo_duplicado]
    
    # 3. Tenta criar
    response = client.post(f"{PREFIX}/", json=payload_duplicado, headers=header_with_token)
    
    # 4. Assert
    assert response.status_code == status.HTTP_409_CONFLICT
    error_detail = response.json()["detail"]
    
    # O service retorna lista de erros ou string, dependendo da implementação.
    # Verificamos se a mensagem menciona conflito.
    if isinstance(error_detail, list):
        assert "já cadastrado" in error_detail[0]["mensagem"]
    else:
        assert "já cadastrado" in str(error_detail)

def test_erro_reativar_funcionario_desabilitado_duplicado(client: TestClient, header_with_token, funcionario_payload):
    """
    Testa a lógica específica: 'funcionario desabilitado com este CPF'.
    O sistema não deve deixar criar novo, deve pedir para reativar o antigo.
    """
    # 1. Cria e Desativa
    payload = funcionario_payload()
    res = client.post(f"{PREFIX}/", json=payload, headers=header_with_token)
    func_id = res.json()["id"]
    client.put(f"{PREFIX}/toggle_ativo/{func_id}", headers=header_with_token)
    
    # 2. Tenta criar NOVO com mesmos dados
    response = client.post(f"{PREFIX}/", json=payload, headers=header_with_token)
    
    # 3. Valida a mensagem específica de erro
    assert response.status_code == status.HTTP_409_CONFLICT
    # Verifica se a mensagem de erro contém a instrução de reativação
    detail = response.json()["detail"]
    if isinstance(detail, list): # Se for lista de erros
         assert "reative o cadastro" in detail[0]["mensagem"] or "desabilitado" in detail[0]["mensagem"]
    else:
         assert "reative o cadastro" in str(detail) or "desabilitado" in str(detail)

# ===========================================================================
# 5. CASOS DE ERRO DE RECURSO NÃO ENCONTRADO (404)
# ===========================================================================

def test_erro_atualizar_id_inexistente(client: TestClient, header_with_token):
    update_data = {"nome": "Fantasma"}
    response = client.put(f"{PREFIX}/999999", json=update_data, headers=header_with_token)
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_erro_toggle_id_inexistente(client: TestClient, header_with_token):
    response = client.put(f"{PREFIX}/toggle_ativo/999999", headers=header_with_token)
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_erro_cargo_funcionario_inexistente(client: TestClient, header_with_token):
    response = client.put(f"{PREFIX}/999999/cargo?cargo_id=1", headers=header_with_token)
    assert response.status_code == status.HTTP_404_NOT_FOUND

# ===========================================================================
# 6. CASOS DE CICLO DE VIDA E INTEGRAÇÃO (LÓGICA COMPLEXA)
# ===========================================================================

def test_vincular_cargo_sucesso(client: TestClient, header_with_token, funcionario_payload, cargo_id):
    """Testa o endpoint específico de vínculo de cargo."""
    # 1. Cria Funcionario
    payload = funcionario_payload()
    res = client.post(f"{PREFIX}/", json=payload, headers=header_with_token)
    func_id = res.json()["id"]
    
    # 2. Vincula Cargo
    response = client.put(f"{PREFIX}/{func_id}/cargo?cargo_id={cargo_id}", headers=header_with_token)
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["cargo_id"] == cargo_id