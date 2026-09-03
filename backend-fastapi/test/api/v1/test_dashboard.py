# ---------------------------------------------------------------------------
# Testes do Dashboard — Fase A (separacao de acesso).
#
# Regra do dono: a VISAO GERAL da loja e exclusiva do Master; o funcionario so
# acessa os endpoints pessoais (filtrados pelo proprio funcionario_id).
# ---------------------------------------------------------------------------

from starlette import status

MASTER_EMAIL = "dono.dash@example.com"
MASTER_PASSWORD = "senhaSegura456"
HWID = "test-terminal-hwid"

# Endpoints de VISAO GERAL — exclusivos do Master.
OVERVIEW_ENDPOINTS = [
    "/api/v1/dashboard/stats",
    "/api/v1/dashboard/tendencia",
    "/api/v1/dashboard/os-vencendo",
    "/api/v1/dashboard/estoque-baixo",
    "/api/v1/dashboard/ranking-funcionarios",
    "/api/v1/dashboard/os-por-status",
    "/api/v1/dashboard/formas-pagamento",
    "/api/v1/dashboard/os-atrasadas-empresa",
    "/api/v1/dashboard/ultimas-vendas",
]

# Endpoints PESSOAIS — qualquer funcionario logado acessa (dados so dele).
PERSONAL_ENDPOINTS = [
    "/api/v1/dashboard/meu-resumo",
    "/api/v1/dashboard/minha-tendencia",
    "/api/v1/dashboard/minha-fila",
    "/api/v1/dashboard/minhas-os-atrasadas",
    "/api/v1/dashboard/minha-atividade-hoje",
]


def _auth_master(client):
    """Cria o usuario Master (is_master=True via /usuarios/) + empresa e retorna o header."""
    client.post("/api/v1/usuarios/", json={
        "nome": "Dono da Loja", "email": MASTER_EMAIL, "senha": MASTER_PASSWORD,
    })
    login = client.post("/api/v1/auth/login", data={
        "username": MASTER_EMAIL, "password": MASTER_PASSWORD, "hwid": HWID,
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}
    empresa = {
        "razao_social": "Empresa Dash 000199 LTDA", "nome_fantasia": "Dash", "is_cnpj": True,
        "documento": "12345678000195", "regime_tributario": "Simples Nacional",
        "celular": "11999998888", "segmento": "assistencia_tecnica",
        "endereco": [{"logradouro": "Av. Paulista", "numero": "1000", "bairro": "Bela Vista",
                      "cidade": "São Paulo", "estado": "SP", "cep": "01310-100"}],
    }
    r = client.post("/api/v1/empresas/", json=empresa, headers=header)
    assert r.status_code == 201, r.text
    return header


def _auth_funcionario(client, master_header):
    """Cria um funcionario comum (nao-master, sem cargo) e loga como ele.
    Retorna (header, funcionario_id)."""
    payload = {
        "nome": "Vendedor Comum", "cpf": "11122233396",
        "usuario": {"nome": "vendcomum", "email": "vendcomum@empresa.com", "senha": "SenhaForte123!"},
        "endereco": [{"logradouro": "Rua X", "numero": "1", "cep": "12345-678",
                      "bairro": "Centro", "cidade": "Lab City", "estado": "SP"}],
    }
    r = client.post("/api/v1/funcionarios/", json=payload, headers=master_header)
    assert r.status_code in (200, 201), r.text
    func_id = r.json()["id"]

    login = client.post("/api/v1/auth/login", data={
        "username": "vendcomum@empresa.com", "password": "SenhaForte123!", "hwid": HWID,
    })
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, func_id


def _cliente(client, header):
    r = client.post("/api/v1/clientes/cliente_pf", json={
        "nome": "Cliente Dash", "cpf": "98765432100", "tipo": "PF", "celular": "11987654321",
        "endereco": [{"logradouro": "Rua Y", "numero": "10", "bairro": "Centro",
                      "cidade": "Campinas", "estado": "SP", "cep": "13010-000"}],
    }, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _forma_pagamento(client, header):
    r = client.post("/api/v1/formas-pagamento/", json={"nome": "Dinheiro", "ativo": True}, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _os_finalizada(client, header, cliente_id, fp_id, numero_serie, valor, funcionario_id):
    payload = {
        "cliente_id": cliente_id, "prioridade": "NORMAL", "defeito_relatado": "Nao liga",
        "dados_adicionais": {}, "funcionario_id": funcionario_id,
        "objeto": {"marca": "Dell", "modelo": "Inspiron", "numero_serie": numero_serie, "dados_adicionais": {}},
        "itens": [{"tipo": "SERVICO", "nome": "Reparo", "unidade_medida": "UN", "quantidade": 1, "valor_unitario": valor}],
    }
    r = client.post("/api/v1/ordens-servico/", json=payload, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    numero = r.json()["numero_os"]
    fin = {"situacao_equipamento": "REPARADO", "garantia": "90 dias",
           "pagamentos": [{"forma_pagamento_id": fp_id, "valor": valor}]}
    rf = client.put(f"/api/v1/ordens-servico/{numero}/finalizar", json=fin, headers=header)
    assert rf.status_code == 200, rf.text
    return numero


def test_overview_liberado_para_master(client, db_session):
    """Master acessa toda a visao geral (200)."""
    header = _auth_master(client)
    for url in OVERVIEW_ENDPOINTS:
        r = client.get(url, headers=header)
        assert r.status_code == 200, f"{url} -> {r.status_code}: {r.text}"


def test_overview_bloqueado_para_funcionario(client, db_session):
    """Funcionario comum recebe 403 em TODA a visao geral."""
    master_header = _auth_master(client)
    func_header, _ = _auth_funcionario(client, master_header)
    for url in OVERVIEW_ENDPOINTS:
        r = client.get(url, headers=func_header)
        assert r.status_code == status.HTTP_403_FORBIDDEN, f"{url} deveria ser 403, veio {r.status_code}: {r.text}"


def test_endpoints_pessoais_liberados_para_funcionario(client, db_session):
    """Funcionario comum acessa os endpoints pessoais (200) — dados dele."""
    master_header = _auth_master(client)
    func_header, _ = _auth_funcionario(client, master_header)
    for url in PERSONAL_ENDPOINTS:
        r = client.get(url, headers=func_header)
        assert r.status_code == 200, f"{url} -> {r.status_code}: {r.text}"


def test_periodo_do_funcionario_limitado_a_um_mes(client, db_session):
    """Teto de 1 mes: /meu-resumo aceita hoje|semana|mes e recusa periodos maiores."""
    master_header = _auth_master(client)
    func_header, _ = _auth_funcionario(client, master_header)

    for periodo in ("hoje", "semana", "mes"):
        r = client.get(f"/api/v1/dashboard/meu-resumo?periodo={periodo}", headers=func_header)
        assert r.status_code == 200, f"{periodo} -> {r.status_code}: {r.text}"

    # 'ano' (ou qualquer periodo maior) e recusado pela validacao do endpoint (422).
    r = client.get("/api/v1/dashboard/meu-resumo?periodo=ano", headers=func_header)
    assert r.status_code == 422, r.text


def test_faturamento_total_soma_vendas_e_os(client, db_session):
    """Fase B: faturamento_total (loja) e meu_faturamento (pessoal) somam a OS."""
    master_header = _auth_master(client)
    func_header, func_id = _auth_funcionario(client, master_header)
    cliente_id = _cliente(client, master_header)
    fp_id = _forma_pagamento(client, master_header)

    # OS de R$500,00 finalizada pelo funcionario.
    _os_finalizada(client, master_header, cliente_id, fp_id, "DASH-FAT-1", 50000, funcionario_id=func_id)

    # Master: faturamento_total = vendas + OS; os_total reflete a OS.
    r = client.get("/api/v1/dashboard/stats?periodo=mes", headers=master_header)
    assert r.status_code == 200, r.text
    stats = r.json()
    assert stats["os_total"] == 50000
    assert stats["faturamento_total"] == stats["vendas_total"] + stats["os_total"]
    assert stats["faturamento_total"] >= 50000

    # Funcionario: meu_faturamento = minhas vendas + minhas OS.
    r = client.get("/api/v1/dashboard/meu-resumo?periodo=mes", headers=func_header)
    assert r.status_code == 200, r.text
    resumo = r.json()
    assert resumo["minhas_os_valor"] == 50000
    assert resumo["meu_faturamento"] == resumo["minhas_vendas_valor"] + resumo["minhas_os_valor"]

    # A tendencia da loja no mes soma 50000 no total_geral (a OS caiu hoje).
    r = client.get("/api/v1/dashboard/tendencia?periodo=mes", headers=master_header)
    assert r.status_code == 200, r.text
    total_serie = sum(i["total_geral"] for i in r.json()["items"])
    assert total_serie == 50000


def test_ranking_ordena_por_vendas_mais_os_e_esconde_zerados(client, db_session):
    """Fase C: ranking soma OS (justo p/ tecnico) e esconde funcionario 100% zerado."""
    master_header = _auth_master(client)
    func_header, func_id = _auth_funcionario(client, master_header)
    cliente_id = _cliente(client, master_header)
    fp_id = _forma_pagamento(client, master_header)

    # Segundo funcionario SEM nenhum movimento (deve sumir do ranking).
    r2 = client.post("/api/v1/funcionarios/", json={
        "nome": "Sem Movimento", "cpf": "55566677720",
        "usuario": {"nome": "vendzero", "email": "vendzero@empresa.com", "senha": "SenhaForte123!"},
        "endereco": [{"logradouro": "Rua Z", "numero": "2", "cep": "12345-678",
                      "bairro": "Centro", "cidade": "Lab City", "estado": "SP"}],
    }, headers=master_header)
    assert r2.status_code in (200, 201), r2.text
    func2_id = r2.json()["id"]

    # OS de R$500,00 finalizada pelo func_id — so servico, sem venda.
    _os_finalizada(client, master_header, cliente_id, fp_id, "RANK-1", 50000, funcionario_id=func_id)

    r = client.get("/api/v1/dashboard/ranking-funcionarios?periodo=mes", headers=master_header)
    assert r.status_code == 200, r.text
    items = r.json()["items"]

    ids = [i["id"] for i in items]
    assert func_id in ids
    assert func2_id not in ids  # zerado -> escondido

    alvo = next(i for i in items if i["id"] == func_id)
    assert alvo["total_vendas_valor"] == 0
    assert alvo["total_os_valor"] == 50000
    assert alvo["total_geral"] == 50000  # ranqueado por vendas + OS
    assert alvo["posicao"] == 1


def test_dashboard_conta_os_pela_finalizacao_nao_pela_abertura(client, db_session):
    """Bug real: OS aberta dias atras e finalizada hoje deixava o painel de HOJE
    dizendo "Nenhuma OS" logo acima de "Servicos R$ 51,10". O painel e de
    resultados, entao o card conta o que foi FINALIZADO no periodo."""
    from datetime import datetime, timedelta
    from app.db.models.ordem_servico import OrdemServico as OSModel

    master_header = _auth_master(client)
    func_header, func_id = _auth_funcionario(client, master_header)
    cliente_id = _cliente(client, master_header)
    fp_id = _forma_pagamento(client, master_header)

    numero = _os_finalizada(client, master_header, cliente_id, fp_id, "DASH-DT-1", 5110, funcionario_id=func_id)

    # Abertura empurrada para tras; finalizacao continua hoje.
    os_db = db_session.query(OSModel).filter(OSModel.numero_os == numero).first()
    os_db.data_criacao = datetime.utcnow() - timedelta(days=4)
    db_session.commit()

    r = client.get("/api/v1/dashboard/stats?periodo=hoje", headers=master_header)
    assert r.status_code == 200, r.text
    stats = r.json()
    assert stats["os_count"] == 1, "a OS finalizada hoje tem que aparecer no painel de hoje"
    assert stats["os_total"] == 5110, "o valor e a contagem usam a MESMA ancora"

    # Coerencia do painel pessoal do funcionario.
    r = client.get("/api/v1/dashboard/meu-resumo?periodo=hoje", headers=func_header)
    resumo = r.json()
    assert resumo["minhas_os_concluidas"] == 1
    assert resumo["minhas_os_valor"] == 5110
