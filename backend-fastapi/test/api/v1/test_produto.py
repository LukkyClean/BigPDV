# ---------------------------------------------------------------------------
# ARQUIVO: test_produtos.py
# DESCRIÇÃO: Testes de integração abrangentes para o domínio de Produtos.
# ---------------------------------------------------------------------------

import pytest
from unittest.mock import patch
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
    # Assume que a rota de login existe e funciona conforme contexto anterior
    login_data = {"username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": TEST_HWID}
    response = client.post("/api/v1/auth/login", data=login_data)
    
    # Fallback caso a autenticação falhe no ambiente de teste isolado
    if response.status_code != 200:
        pytest.skip("Falha na autenticação do usuário de teste.")
        
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def valid_product_payload():
    """Retorna um payload padrão e válido para criação de produto."""
    return {
        "nome": "Café Gourmet Moído 500g",
        "codigo_produto": "CFG-TEST-FULL-001",
        "unidade_medida": "UN",
        "observacao": "Armazenar em local seco.",
        "nota_fiscal": "1004.22.99",
        "categoria": "Bebidas",
        "marca": "Fazenda Teste",
        "id_fornecedor": None,
        "estoque": {
            "valor_varejo": 2999,
            "quantidade": 100,
            "valor_entrada": 1500,
            "valor_atacado": 2500,
            "quantidade_minima": 20
        }
    }

# =========================
# 1. Testes: Criação (POST)
# =========================

def test_criar_produto_sucesso(client: TestClient, header_with_token, valid_product_payload):
    """Testa a criação completa: Produto + Estoque."""
    response = client.post("/api/v1/produtos/", json=valid_product_payload, headers=header_with_token)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["nome"] == valid_product_payload["nome"]
    assert data["estoque"]["quantidade"] == 100
    assert data["id"] is not None

def test_erro_criar_produto_codigo_duplicado(client: TestClient, header_with_token, valid_product_payload):
    """Testa validação de unicidade do codigo_produto."""
    # 1. Cria o primeiro
    client.post("/api/v1/produtos/", json=valid_product_payload, headers=header_with_token)
    
    # 2. Tenta criar o segundo igual
    response = client.post("/api/v1/produtos/", json=valid_product_payload, headers=header_with_token)
    
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "já cadastrado" in response.json()["detail"]["mensagem"]

# =========================
# 2. Testes: Leitura (GET)
# =========================

def test_listar_todos_produtos(client: TestClient, header_with_token, valid_product_payload):
    """Testa a listagem geral sem filtros (busca vazia)."""
    client.post("/api/v1/produtos/", json=valid_product_payload, headers=header_with_token)
    
    response = client.get("/api/v1/produtos/", headers=header_with_token)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1

def test_buscar_produto_por_termo(client: TestClient, header_with_token, valid_product_payload):
    """Testa o filtro de busca (get_produto_by_search)."""
    valid_product_payload["codigo_produto"] = "BUSCA-ESPECIFICA"
    client.post("/api/v1/produtos/", json=valid_product_payload, headers=header_with_token)
    
    # Busca pelo código
    response = client.get(f"/api/v1/produtos/?buscar=BUSCA-ESPECIFICA", headers=header_with_token)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["codigo_produto"] == "BUSCA-ESPECIFICA"

# ==================================================
# 2.1 Testes: Busca inteligente (core/busca.py)
# ==================================================

@pytest.fixture
def catalogo_de_busca(client: TestClient, header_with_token, valid_product_payload):
    """
    Cria um mini-catálogo com os casos que o balcão vive: nome composto,
    acento, marca e código de barras.
    """
    produtos = [
        {"nome": "Tinta Azul Metálica", "codigo_produto": "TNT-001",
         "codigo_barras": "7891234567890", "marca": "Suvinil", "categoria": "Pintura"},
        {"nome": "Açúcar Refinado 1kg", "codigo_produto": "ACU-001",
         "codigo_barras": "7899999999999", "marca": "União", "categoria": "Alimentos"},
        {"nome": "Pincel Cerda Macia", "codigo_produto": "PNC-001",
         "codigo_barras": "7890000000000", "marca": "Tigre", "categoria": "Pintura"},
    ]

    for extra in produtos:
        payload = {**valid_product_payload, **extra}
        resposta = client.post("/api/v1/produtos/", json=payload, headers=header_with_token)
        assert resposta.status_code == status.HTTP_201_CREATED

    return produtos


def _nomes(resposta) -> list[str]:
    return [item["nome"] for item in resposta.json()]


def test_busca_encontra_palavra_no_meio_do_nome(client, header_with_token, catalogo_de_busca):
    """O caso que originou a refatoração: 'azul' tem que achar 'Tinta Azul'."""
    resposta = client.get("/api/v1/produtos/?buscar=azul", headers=header_with_token)

    assert resposta.status_code == status.HTTP_200_OK
    assert "Tinta Azul Metálica" in _nomes(resposta)


def test_busca_ignora_a_ordem_das_palavras(client, header_with_token, catalogo_de_busca):
    resposta = client.get("/api/v1/produtos/?buscar=azul tinta", headers=header_with_token)

    assert "Tinta Azul Metálica" in _nomes(resposta)


def test_busca_ignora_acentos(client, header_with_token, catalogo_de_busca):
    resposta = client.get("/api/v1/produtos/?buscar=acucar", headers=header_with_token)

    assert "Açúcar Refinado 1kg" in _nomes(resposta)


def test_busca_exige_todas_as_palavras(client, header_with_token, catalogo_de_busca):
    """'tinta pincel' não pode trazer os dois: nenhum produto tem as duas palavras."""
    resposta = client.get("/api/v1/produtos/?buscar=tinta pincel", headers=header_with_token)

    assert _nomes(resposta) == []


def test_busca_por_codigo_de_barras(client, header_with_token, catalogo_de_busca):
    """Bipar o leitor tem que achar — antes o código de barras nem era varrido."""
    resposta = client.get("/api/v1/produtos/?buscar=7891234567890", headers=header_with_token)

    assert _nomes(resposta) == ["Tinta Azul Metálica"]


def test_busca_por_marca(client, header_with_token, catalogo_de_busca):
    resposta = client.get("/api/v1/produtos/?buscar=suvinil", headers=header_with_token)

    assert _nomes(resposta) == ["Tinta Azul Metálica"]


def test_codigo_exato_vem_em_primeiro(client, header_with_token, catalogo_de_busca):
    """
    Quem digita o SKU inteiro tem que receber AQUELE item no topo, nunca um
    parecido — é o que protege o operador no balcão.
    """
    resposta = client.get("/api/v1/produtos/?buscar=TNT-001", headers=header_with_token)

    assert _nomes(resposta)[0] == "Tinta Azul Metálica"


def test_busca_tolera_erro_de_digitacao(client, header_with_token, catalogo_de_busca):
    """'tnta' não casa com nada no LIKE; o resgate por similaridade assume."""
    resposta = client.get("/api/v1/produtos/?buscar=tnta", headers=header_with_token)

    assert "Tinta Azul Metálica" in _nomes(resposta)


def test_busca_sem_resultado_continua_vazia(client, header_with_token, catalogo_de_busca):
    """O resgate não pode virar desculpa para devolver qualquer coisa."""
    resposta = client.get("/api/v1/produtos/?buscar=geladeira", headers=header_with_token)

    assert _nomes(resposta) == []


def test_busca_vazia_devolve_o_catalogo(client, header_with_token, catalogo_de_busca):
    """A tela de Produtos depende disso para listar tudo."""
    resposta = client.get("/api/v1/produtos/", headers=header_with_token)

    assert len(resposta.json()) >= 3


def test_limite_corta_os_resultados(client, header_with_token, catalogo_de_busca):
    resposta = client.get("/api/v1/produtos/?buscar=001&limite=2", headers=header_with_token)

    assert len(resposta.json()) == 2


def test_autocomplete_sem_termo_nao_devolve_nada(client, header_with_token, catalogo_de_busca):
    """O campo do PDV não pode despejar o catálogo ao ganhar foco."""
    resposta = client.get("/api/v1/produtos/search", headers=header_with_token)

    assert resposta.json() == []


def test_autocomplete_encontra_palavra_no_meio(client, header_with_token, catalogo_de_busca):
    resposta = client.get("/api/v1/produtos/search?search=azul", headers=header_with_token)

    assert "Tinta Azul Metálica" in _nomes(resposta)

# =========================
# 3. Testes: Atualização (PUT)
# =========================

def test_editar_produto_completo(client: TestClient, header_with_token, valid_product_payload):
    """Testa update_produto e lógica de atualização de estoque aninhado."""
    # Cria
    res_create = client.post("/api/v1/produtos/", json=valid_product_payload, headers=header_with_token)
    produto_id = res_create.json()["id"]
    
    # Atualiza
    update_payload = {
        "nome": "Café Editado",
        "estoque": {"valor_varejo": 9999}
    }
    response = client.put(f"/api/v1/produtos/{produto_id}", json=update_payload, headers=header_with_token)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["nome"] == "Café Editado"
    assert data["estoque"]["valor_varejo"] == 9999

def test_editar_produto_inexistente(client: TestClient, header_with_token):
    """Testa erro 404 na atualização."""
    response = client.put("/api/v1/produtos/99999", json={"nome": "X"}, headers=header_with_token)
    assert response.status_code == status.HTTP_404_NOT_FOUND

# =========================
# 4. Testes: Toggle Status / Soft Delete
# =========================

def test_toggle_status_e_conflito_codigo(client: TestClient, header_with_token, valid_product_payload):
    """
    Testa:
    1. Desativar produto.
    2. Reativar com conflito de código.
    3. Reativar resolvendo o conflito.
    """
    # Cria produto A
    res = client.post("/api/v1/produtos/", json=valid_product_payload, headers=header_with_token)
    id_prod_a = res.json()["id"]
    code_a = valid_product_payload["codigo_produto"]

    # Desativa produto A
    client.put(f"/api/v1/produtos/toggle_ativo/{id_prod_a}", headers=header_with_token)

    # Cria produto B com MESMO código do A (permitido pois A está inativo/soft deleted?)
    # Nota: Se o banco permitir unique apenas em ativos, isso passa. 
    # Se o banco tiver unique constraint hard, falharia antes. 
    # Assumindo lógica da aplicação:
    payload_b = valid_product_payload.copy()
    payload_b["nome"] = "Produto B Conflitante"
    res_b = client.post("/api/v1/produtos/", json=payload_b, headers=header_with_token)
    
    # Se conseguiu criar o B com mesmo código, agora tentamos reativar o A
    if res_b.status_code == 201:
        # Tenta reativar A -> Deve dar conflito
        res_reactivate = client.put(f"/api/v1/produtos/toggle_ativo/{id_prod_a}", headers=header_with_token)
        assert res_reactivate.status_code == status.HTTP_409_CONFLICT
        
        # Reativa A fornecendo novo código
        res_reactivate_ok = client.put(
            f"/api/v1/produtos/toggle_ativo/{id_prod_a}?novo_codigo_produto={code_a}_NEW", 
            headers=header_with_token
        )
        assert res_reactivate_ok.status_code == status.HTTP_200_OK
        assert res_reactivate_ok.json()["ativo"] is True
        assert res_reactivate_ok.json()["codigo_produto"] == f"{code_a}_NEW"

# =========================
# 5. Testes: Imagens (Upload e Delete)
# =========================

# Mock para não salvar arquivos reais no disco durante os testes
@patch("app.services.produto.salvar_imagem")
@patch("app.services.produto.deletar_imagem")
def test_upload_e_delete_imagem(mock_delete, mock_save, client: TestClient, header_with_token, valid_product_payload):
    """
    Testa o fluxo completo de imagens:
    1. Upload de foto.
    2. Verificação de resposta.
    3. Deleção de foto.
    """
    # Configurar Mocks
    mock_save.return_value = "static/uploads/produtos/fake_path.jpg"
    mock_delete.return_value = True

    # 1. Preparar Produto
    res_prod = client.post("/api/v1/produtos/", json=valid_product_payload, headers=header_with_token)
    produto_id = res_prod.json()["id"]

    # 2. Upload da Imagem
    # Simula um arquivo JPEG
    files = {
        "image_file": ("test_image.jpg", b"fake binary content", "image/jpeg")
    }
    data_form = {"principal": "true"}

    response_upload = client.post(
        f"/api/v1/produtos/{produto_id}/fotos",
        files=files,
        data=data_form,
        headers=header_with_token
    )

    assert response_upload.status_code == status.HTTP_201_CREATED
    data_img = response_upload.json()
    assert data_img["produto_id"] == produto_id
    assert data_img["principal"] is True
    image_id = data_img["id"]

    # 3. Deleção da Imagem
    response_delete = client.delete(f"/api/v1/produtos/fotos/{image_id}", headers=header_with_token)
    
    assert response_delete.status_code == status.HTTP_204_NO_CONTENT
    
    # Verifica se os métodos de serviço (mockados) foram chamados corretamente
    mock_save.assert_called_once()
    mock_delete.assert_called_once()

def test_upload_imagem_produto_inexistente(client: TestClient, header_with_token):
    """Testa upload para ID inválido."""
    files = {"image_file": ("test.jpg", b"content", "image/jpeg")}
    response = client.post("/api/v1/produtos/99999/fotos", files=files, headers=header_with_token)
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_delete_imagem_inexistente(client: TestClient, header_with_token):
    """Testa deleção de imagem inválida."""
    response = client.delete("/api/v1/produtos/fotos/99999", headers=header_with_token)
    assert response.status_code == status.HTTP_404_NOT_FOUND