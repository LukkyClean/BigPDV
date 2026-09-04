# ---------------------------------------------------------------------------
# F3a — configuração de comissão no Cargo (persistência dos campos novos).
# ---------------------------------------------------------------------------

TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"


def _auth(client):
    client.post("/api/v1/usuarios/", json={
        "nome": "Admin Master", "email": TEST_USER_EMAIL, "senha": TEST_USER_PASSWORD,
    })
    login = client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": "test-terminal-hwid",
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}
    empresa = {
        "razao_social": "Empresa Teste 000199 LTDA", "nome_fantasia": "Teste", "is_cnpj": True,
        "documento": "12345678000195", "regime_tributario": "Simples Nacional",
        "celular": "11999998888", "segmento": "assistencia_tecnica",
        "endereco": [{"logradouro": "Av. Paulista", "numero": "1000", "bairro": "Bela Vista",
                      "cidade": "São Paulo", "estado": "SP", "cep": "01310-100"}],
    }
    r = client.post("/api/v1/empresas/", json=empresa, headers=header)
    assert r.status_code == 201, r.text
    return header


def test_cargo_persiste_comissao(client, db_session):
    header = _auth(client)
    r = client.post("/api/v1/cargos/", json={
        "nome": "Vendedor",
        "permissoes": {"view_sales": True},
        "comissao_venda_percentual": 500,    # 5,00%
        "comissao_servico_percentual": 800,  # 8,00%
        "meta_mensal": 500000,               # R$ 5.000,00
    }, headers=header)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body["comissao_venda_percentual"] == 500
    assert body["comissao_servico_percentual"] == 800
    assert body["meta_mensal"] == 500000
    cargo_id = body["id"]

    # Update parcial: muda só o % de venda, os demais permanecem.
    u = client.put(f"/api/v1/cargos/{cargo_id}", json={"comissao_venda_percentual": 600}, headers=header)
    assert u.status_code == 200, u.text
    ub = u.json()
    assert ub["comissao_venda_percentual"] == 600
    assert ub["comissao_servico_percentual"] == 800
    assert ub["meta_mensal"] == 500000


def test_cargo_comissao_opcional(client, db_session):
    # Cargo sem comissão informada persiste com null (herda depois).
    header = _auth(client)
    r = client.post("/api/v1/cargos/", json={"nome": "Estoquista", "permissoes": {}}, headers=header)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body["comissao_venda_percentual"] is None
    assert body["meta_mensal"] is None
