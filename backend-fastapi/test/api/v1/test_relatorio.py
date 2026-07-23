# ---------------------------------------------------------------------------
# Testes do modulo de Relatorios — Fase 1 (Faturamento).
# ---------------------------------------------------------------------------

from datetime import datetime

from starlette import status

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
        "documento": "12345678000199", "regime_tributario": "Simples Nacional",
        "celular": "11999998888", "segmento": "assistencia_tecnica",
        "endereco": [{"logradouro": "Av. Paulista", "numero": "1000", "bairro": "Bela Vista",
                      "cidade": "São Paulo", "estado": "SP", "cep": "01310-100"}],
    }
    r = client.post("/api/v1/empresas/", json=empresa, headers=header)
    assert r.status_code == 201, r.text
    return header


def _cliente(client, header):
    r = client.post("/api/v1/clientes/cliente_pf", json={
        "nome": "João Pedro Silva", "cpf": "98765432101", "tipo": "PF", "celular": "11987654321",
        "endereco": [{"logradouro": "Rua das Flores", "numero": "100", "bairro": "Centro",
                      "cidade": "Campinas", "estado": "SP", "cep": "13010-000"}],
    }, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _forma_pagamento(client, header):
    r = client.post("/api/v1/formas-pagamento/", json={"nome": "Dinheiro", "ativo": True}, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _os_finalizada(client, header, cliente_id, fp_id, numero_serie, valor):
    payload = {
        "cliente_id": cliente_id, "prioridade": "NORMAL", "defeito_relatado": "Não liga",
        "dados_adicionais": {},
        "objeto": {"marca": "Dell", "modelo": "Inspiron", "numero_serie": numero_serie, "dados_adicionais": {}},
        "itens": [{"tipo": "SERVICO", "nome": "Reparo", "unidade_medida": "UN", "quantidade": 1, "valor_unitario": valor}],
    }
    r = client.post("/api/v1/ordens-servico/", json=payload, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    numero = r.json()["numero_os"]
    fin = {
        "situacao_equipamento": "REPARADO", "garantia": "90 dias",
        "pagamentos": [{"forma_pagamento_id": fp_id, "valor": valor}],
    }
    rf = client.put(f"/api/v1/ordens-servico/{numero}/finalizar", json=fin, headers=header)
    assert rf.status_code == 200, rf.text
    return numero


def test_faturamento_soma_os_finalizada(client, db_session):
    header = _auth(client)
    cliente_id = _cliente(client, header)
    fp_id = _forma_pagamento(client, header)
    _os_finalizada(client, header, cliente_id, fp_id, "SERIAL-R1", 14000)

    hoje = datetime.utcnow().date().isoformat()
    r = client.get(f"/api/v1/relatorios/faturamento?inicio={hoje}&fim={hoje}", headers=header)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["faturamento_total"] == 14000, body
    assert body["faturamento_os"] == 14000
    assert body["faturamento_vendas"] == 0
    assert body["qtd_os"] == 1
    assert body["ticket_medio"] == 14000

    # série por dia: o dia de hoje soma 14000
    dia_hoje = next((d for d in body["por_dia"] if d["dia"] == hoje), None)
    assert dia_hoje is not None, body["por_dia"]
    assert dia_hoje["total_geral"] == 14000

    # formas de pagamento: Dinheiro = 14000
    assert any(f["nome"] == "Dinheiro" and f["valor_total"] == 14000 for f in body["formas_pagamento"]), body["formas_pagamento"]


def test_faturamento_periodo_vazio_zera(client, db_session):
    header = _auth(client)
    # sem nenhuma transação, faturamento zerado e ticket 0 (sem divisão por zero)
    hoje = datetime.utcnow().date().isoformat()
    r = client.get(f"/api/v1/relatorios/faturamento?inicio={hoje}&fim={hoje}", headers=header)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["faturamento_total"] == 0
    assert body["ticket_medio"] == 0
    assert body["qtd_os"] == 0 and body["qtd_vendas"] == 0
