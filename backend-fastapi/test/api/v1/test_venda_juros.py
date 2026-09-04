# ---------------------------------------------------------------------------
# Testes do juros no fechamento de venda: repassado ao cliente x absorvido
# pela loja. Espelham os equivalentes de OS em test_ordem_servico_oficina.py —
# os dois modulos precisam se comportar de forma identica.
# ---------------------------------------------------------------------------

from app.db.models.contador_venda import ContadorVenda

TEST_USER_EMAIL = "teste.juros@example.com"
TEST_USER_PASSWORD = "senhaSegura456"


def _seed_contador_venda(db_session):
    """Semeia o contador global de vendas (id=1) — normalmente feito no startup
    do app, que nao roda nos testes. Necessario para finalizar vendas."""
    if not db_session.query(ContadorVenda).first():
        db_session.add(ContadorVenda(id=1, proximo_numero=1))
        db_session.commit()


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
        "razao_social": "Empresa Juros 000199 LTDA", "nome_fantasia": "Juros", "is_cnpj": True,
        "documento": "12345678000195", "regime_tributario": "Simples Nacional",
        "celular": "11999998888", "segmento": "assistencia_tecnica",
        "endereco": [{"logradouro": "Av. Paulista", "numero": "1000", "bairro": "Bela Vista",
                      "cidade": "São Paulo", "estado": "SP", "cep": "01310-100"}],
    }
    r = client.post("/api/v1/empresas/", json=empresa, headers=header)
    assert r.status_code == 201, r.text
    return header


def _funcionario(client, header):
    r = client.post("/api/v1/funcionarios/", json={
        "nome": "Vendedor Teste", "cpf": "11122233396", "contato": "11999999999",
        "usuario": {"nome": "vendedor1", "email": "vend1@empresa.com", "senha": "SenhaForte123!"},
        "endereco": [{"logradouro": "Rua X", "numero": "1", "cep": "12345-678",
                      "bairro": "Centro", "cidade": "Lab City", "estado": "SP"}],
    }, headers=header)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _produto(client, header, codigo, varejo, quantidade=10):
    r = client.post("/api/v1/produtos/", json={
        "nome": f"Produto {codigo}", "codigo_produto": codigo, "unidade_medida": "UN",
        "estoque": {"valor_varejo": varejo, "quantidade": quantidade},
    }, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _forma_pagamento(client, header):
    r = client.post("/api/v1/formas-pagamento/", json={"nome": "Cartão de Crédito", "ativo": True}, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _venda_com_juros(client, header, funcionario_id, produto_id, fp_id, juros, responsavel):
    """Abre uma venda de 1 item e finaliza com um pagamento que carrega juros.

    Espelha o que o frontend monta: com CLIENTE o juros vem embutido no `valor`
    e soma no `acrescimo`; com LOJA o `valor` e so a base e o `acrescimo` fica
    zerado.
    """
    cv = client.post("/api/v1/vendas/", json={"funcionario_id": funcionario_id}, headers=header)
    assert cv.status_code == 201, cv.text
    venda_id = cv.json()["id"]

    add = client.post(f"/api/v1/vendas/{venda_id}/itens", json={
        "tipo_produto": "CADASTRADO", "produto_id": produto_id, "quantidade": 1,
    }, headers=header)
    assert add.status_code == 201, add.text
    base = add.json()["financeiro_atualizado"]["total"]

    repassa = responsavel == "CLIENTE"
    fin = client.post(f"/api/v1/vendas/{venda_id}/finalizar", json={
        "acrescimo": juros if repassa else 0,
        "pagamentos": [{
            "forma_pagamento_id": fp_id,
            "valor": base + juros if repassa else base,
            "juros_valor": juros,
            "juros_responsavel": responsavel,
            "parcelado": False,
            "qtd_parcelas": None,
            "bandeira_cartao": "VISA",
        }],
    }, headers=header)
    assert fin.status_code == 200, fin.text
    return base, fin.json()


def test_venda_juros_repassado_ao_cliente_sobe_o_total(client, db_session):
    """CLIENTE: o juros entra no acrescimo e o cliente paga a mais."""
    _seed_contador_venda(db_session)
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    produto_id = _produto(client, header, "P-JC", 10000)
    fp_id = _forma_pagamento(client, header)

    base, body = _venda_com_juros(client, header, funcionario_id, produto_id, fp_id, 500, "CLIENTE")

    assert body["acrescimo"] == 500
    assert body["total"] == base + 500, "total sobe com o juros repassado"
    pgto = body["pagamentos"][0]
    assert pgto["valor"] == base + 500, "o valor cobrado ja inclui o juros"
    assert pgto["juros_valor"] == 500
    assert pgto["juros_responsavel"] == "CLIENTE"


def test_venda_juros_absorvido_pela_loja_nao_sobe_o_total(client, db_session):
    """LOJA: o cliente paga o preco combinado; o juros fica registrado como
    custo e NAO pode inflar o total da venda."""
    _seed_contador_venda(db_session)
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    produto_id = _produto(client, header, "P-JL", 10000)
    fp_id = _forma_pagamento(client, header)

    base, body = _venda_com_juros(client, header, funcionario_id, produto_id, fp_id, 500, "LOJA")

    assert body["acrescimo"] == 0, "juros absorvido nao e acrescimo"
    assert body["total"] == base, "o cliente paga o preco combinado"
    pgto = body["pagamentos"][0]
    assert pgto["valor"] == base, "o valor cobrado NAO inclui o juros"
    assert pgto["juros_valor"] == 500, "mas o custo fica registrado"
    assert pgto["juros_responsavel"] == "LOJA"


def test_venda_pagamento_sem_juros_assume_cliente(client, db_session):
    """Retrocompatibilidade: payload antigo, sem os campos de juros, continua
    valido e e lido como CLIENTE com juros zero."""
    _seed_contador_venda(db_session)
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    produto_id = _produto(client, header, "P-JZ", 10000)
    fp_id = _forma_pagamento(client, header)

    cv = client.post("/api/v1/vendas/", json={"funcionario_id": funcionario_id}, headers=header)
    venda_id = cv.json()["id"]
    add = client.post(f"/api/v1/vendas/{venda_id}/itens", json={
        "tipo_produto": "CADASTRADO", "produto_id": produto_id, "quantidade": 1,
    }, headers=header)
    total = add.json()["financeiro_atualizado"]["total"]

    fin = client.post(f"/api/v1/vendas/{venda_id}/finalizar", json={
        "pagamentos": [{
            "forma_pagamento_id": fp_id, "valor": total,
            "parcelado": False, "qtd_parcelas": None,
        }],
    }, headers=header)
    assert fin.status_code == 200, fin.text

    pgto = fin.json()["pagamentos"][0]
    assert pgto["juros_valor"] == 0
    assert pgto["juros_responsavel"] == "CLIENTE"


# ---------------------------------------------------------------------------
# LIVRO-RAZAO UNICO DE ESTOQUE
#
# Antes, venda gravava em `logs_produto` e OS/cadastro/manual em
# `movimentacoes_estoque` — o historico de estoque nunca mostrava venda.
# Estes testes travam a convergencia: tudo num livro so, com `origem`.
# ---------------------------------------------------------------------------

def _movimentacoes(db_session, produto_id: int):
    from app.db.models.movimentacao_estoque import MovimentacaoEstoque
    db_session.expire_all()
    return (
        db_session.query(MovimentacaoEstoque)
        .filter(MovimentacaoEstoque.produto_id == produto_id)
        .order_by(MovimentacaoEstoque.id)
        .all()
    )


def test_venda_registra_no_livro_unico_com_origem_e_vinculo(client, db_session):
    """Venda passa a aparecer no historico de estoque, com origem VENDA e a FK
    da venda — antes ela so existia no logs_produto, que ninguem lia."""
    _seed_contador_venda(db_session)
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    produto_id = _produto(client, header, "P-LIVRO", 10000, quantidade=10)
    fp_id = _forma_pagamento(client, header)

    cv = client.post("/api/v1/vendas/", json={"funcionario_id": funcionario_id}, headers=header)
    venda_id = cv.json()["id"]
    add = client.post(f"/api/v1/vendas/{venda_id}/itens", json={
        "tipo_produto": "CADASTRADO", "produto_id": produto_id, "quantidade": 3,
    }, headers=header)
    total = add.json()["financeiro_atualizado"]["total"]
    fin = client.post(f"/api/v1/vendas/{venda_id}/finalizar", json={
        "pagamentos": [{"forma_pagamento_id": fp_id, "valor": total,
                        "parcelado": False, "qtd_parcelas": None}],
    }, headers=header)
    assert fin.status_code == 200, fin.text

    movs = _movimentacoes(db_session, produto_id)
    saidas = [m for m in movs if m.origem == "VENDA"]
    assert len(saidas) == 1, [(m.origem, m.tipo) for m in movs]
    assert saidas[0].venda_id == venda_id, "o vinculo com a venda e consultavel, nao texto"
    assert saidas[0].ordem_servico_id is None
    assert saidas[0].quantidade == 3
    assert saidas[0].quantidade_anterior == 10
    assert saidas[0].quantidade_posterior == 7


def test_cadastro_de_produto_marca_origem_cadastro(client, db_session):
    """Estoque inicial do cadastro nao pode se confundir com venda nem com
    ajuste manual no historico."""
    _seed_contador_venda(db_session)
    header = _auth(client)
    produto_id = _produto(client, header, "P-CAD", 10000, quantidade=5)

    movs = _movimentacoes(db_session, produto_id)
    assert len(movs) == 1
    assert movs[0].origem == "CADASTRO"
    assert movs[0].venda_id is None and movs[0].ordem_servico_id is None


def test_venda_nao_escreve_mais_no_livro_legado(client, db_session):
    """`logs_produto` esta aposentada: nenhuma linha nova deve ser criada."""
    from app.db.models.log_produto import LogProduto

    _seed_contador_venda(db_session)
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    produto_id = _produto(client, header, "P-LEG", 10000, quantidade=10)
    fp_id = _forma_pagamento(client, header)

    cv = client.post("/api/v1/vendas/", json={"funcionario_id": funcionario_id}, headers=header)
    venda_id = cv.json()["id"]
    add = client.post(f"/api/v1/vendas/{venda_id}/itens", json={
        "tipo_produto": "CADASTRADO", "produto_id": produto_id, "quantidade": 1,
    }, headers=header)
    total = add.json()["financeiro_atualizado"]["total"]
    client.post(f"/api/v1/vendas/{venda_id}/finalizar", json={
        "pagamentos": [{"forma_pagamento_id": fp_id, "valor": total,
                        "parcelado": False, "qtd_parcelas": None}],
    }, headers=header)

    db_session.expire_all()
    assert db_session.query(LogProduto).count() == 0
