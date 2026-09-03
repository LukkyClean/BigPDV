# ---------------------------------------------------------------------------
# ARQUIVO: test/api/v1/test_venda_correcao_fiscal.py
# DESCRIÇÃO: Testes automatizados para a rota de correção cadastral/fiscal de vendas,
#            garantindo a atualização de vendas finalizadas, a invariância de estoque
#            e lançamentos financeiros, e o enriquecimento de dados no Centro Fiscal.
# ---------------------------------------------------------------------------

import pytest
from fastapi.testclient import TestClient
from app.db.models.contador_venda import ContadorVenda
from app.db.models.documento_fiscal import DocumentoFiscal
from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings
from app.db.models.produto import Produto

TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"
TEST_HWID = "test-terminal-hwid"


@pytest.fixture(scope="function")
def header_with_token(client: TestClient, db_session, create_test_empresa) -> dict:
    """Autentica o usuário e retorna o header Authorization."""
    login_data = {"username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": TEST_HWID}
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200, "Falha ao logar no setup do teste"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_contador_venda(db_session):
    if not db_session.query(ContadorVenda).first():
        db_session.add(ContadorVenda(id=1, proximo_numero=1))
        db_session.commit()


def _funcionario(client: TestClient, header: dict) -> int:
    r = client.post(
        "/api/v1/funcionarios/",
        json={
            "nome": "Vendedor Fiscal",
            "cpf": "11122233396",
            "contato": "11999999999",
            "usuario": {"nome": "vend_fiscal", "email": "vend_fiscal@empresa.com", "senha": "SenhaForte123!"},
            "endereco": [
                {
                    "logradouro": "Rua X",
                    "numero": "1",
                    "cep": "12345-678",
                    "bairro": "Centro",
                    "cidade": "São Paulo",
                    "estado": "SP",
                }
            ],
        },
        headers=header,
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _cliente(client: TestClient, header: dict, nome="Cliente Teste", doc="52998224725") -> int:
    r = client.post(
        "/api/v1/clientes/cliente_pf",
        json={
            "tipo": "PF",
            "nome": nome,
            "cpf": doc,
            "celular": "11988887777",
            "email": "cliente@teste.com",
            "endereco": [
                {
                    "logradouro": "Rua das Flores",
                    "numero": "123",
                    "bairro": "Jardim",
                    "cidade": "Campinas",
                    "estado": "SP",
                    "cep": "13000-000",
                }
            ],
        },
        headers=header,
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _produto(client: TestClient, header: dict, codigo="PROD01", varejo=5000, quantidade=10) -> int:
    r = client.post(
        "/api/v1/produtos/",
        json={
            "nome": f"Produto {codigo}",
            "codigo_produto": codigo,
            "codigo_barras": "7891234567890",
            "unidade_medida": "UN",
            "estoque": {"valor_varejo": varejo, "quantidade": quantidade},
        },
        headers=header,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _forma_pagamento(client: TestClient, header: dict) -> int:
    r = client.post(
        "/api/v1/formas-pagamento/",
        json={"nome": "Dinheiro", "ativo": True},
        headers=header,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_correcao_fiscal_venda_finalizada_sucesso(client: TestClient, db_session, header_with_token: dict):
    _seed_contador_venda(db_session)
    header = header_with_token
    func_id = _funcionario(client, header)
    prod_id = _produto(client, header, codigo="CF01", varejo=10000, quantidade=10)
    fp_id = _forma_pagamento(client, header)

    # 1. Cria venda sem cliente (venda rápida de balcão)
    cv = client.post("/api/v1/vendas/", json={"funcionario_id": func_id}, headers=header)
    assert cv.status_code == 201
    venda_id = cv.json()["id"]

    # Adiciona item e finaliza
    client.post(
        f"/api/v1/vendas/{venda_id}/itens",
        json={"tipo_produto": "CADASTRADO", "produto_id": prod_id, "quantidade": 2},
        headers=header,
    )
    fin = client.post(
        f"/api/v1/vendas/{venda_id}/finalizar",
        json={
            "acrescimo": 0,
            "pagamentos": [
                {
                    "forma_pagamento_id": fp_id,
                    "valor": 20000,
                    "juros_valor": 0,
                    "juros_responsavel": "LOJA",
                    "parcelado": False,
                    "qtd_parcelas": None,
                }
            ],
        },
        headers=header,
    )
    assert fin.status_code == 200, fin.text
    venda_fechada = fin.json()
    assert venda_fechada["status"] == "FINALIZADA"
    assert venda_fechada["cliente_id"] is None
    num_venda = venda_fechada["numero_venda"]

    # 2. Cria um cliente para vincular
    cliente_id = _cliente(client, header, nome="Maria Destinatária", doc="52998224725")

    # 3. Dispara correção cadastral e fiscal na venda FINALIZADA
    correcao_payload = {
        "cliente_id": cliente_id,
        "observacao": "NF-e emitida referente ao pedido de balcão.",
        "natureza_operacao": "Venda de Mercadoria",
        "consumidor_final": True,
        "indicador_presenca": 1,
    }
    r_corr = client.patch(
        f"/api/v1/vendas/{venda_id}/correcao-fiscal",
        json=correcao_payload,
        headers=header,
    )
    assert r_corr.status_code == 200, r_corr.text
    dados_atualizados = r_corr.json()

    # Validações
    assert dados_atualizados["cliente_id"] == cliente_id
    assert dados_atualizados["observacao"] == "NF-e emitida referente ao pedido de balcão."
    assert dados_atualizados["status"] == "FINALIZADA"
    assert dados_atualizados["numero_venda"] == num_venda


def test_invariancia_estoque_e_financeiro_apos_correcao(client: TestClient, db_session, header_with_token: dict):
    _seed_contador_venda(db_session)
    header = header_with_token
    func_id = _funcionario(client, header)
    prod_id = _produto(client, header, codigo="INV01", varejo=3500, quantidade=20)
    fp_id = _forma_pagamento(client, header)

    cv = client.post("/api/v1/vendas/", json={"funcionario_id": func_id}, headers=header)
    venda_id = cv.json()["id"]
    client.post(
        f"/api/v1/vendas/{venda_id}/itens",
        json={"tipo_produto": "CADASTRADO", "produto_id": prod_id, "quantidade": 3},
        headers=header,
    )
    client.post(
        f"/api/v1/vendas/{venda_id}/finalizar",
        json={
            "acrescimo": 0,
            "pagamentos": [
                {
                    "forma_pagamento_id": fp_id,
                    "valor": 10500,
                    "juros_valor": 0,
                    "juros_responsavel": "LOJA",
                    "parcelado": False,
                    "qtd_parcelas": None,
                }
            ],
        },
        headers=header,
    )

    # Verifica estoque antes da correção: 20 - 3 = 17
    prod_antes = db_session.query(Produto).filter(Produto.id == prod_id).first()
    assert prod_antes.estoque.quantidade == 17

    cliente_id = _cliente(client, header, nome="José Invariante", doc="52998224725")

    # Corrige venda
    client.patch(
        f"/api/v1/vendas/{venda_id}/correcao-fiscal",
        json={"cliente_id": cliente_id, "observacao": "Nova observacao"},
        headers=header,
    )

    # Verifica estoque após correção: estritamente 17
    db_session.expire_all()
    prod_depois = db_session.query(Produto).filter(Produto.id == prod_id).first()
    assert prod_depois.estoque.quantidade == 17

    # Verifica financeiro da venda
    venda_get = client.get(f"/api/v1/vendas/{venda_id}", headers=header).json()
    assert venda_get["total"] == 10500
    assert venda_get["subtotal"] == 10500


def test_correcao_fiscal_cliente_inexistente_erro(client: TestClient, db_session, header_with_token: dict):
    _seed_contador_venda(db_session)
    header = header_with_token
    func_id = _funcionario(client, header)

    cv = client.post("/api/v1/vendas/", json={"funcionario_id": func_id}, headers=header)
    venda_id = cv.json()["id"]

    r = client.patch(
        f"/api/v1/vendas/{venda_id}/correcao-fiscal",
        json={"cliente_id": 999999},
        headers=header,
    )
    assert r.status_code in (400, 404)


def test_correcao_fiscal_venda_inexistente_erro(client: TestClient, db_session, header_with_token: dict):
    _seed_contador_venda(db_session)
    header = header_with_token

    r = client.patch(
        "/api/v1/vendas/999999/correcao-fiscal",
        json={"observacao": "Teste"},
        headers=header,
    )
    assert r.status_code == 404


def test_detalhe_documento_fiscal_hidratado(client: TestClient, db_session, header_with_token: dict):
    _seed_contador_venda(db_session)
    header = header_with_token
    func_id = _funcionario(client, header)
    prod_id = _produto(client, header, codigo="NFE01", varejo=2500, quantidade=10)
    cliente_id = _cliente(client, header, nome="Ana Fiscal", doc="52998224725")
    fp_id = _forma_pagamento(client, header)

    # Cria configuração fiscal para empresa
    db_session.add(
        EmpresaFiscalSettings(
            empresa_id=1,
            ambiente_emissao=2,
            serie_nfe=1,
            ultimo_numero_nfe=10,
        )
    )
    db_session.commit()

    # Cria e finaliza venda
    cv = client.post(
        "/api/v1/vendas/",
        json={"funcionario_id": func_id, "cliente_id": cliente_id},
        headers=header,
    )
    venda_id = cv.json()["id"]
    client.post(
        f"/api/v1/vendas/{venda_id}/itens",
        json={"tipo_produto": "CADASTRADO", "produto_id": prod_id, "quantidade": 1},
        headers=header,
    )
    fin = client.post(
        f"/api/v1/vendas/{venda_id}/finalizar",
        json={
            "acrescimo": 0,
            "pagamentos": [
                {
                    "forma_pagamento_id": fp_id,
                    "valor": 2500,
                    "juros_valor": 0,
                    "juros_responsavel": "LOJA",
                    "parcelado": False,
                    "qtd_parcelas": None,
                }
            ],
        },
        headers=header,
    )
    num_venda = fin.json()["numero_venda"]

    # Cria um DocumentoFiscal mockado no banco para a venda
    doc = DocumentoFiscal(
        tipo_documento="NFE",
        origem_tipo="VENDA",
        origem_id=num_venda,
        status="REJEITADA",
        numero_documento=11,
        serie=1,
        ref_api="venda-test-ref",
        ambiente_emissao=2,
        valor_total=2500,
        mensagem_sefaz="Rejeição 696: Operação com não contribuinte deve indicar IE isenta",
        codigo_status_sefaz=696,
    )
    db_session.add(doc)
    db_session.commit()

    # Consulta o detalhe do documento via API fiscal
    r_doc = client.get(f"/api/v1/fiscal/documentos/{doc.id}", headers=header)
    assert r_doc.status_code == 200, r_doc.text
    dados = r_doc.json()

    assert dados["id"] == doc.id
    assert dados["status"] == "REJEITADA"
    assert dados["venda_id"] == venda_id
    assert dados["destinatario_id"] == cliente_id
    assert dados["destinatario_nome"] == "Ana Fiscal"
    assert dados["destinatario_documento"] == "52998224725"
    assert dados["destinatario_uf"] == "SP"
    assert dados["codigo_status_sefaz"] == 696
    assert len(dados["itens_resumo"]) == 1
    assert dados["itens_resumo"][0]["nome"] == "Produto NFE01"
    assert dados["itens_resumo"][0]["quantidade"] == 1


def test_reemissao_documento_cria_tentativa_pendente(client: TestClient, db_session, header_with_token: dict):
    _seed_contador_venda(db_session)
    header = header_with_token

    db_session.add(
        EmpresaFiscalSettings(
            empresa_id=1,
            ambiente_emissao=2,
            serie_nfe=1,
            ultimo_numero_nfe=10,
        )
    )
    db_session.commit()

    doc_rejeitado = DocumentoFiscal(
        tipo_documento="NFE",
        origem_tipo="VENDA",
        origem_id=101,
        status="REJEITADA",
        numero_documento=11,
        serie=1,
        ref_api="venda-101",
        ambiente_emissao=2,
        valor_total=5000,
        mensagem_sefaz="Rejeição 204: Duplicidade de NF-e",
        codigo_status_sefaz=204,
    )
    db_session.add(doc_rejeitado)
    db_session.commit()

    # Reemitir
    r_reemitir = client.post(f"/api/v1/fiscal/documentos/{doc_rejeitado.id}/reemitir", headers=header)
    assert r_reemitir.status_code == 200, r_reemitir.text
    novo_doc = r_reemitir.json()

    assert novo_doc["status"] == "PENDENTE"
    assert novo_doc["tentativa_anterior_id"] == doc_rejeitado.id
    assert novo_doc["origem_id"] == 101


def test_produto_get_by_id_endpoint(client: TestClient, db_session, header_with_token: dict):
    """Garante que o novo endpoint GET /api/v1/produtos/{produto_id} funciona perfeitamente."""
    header = header_with_token
    prod_id = _produto(client, header, codigo="PROD_ID_01", varejo=1500, quantidade=5)

    res = client.get(f"/api/v1/produtos/{prod_id}", headers=header)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == prod_id
    assert data["codigo_produto"] == "PROD_ID_01"
    assert data["estoque"]["valor_varejo"] == 1500


def test_documento_fiscal_timestamps_utc(client: TestClient, db_session, header_with_token: dict):
    """Garante que os timestamps de documentos fiscais são salvos e retornados com integridade."""
    _seed_contador_venda(db_session)
    header = header_with_token

    db_session.add(
        EmpresaFiscalSettings(
            empresa_id=1,
            ambiente_emissao=2,
            serie_nfe=1,
            ultimo_numero_nfe=50,
        )
    )
    db_session.commit()

    doc = DocumentoFiscal(
        tipo_documento="NFE",
        origem_tipo="VENDA",
        origem_id=500,
        status="AUTORIZADA",
        numero_documento=50,
        serie=1,
        ref_api="venda-500",
        ambiente_emissao=2,
        valor_total=10000,
    )
    db_session.add(doc)
    db_session.commit()

    r = client.get(f"/api/v1/fiscal/documentos/{doc.id}", headers=header)
    assert r.status_code == 200, r.text
    doc_json = r.json()
    assert doc_json["data_criacao"] is not None
    assert doc_json["data_atualizacao"] is not None


def test_bloqueio_correcao_venda_com_nfe_autorizada(client: TestClient, db_session, header_with_token: dict):
    """Garante que uma venda com NF-e já autorizada não pode ter dados alterados via correção fiscal."""
    _seed_contador_venda(db_session)
    header = header_with_token
    func_id = _funcionario(client, header)
    prod_id = _produto(client, header, codigo="BLQ01", varejo=3000, quantidade=5)
    fp_id = _forma_pagamento(client, header)

    # 1. Cria e finaliza venda
    cv = client.post("/api/v1/vendas/", json={"funcionario_id": func_id}, headers=header)
    assert cv.status_code == 201
    venda_id = cv.json()["id"]

    client.post(
        f"/api/v1/vendas/{venda_id}/itens",
        json={"tipo_produto": "CADASTRADO", "produto_id": prod_id, "quantidade": 1},
        headers=header,
    )
    fin = client.post(
        f"/api/v1/vendas/{venda_id}/finalizar",
        json={
            "acrescimo": 0,
            "pagamentos": [
                {
                    "forma_pagamento_id": fp_id,
                    "valor": 3000,
                    "juros_valor": 0,
                    "juros_responsavel": "LOJA",
                    "parcelado": False,
                    "qtd_parcelas": None,
                }
            ],
        },
        headers=header,
    )
    assert fin.status_code == 200
    num_venda = fin.json()["numero_venda"]

    # 2. Cria documento AUTORIZADA para esta venda
    doc = DocumentoFiscal(
        tipo_documento="NFE",
        origem_tipo="VENDA",
        origem_id=num_venda,
        status="AUTORIZADA",
        numero_documento=99,
        serie=1,
        ref_api=f"venda-{num_venda}",
        ambiente_emissao=2,
        valor_total=3000,
    )
    db_session.add(doc)
    db_session.commit()

    # 3. Tenta aplicar correção fiscal na venda -> DEVE FALHAR (409)
    #    O bloqueio passou a responder 409 com detail estruturado, igual ao
    #    resto do módulo fiscal (ver emissao.py). O frontend lê detail.mensagem.
    cliente_id = _cliente(client, header, nome="Tentativa Invalida")
    res_bloq = client.patch(
        f"/api/v1/vendas/{venda_id}/correcao-fiscal",
        json={"cliente_id": cliente_id},
        headers=header,
    )
    assert res_bloq.status_code == 409, res_bloq.text
    detalhe = res_bloq.json()["detail"]
    assert detalhe["codigo"] == "NF_AUTORIZADA"
    assert "autorizada" in detalhe["mensagem"]
    assert detalhe["documento_id"] is not None
