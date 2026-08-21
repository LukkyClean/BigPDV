# ---------------------------------------------------------------------------
# Testes do modulo de Relatorios — Fase 1 (Faturamento).
# ---------------------------------------------------------------------------

from datetime import datetime

from starlette import status

from app.db.models.contador_venda import ContadorVenda


def _seed_contador_venda(db_session):
    """Semeia o contador global de vendas (id=1) — normalmente feito no startup do app,
    que não roda nos testes. Necessário para finalizar vendas."""
    if not db_session.query(ContadorVenda).first():
        db_session.add(ContadorVenda(id=1, proximo_numero=1))
        db_session.commit()

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


def _funcionario(client, header):
    payload = {
        "nome": "Vendedor Teste", "cpf": "11122233344", "contato": "11999999999",
        "usuario": {"nome": "vendedor1", "email": "vend1@empresa.com", "senha": "SenhaForte123!"},
        "endereco": [{"logradouro": "Rua X", "numero": "1", "cep": "12345-678",
                      "bairro": "Centro", "cidade": "Lab City", "estado": "SP"}],
    }
    r = client.post("/api/v1/funcionarios/", json=payload, headers=header)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _produto(client, header, codigo, varejo, entrada=None, quantidade=0, minima=None, categoria=None):
    estoque = {"valor_varejo": varejo, "quantidade": quantidade}
    if entrada is not None:
        estoque["valor_entrada"] = entrada
    if minima is not None:
        estoque["quantidade_minima"] = minima
    payload = {
        "nome": f"Produto {codigo}", "codigo_produto": codigo, "unidade_medida": "UN",
        "categoria": categoria, "estoque": estoque,
    }
    r = client.post("/api/v1/produtos/", json=payload, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _venda_finalizada(client, header, funcionario_id, produto_id, quantidade, fp_id):
    """Cria venda -> adiciona item cadastrado (preço vem do estoque) -> finaliza."""
    cv = client.post("/api/v1/vendas/", json={"funcionario_id": funcionario_id}, headers=header)
    assert cv.status_code == 201, cv.text
    venda_id = cv.json()["id"]
    add = client.post(f"/api/v1/vendas/{venda_id}/itens", json={
        "tipo_produto": "CADASTRADO", "produto_id": produto_id, "quantidade": quantidade,
    }, headers=header)
    assert add.status_code == 201, add.text
    total = add.json()["financeiro_atualizado"]["total"]
    fin = client.post(f"/api/v1/vendas/{venda_id}/finalizar", json={
        "pagamentos": [{"forma_pagamento_id": fp_id, "valor": total, "parcelado": False, "qtd_parcelas": None}],
    }, headers=header)
    assert fin.status_code == 200, fin.text
    return venda_id, total


def _os_finalizada(client, header, cliente_id, fp_id, numero_serie, valor, funcionario_id=None, situacao="REPARADO"):
    objeto_payload = {
        "cliente_id": cliente_id, "prioridade": "NORMAL", "defeito_relatado": "Não liga",
        "dados_adicionais": {},
        "objeto": {"marca": "Dell", "modelo": "Inspiron", "numero_serie": numero_serie, "dados_adicionais": {}},
        "itens": [{"tipo": "SERVICO", "nome": "Reparo", "unidade_medida": "UN", "quantidade": 1, "valor_unitario": valor}],
    }
    if funcionario_id is not None:
        objeto_payload["funcionario_id"] = funcionario_id
    payload = objeto_payload
    r = client.post("/api/v1/ordens-servico/", json=payload, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    numero = r.json()["numero_os"]
    fin = {
        "situacao_equipamento": situacao, "garantia": "90 dias",
        "pagamentos": [{"forma_pagamento_id": fp_id, "valor": valor}],
    }
    rf = client.put(f"/api/v1/ordens-servico/{numero}/finalizar", json=fin, headers=header)
    assert rf.status_code == 200, rf.text
    return numero


def _os_aberta(client, header, cliente_id, numero_serie, funcionario_id=None):
    """Cria uma OS e deixa ABERTA (não finaliza) — para medir throughput/backlog."""
    objeto_payload = {
        "cliente_id": cliente_id, "prioridade": "NORMAL", "defeito_relatado": "Não liga",
        "dados_adicionais": {},
        "objeto": {"marca": "Dell", "modelo": "Inspiron", "numero_serie": numero_serie, "dados_adicionais": {}},
        "itens": [{"tipo": "SERVICO", "nome": "Reparo", "unidade_medida": "UN", "quantidade": 1, "valor_unitario": 5000}],
    }
    if funcionario_id is not None:
        objeto_payload["funcionario_id"] = funcionario_id
    r = client.post("/api/v1/ordens-servico/", json=objeto_payload, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    return r.json()["numero_os"]


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


def _os_finalizada_com_juros(client, header, cliente_id, fp_id, serie, base, juros, responsavel):
    """OS finalizada com juros de cartão, repassado ou absorvido pela loja."""
    payload = {
        "cliente_id": cliente_id, "prioridade": "NORMAL", "defeito_relatado": "Não liga",
        "dados_adicionais": {},
        "objeto": {"marca": "Dell", "modelo": "Inspiron", "numero_serie": serie, "dados_adicionais": {}},
        "itens": [{"tipo": "SERVICO", "nome": "Reparo", "unidade_medida": "UN",
                   "quantidade": 1, "valor_unitario": base}],
    }
    r = client.post("/api/v1/ordens-servico/", json=payload, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    numero = r.json()["numero_os"]

    repassa = responsavel == "CLIENTE"
    fin = {
        "situacao_equipamento": "REPARADO", "garantia": "90 dias",
        "acrescimo": juros if repassa else 0,
        "pagamentos": [{
            "forma_pagamento_id": fp_id,
            "valor": base + juros if repassa else base,
            "juros_valor": juros,
            "juros_responsavel": responsavel,
        }],
    }
    rf = client.put(f"/api/v1/ordens-servico/{numero}/finalizar", json=fin, headers=header)
    assert rf.status_code == 200, rf.text
    return numero


def test_faturamento_juros_absorvido_reduz_o_liquido(client, db_session):
    """LOJA: o cliente pagou 14000 (o bruto não muda), mas 700 saíram do caixa
    da loja para a operadora — o líquido tem que refletir isso."""
    header = _auth(client)
    cliente_id = _cliente(client, header)
    fp_id = _forma_pagamento(client, header)
    _os_finalizada_com_juros(client, header, cliente_id, fp_id, "SERIAL-JA", 14000, 700, "LOJA")

    hoje = datetime.utcnow().date().isoformat()
    r = client.get(f"/api/v1/relatorios/faturamento?inicio={hoje}&fim={hoje}", headers=header)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["faturamento_total"] == 14000, "bruto não muda: o cliente não foi cobrado a mais"
    assert body["juros_absorvido"] == 700
    assert body["juros_repassado"] == 0
    assert body["faturamento_liquido"] == 13300, "o juros bancado pela loja sai do líquido"


def test_faturamento_juros_repassado_sai_do_liquido(client, db_session):
    """CLIENTE: o bruto sobe (o cliente pagou a mais), mas o juros vai para a
    operadora — então não pode ficar contado como receita da loja."""
    header = _auth(client)
    cliente_id = _cliente(client, header)
    fp_id = _forma_pagamento(client, header)
    _os_finalizada_com_juros(client, header, cliente_id, fp_id, "SERIAL-JR", 14000, 700, "CLIENTE")

    hoje = datetime.utcnow().date().isoformat()
    r = client.get(f"/api/v1/relatorios/faturamento?inicio={hoje}&fim={hoje}", headers=header)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["faturamento_total"] == 14700, "bruto inclui o acréscimo cobrado do cliente"
    assert body["juros_repassado"] == 700
    assert body["juros_absorvido"] == 0
    assert body["faturamento_liquido"] == 14000, "a loja fica com a base, não com o juros"


def test_faturamento_sem_juros_liquido_igual_ao_bruto(client, db_session):
    """Loja que não cobra juros: líquido e bruto são o mesmo número, e as duas
    linhas de juros ficam zeradas."""
    header = _auth(client)
    cliente_id = _cliente(client, header)
    fp_id = _forma_pagamento(client, header)
    _os_finalizada(client, header, cliente_id, fp_id, "SERIAL-SJ", 14000)

    hoje = datetime.utcnow().date().isoformat()
    r = client.get(f"/api/v1/relatorios/faturamento?inicio={hoje}&fim={hoje}", headers=header)
    body = r.json()

    assert body["juros_repassado"] == 0 and body["juros_absorvido"] == 0
    assert body["faturamento_liquido"] == body["faturamento_total"] == 14000


def test_faturamento_conta_no_dia_da_FINALIZACAO_nao_no_da_abertura(client, db_session):
    """Bug real: OS aberta em 23/07 e finalizada em 27/07 aparecia como
    faturamento do dia 23 — receita lançada num dia em que ela nem tinha sido
    cobrada. O dinheiro entra quando a OS fecha."""
    from datetime import timedelta
    from app.db.models.ordem_servico import OrdemServico as OSModel

    header = _auth(client)
    cliente_id = _cliente(client, header)
    fp_id = _forma_pagamento(client, header)
    numero = _os_finalizada(client, header, cliente_id, fp_id, "SERIAL-DT", 14000)

    # Empurra a abertura para 5 dias atrás, mantendo a finalização hoje.
    os_db = db_session.query(OSModel).filter(OSModel.numero_os == numero).first()
    os_db.data_criacao = datetime.utcnow() - timedelta(days=5)
    db_session.commit()

    hoje = datetime.utcnow().date()
    abertura = (hoje - timedelta(days=5)).isoformat()

    # Período que contém SÓ o dia da abertura: não pode ter faturamento.
    r = client.get(f"/api/v1/relatorios/faturamento?inicio={abertura}&fim={abertura}", headers=header)
    assert r.status_code == 200, r.text
    assert r.json()["faturamento_os"] == 0, "abertura não é faturamento"

    # Período que contém só o dia da finalização: é aqui que a receita entra.
    r = client.get(f"/api/v1/relatorios/faturamento?inicio={hoje.isoformat()}&fim={hoje.isoformat()}", headers=header)
    body = r.json()
    assert body["faturamento_os"] == 14000, body
    assert body["qtd_os"] == 1

    dia = next((d for d in body["por_dia"] if d["dia"] == hoje.isoformat()), None)
    assert dia is not None and dia["total_os"] == 14000, "a série por dia usa a mesma âncora"


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


def test_ranking_funcionario_soma_faturamento(client, db_session):
    header = _auth(client)
    cliente_id = _cliente(client, header)
    fp_id = _forma_pagamento(client, header)
    func_id = _funcionario(client, header)
    _os_finalizada(client, header, cliente_id, fp_id, "SERIAL-RK", 20000, funcionario_id=func_id)

    hoje = datetime.utcnow().date().isoformat()
    r = client.get(f"/api/v1/relatorios/ranking-funcionarios?inicio={hoje}&fim={hoje}", headers=header)
    assert r.status_code == 200, r.text
    itens = r.json()["itens"]
    alvo = next((i for i in itens if i["funcionario_id"] == func_id), None)
    assert alvo is not None, itens
    assert alvo["faturamento_os"] == 20000
    assert alvo["faturamento_vendas"] == 0
    assert alvo["faturamento_total"] == 20000
    assert alvo["qtd_os"] == 1


def test_comissao_calcula_pela_taxa_do_cargo(client, db_session):
    header = _auth(client)
    cliente_id = _cliente(client, header)
    fp_id = _forma_pagamento(client, header)

    # Cargo com 5% em vendas e 8% em serviços (basis points)
    c = client.post("/api/v1/cargos/", json={
        "nome": "Tecnico", "permissoes": {},
        "comissao_venda_percentual": 500, "comissao_servico_percentual": 800,
    }, headers=header)
    assert c.status_code in (200, 201), c.text
    cargo_id = c.json()["id"]

    func_id = _funcionario(client, header)
    lk = client.put(f"/api/v1/funcionarios/{func_id}/cargo?cargo_id={cargo_id}", headers=header)
    assert lk.status_code == 200, lk.text

    # OS de R$1.000,00 finalizada, atribuída ao funcionário → base de serviço
    _os_finalizada(client, header, cliente_id, fp_id, "SERIAL-COM", 100000, funcionario_id=func_id)

    hoje = datetime.utcnow().date().isoformat()
    r = client.get(f"/api/v1/relatorios/comissoes?inicio={hoje}&fim={hoje}", headers=header)
    assert r.status_code == 200, r.text
    body = r.json()

    alvo = next((i for i in body["itens"] if i["funcionario_id"] == func_id), None)
    assert alvo is not None, body["itens"]
    # 8% de 100000 = 8000 (serviço); vendas 0
    assert alvo["percentual_servico"] == 800
    assert alvo["comissao_servico"] == 8000
    assert alvo["comissao_vendas"] == 0
    assert alvo["comissao_total"] == 8000
    assert body["total_comissao"] >= 8000
    # modo default (não configurado) = direto e comissão liberada
    assert alvo["comissao_modo"] == "direto"
    assert alvo["comissao_liberada"] is True


def test_comissao_modo_meta_bloqueia_abaixo_da_meta(client, db_session):
    """modo='meta': abaixo da meta a comissão trava em zero (gatilho)."""
    header = _auth(client)
    cliente_id = _cliente(client, header)
    fp_id = _forma_pagamento(client, header)

    # Cargo com gatilho por meta: meta R$2.000,00 e 8% em serviços
    c = client.post("/api/v1/cargos/", json={
        "nome": "Tecnico Meta", "permissoes": {},
        "comissao_servico_percentual": 800, "meta_mensal": 200000, "comissao_modo": "meta",
    }, headers=header)
    assert c.status_code in (200, 201), c.text
    cargo_id = c.json()["id"]

    func_id = _funcionario(client, header)
    lk = client.put(f"/api/v1/funcionarios/{func_id}/cargo?cargo_id={cargo_id}", headers=header)
    assert lk.status_code == 200, lk.text

    # Faturou R$1.000,00 < meta R$2.000,00 → não bateu, comissão zero
    _os_finalizada(client, header, cliente_id, fp_id, "SERIAL-META1", 100000, funcionario_id=func_id)

    hoje = datetime.utcnow().date().isoformat()
    r = client.get(f"/api/v1/relatorios/comissoes?inicio={hoje}&fim={hoje}", headers=header)
    assert r.status_code == 200, r.text
    body = r.json()

    alvo = next((i for i in body["itens"] if i["funcionario_id"] == func_id), None)
    assert alvo is not None, body["itens"]
    assert alvo["comissao_modo"] == "meta"
    assert alvo["comissao_liberada"] is False
    assert alvo["comissao_servico"] == 0
    assert alvo["comissao_total"] == 0


def test_comissao_modo_meta_libera_ao_atingir(client, db_session):
    """modo='meta': ao atingir a meta, paga a taxa cheia sobre a base."""
    header = _auth(client)
    cliente_id = _cliente(client, header)
    fp_id = _forma_pagamento(client, header)

    # Meta baixa (R$500,00) para o faturamento superar
    c = client.post("/api/v1/cargos/", json={
        "nome": "Tecnico Meta OK", "permissoes": {},
        "comissao_servico_percentual": 800, "meta_mensal": 50000, "comissao_modo": "meta",
    }, headers=header)
    assert c.status_code in (200, 201), c.text
    cargo_id = c.json()["id"]

    func_id = _funcionario(client, header)
    lk = client.put(f"/api/v1/funcionarios/{func_id}/cargo?cargo_id={cargo_id}", headers=header)
    assert lk.status_code == 200, lk.text

    # Faturou R$1.000,00 >= meta R$500,00 → libera; 8% de 100000 = 8000
    _os_finalizada(client, header, cliente_id, fp_id, "SERIAL-META2", 100000, funcionario_id=func_id)

    hoje = datetime.utcnow().date().isoformat()
    r = client.get(f"/api/v1/relatorios/comissoes?inicio={hoje}&fim={hoje}", headers=header)
    assert r.status_code == 200, r.text
    body = r.json()

    alvo = next((i for i in body["itens"] if i["funcionario_id"] == func_id), None)
    assert alvo is not None, body["itens"]
    assert alvo["comissao_modo"] == "meta"
    assert alvo["comissao_liberada"] is True
    assert alvo["comissao_servico"] == 8000
    assert alvo["comissao_total"] == 8000


def test_comissao_override_funcionario_vence_cargo(client, db_session):
    """O override no funcionário prevalece sobre o cargo (cascata func -> cargo).

    Cargo trava por meta; o funcionário sobrescreve modo='direto' e paga assim mesmo.
    """
    header = _auth(client)
    cliente_id = _cliente(client, header)
    fp_id = _forma_pagamento(client, header)

    # Cargo: gatilho por meta alta (travaria) + 8% serviço
    c = client.post("/api/v1/cargos/", json={
        "nome": "Tecnico Override", "permissoes": {},
        "comissao_servico_percentual": 800, "meta_mensal": 999999, "comissao_modo": "meta",
    }, headers=header)
    assert c.status_code in (200, 201), c.text
    cargo_id = c.json()["id"]

    func_id = _funcionario(client, header)
    lk = client.put(f"/api/v1/funcionarios/{func_id}/cargo?cargo_id={cargo_id}", headers=header)
    assert lk.status_code == 200, lk.text

    # Override no funcionário: paga direto (ignora a meta do cargo)
    up = client.put(f"/api/v1/funcionarios/{func_id}", json={"comissao_modo": "direto"}, headers=header)
    assert up.status_code == 200, up.text
    assert up.json()["comissao_modo"] == "direto"

    _os_finalizada(client, header, cliente_id, fp_id, "SERIAL-OVR", 100000, funcionario_id=func_id)

    hoje = datetime.utcnow().date().isoformat()
    r = client.get(f"/api/v1/relatorios/comissoes?inicio={hoje}&fim={hoje}", headers=header)
    assert r.status_code == 200, r.text
    body = r.json()

    alvo = next((i for i in body["itens"] if i["funcionario_id"] == func_id), None)
    assert alvo is not None, body["itens"]
    assert alvo["comissao_modo"] == "direto"
    assert alvo["comissao_liberada"] is True
    # taxa herdada do cargo (800), modo sobrescrito → 8% de 100000 = 8000
    assert alvo["comissao_servico"] == 8000


# ---------------------------------------------------------------------------
# Fase 4a — Estoque / Curva ABC
# ---------------------------------------------------------------------------

def test_estoque_curva_abc_classifica_por_faturamento(client, db_session):
    """Três produtos com faturamentos 70k/20k/10k → classes A/B/C pelo acumulado."""
    header = _auth(client)
    _seed_contador_venda(db_session)
    fp_id = _forma_pagamento(client, header)
    func_id = _funcionario(client, header)

    prod_a = _produto(client, header, "ABC-A", varejo=7000, entrada=3000, quantidade=100)
    prod_b = _produto(client, header, "ABC-B", varejo=2000, entrada=800, quantidade=100)
    prod_c = _produto(client, header, "ABC-C", varejo=1000, entrada=400, quantidade=100)

    # Vendas: A=10×7000=70k, B=10×2000=20k, C=10×1000=10k. Total 100k.
    _venda_finalizada(client, header, func_id, prod_a, 10, fp_id)
    _venda_finalizada(client, header, func_id, prod_b, 10, fp_id)
    _venda_finalizada(client, header, func_id, prod_c, 10, fp_id)

    hoje = datetime.utcnow().date().isoformat()
    r = client.get(f"/api/v1/relatorios/estoque?inicio={hoje}&fim={hoje}", headers=header)
    assert r.status_code == 200, r.text
    body = r.json()

    curva = {i["produto_id"]: i for i in body["curva_abc"]}
    assert curva[prod_a]["faturamento"] == 70000
    assert curva[prod_a]["classe"] == "A"          # acumulado 70% ≤ 80
    assert curva[prod_b]["faturamento"] == 20000
    assert curva[prod_b]["classe"] == "B"          # acumulado 90% ≤ 95
    assert curva[prod_c]["faturamento"] == 10000
    assert curva[prod_c]["classe"] == "C"          # acumulado 100%
    # participação de A = 70% do total
    assert curva[prod_a]["participacao_pct"] == 70.0
    assert curva[prod_c]["acumulado_pct"] == 100.0


def test_estoque_kpis_reposicao_e_parados(client, db_session):
    """Valor imobilizado, produto abaixo do mínimo e produto sem venda (parado)."""
    header = _auth(client)

    # 100 un a custo 1000 = 100000; não vende → parado; acima do mínimo (100 > 5)
    prod_parado = _produto(client, header, "STK-PARADO", varejo=2000, entrada=1000, quantidade=100, minima=5)
    # 3 un com mínimo 10 → abaixo do mínimo; também sem venda → parado
    prod_baixo = _produto(client, header, "STK-BAIXO", varejo=1000, entrada=500, quantidade=3, minima=10)

    hoje = datetime.utcnow().date().isoformat()
    r = client.get(f"/api/v1/relatorios/estoque?inicio={hoje}&fim={hoje}", headers=header)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["skus_ativos"] == 2
    # custo total = 100×1000 + 3×500 = 101500
    assert body["valor_custo_total"] == 101500
    # venda total = 100×2000 + 3×1000 = 203000
    assert body["valor_venda_total"] == 203000

    assert body["itens_abaixo_minimo"] == 1
    assert any(i["produto_id"] == prod_baixo for i in body["abaixo_minimo"])

    # nenhum vendeu → os dois estão parados; o de maior capital vem primeiro
    assert body["itens_parados"] == 2
    parados_ids = [p["produto_id"] for p in body["parados"]]
    assert parados_ids[0] == prod_parado  # 100000 > 1500
    parado = next(p for p in body["parados"] if p["produto_id"] == prod_parado)
    assert parado["valor_custo"] == 100000


# ---------------------------------------------------------------------------
# Fase 4b — OS-performance
# ---------------------------------------------------------------------------

def test_os_performance_throughput_reparo_e_tecnico(client, db_session):
    """2 OS finalizadas (1 REPARADO, 1 SEM_REPARO) + 1 aberta → métricas e por técnico."""
    header = _auth(client)
    cliente_id = _cliente(client, header)
    fp_id = _forma_pagamento(client, header)
    func_id = _funcionario(client, header)

    _os_finalizada(client, header, cliente_id, fp_id, "PERF-1", 100000, funcionario_id=func_id, situacao="REPARADO")
    _os_finalizada(client, header, cliente_id, fp_id, "PERF-2", 20000, funcionario_id=func_id, situacao="SEM_REPARO")
    _os_aberta(client, header, cliente_id, "PERF-3", funcionario_id=func_id)

    hoje = datetime.utcnow().date().isoformat()
    r = client.get(f"/api/v1/relatorios/os-performance?inicio={hoje}&fim={hoje}", headers=header)
    assert r.status_code == 200, r.text
    body = r.json()

    # Throughput: 3 criadas hoje (2 finalizadas + 1 aberta), 2 finalizadas.
    assert body["abertas"] == 3
    assert body["finalizadas"] == 2
    assert body["faturamento_total"] == 120000
    assert body["tempo_medio_horas"] is not None and body["tempo_medio_horas"] >= 0

    # Desfecho / taxa de reparo.
    assert body["reparo"]["reparado"] == 1
    assert body["reparo"]["sem_reparo"] == 1
    assert body["reparo"]["taxa_reparo_pct"] == 50.0

    # Por técnico.
    alvo = next((t for t in body["por_tecnico"] if t["funcionario_id"] == func_id), None)
    assert alvo is not None, body["por_tecnico"]
    assert alvo["finalizadas"] == 2
    assert alvo["faturamento"] == 120000

    # Snapshot por status: 2 FINALIZADA + 1 ABERTA no backlog.
    status_map = {s["status"]: s["quantidade"] for s in body["por_status"]}
    assert status_map.get("FINALIZADA") == 2
    assert status_map.get("ABERTA") == 1


# ---------------------------------------------------------------------------
# Recorte por perfil: o funcionario ve o que ELE fez; a loja e do dono.
# ---------------------------------------------------------------------------

def _funcionario_com_acesso(client, header, *, nome, cpf, email, senha, cargo_id=None):
    """Funcionario COM credencial de acesso — precisa logar para exercer o recorte."""
    payload = {
        "nome": nome, "cpf": cpf, "contato": "11999999999",
        "usuario": {"nome": nome, "email": email, "senha": senha},
        "endereco": [{"logradouro": "Rua X", "numero": "1", "cep": "12345-678",
                      "bairro": "Centro", "cidade": "Lab City", "estado": "SP"}],
    }
    r = client.post("/api/v1/funcionarios/", json=payload, headers=header)
    assert r.status_code in (200, 201), r.text
    func_id = r.json()["id"]
    if cargo_id is not None:
        lk = client.put(f"/api/v1/funcionarios/{func_id}/cargo?cargo_id={cargo_id}", headers=header)
        assert lk.status_code == 200, lk.text
    return func_id


def _login(client, email, senha):
    r = client.post("/api/v1/auth/login", data={
        "username": email, "password": senha, "hwid": "test-terminal-hwid",
    })
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _cargo_com_relatorio(client, header, nome="Vendedor Relatorio"):
    r = client.post("/api/v1/cargos/", json={
        "nome": nome, "permissoes": {"relatorio": True},
    }, headers=header)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def test_faturamento_do_funcionario_traz_so_o_que_ele_fez(client, db_session):
    """O funcionario ve o proprio faturamento; o do colega nao entra na conta.

    E as contas da LOJA (juros, CMV, lucro, formas de pagamento) ficam zeradas:
    quem garante isso e o recorte do backend, nao o `v-if` da tela.
    """
    _seed_contador_venda(db_session)
    header = _auth(client)
    fp_id = _forma_pagamento(client, header)
    # entrada=4000 garante CMV > 0 na visao do dono — e o contraste que prova
    # que o zero do funcionario e recorte, nao ausencia de dado.
    produto_id = _produto(client, header, "P-ESCOPO", varejo=10000, entrada=4000, quantidade=100)

    cargo_id = _cargo_com_relatorio(client, header)
    eu = _funcionario_com_acesso(
        client, header, nome="Vendedor Escopo", cpf="11122233355",
        email="escopo@empresa.com", senha="SenhaForte123!", cargo_id=cargo_id,
    )
    colega = _funcionario_com_acesso(
        client, header, nome="Colega Escopo", cpf="11122233366",
        email="colega@empresa.com", senha="SenhaForte123!",
    )

    _venda_finalizada(client, header, eu, produto_id, 1, fp_id)      # R$ 100,00
    _venda_finalizada(client, header, colega, produto_id, 3, fp_id)  # R$ 300,00

    hoje = datetime.utcnow().date().isoformat()
    rota = f"/api/v1/relatorios/faturamento?inicio={hoje}&fim={hoje}"

    # O dono continua vendo a loja inteira — guarda contra regressao.
    rm = client.get(rota, headers=header)
    assert rm.status_code == 200, rm.text
    dono = rm.json()
    assert dono["faturamento_total"] == 40000
    assert dono["qtd_vendas"] == 2
    assert dono["cmv"] > 0, "o dono precisa enxergar custo, senao o teste nao contrasta"

    # O funcionario ve so os R$ 100,00 dele.
    h_func = _login(client, "escopo@empresa.com", "SenhaForte123!")
    rf = client.get(rota, headers=h_func)
    assert rf.status_code == 200, rf.text
    meu = rf.json()
    assert meu["faturamento_total"] == 10000
    assert meu["faturamento_vendas"] == 10000
    assert meu["qtd_vendas"] == 1
    assert meu["ticket_medio"] == 10000

    # Contas da loja nao vazam para a tela dele.
    assert meu["cmv"] == 0
    assert meu["lucro_bruto"] == 0
    assert meu["margem_percentual"] == 0
    assert meu["juros_repassado"] == 0
    assert meu["juros_absorvido"] == 0
    assert meu["formas_pagamento"] == []
    # Sem juros a descontar, o liquido E o total — senao a tela mostraria R$ 0,00.
    assert meu["faturamento_liquido"] == 10000

    # A serie por dia tambem e a dele.
    assert sum(d["total_geral"] for d in meu["por_dia"]) == 10000


def test_relatorios_gerenciais_sao_exclusivos_do_master(client, db_session):
    """Ranking, comissoes, estoque e desempenho de OS respondem 403 a quem nao e Master.

    Sao os quatro que expoem colega, custo e imobilizado. A permissao do modulo
    nao basta: o cargo abaixo TEM 'relatorio' e mesmo assim leva 403.
    """
    header = _auth(client)
    cargo_id = _cargo_com_relatorio(client, header, nome="Vendedor Sem Visao Geral")
    _funcionario_com_acesso(
        client, header, nome="Vendedor Bloqueado", cpf="11122233377",
        email="bloqueado@empresa.com", senha="SenhaForte123!", cargo_id=cargo_id,
    )
    h_func = _login(client, "bloqueado@empresa.com", "SenhaForte123!")

    hoje = datetime.utcnow().date().isoformat()
    for nome in ("ranking-funcionarios", "comissoes", "estoque", "os-performance"):
        r = client.get(f"/api/v1/relatorios/{nome}?inicio={hoje}&fim={hoje}", headers=h_func)
        assert r.status_code == status.HTTP_403_FORBIDDEN, (nome, r.status_code, r.text)

    # E o dono continua entrando nos quatro.
    for nome in ("ranking-funcionarios", "comissoes", "estoque", "os-performance"):
        r = client.get(f"/api/v1/relatorios/{nome}?inicio={hoje}&fim={hoje}", headers=header)
        assert r.status_code == 200, (nome, r.text)
