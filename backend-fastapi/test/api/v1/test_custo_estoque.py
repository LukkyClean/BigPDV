# ---------------------------------------------------------------------------
# ARQUIVO: test_custo_estoque.py
# DESCRICAO: Livro de estoque como fonte unica da quantidade E do custo.
#
#   Fase 0 — integridade do livro: toda alteracao de quantidade passa pelo
#            registro central e deixa rastro. Antes existiam cinco caminhos de
#            escrita, e um deles trocava a quantidade sem gravar nada.
#   Fase 1 — custo: media ponderada na compra, custo congelado na saida.
#   Fase 2 — CMV e lucro no relatorio de faturamento.
# ---------------------------------------------------------------------------

import pytest
from starlette import status

from app.db.models.contador_venda import ContadorVenda
from app.services.movimentacao_estoque import calcular_custo_medio


TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"


# =========================
# Helpers
# =========================

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


def _seed_contador_venda(db_session):
    if not db_session.query(ContadorVenda).first():
        db_session.add(ContadorVenda(id=1, proximo_numero=1))
        db_session.commit()


def _produto(client, header, codigo, varejo, entrada=None, quantidade=0):
    estoque = {"valor_varejo": varejo, "quantidade": quantidade}
    if entrada is not None:
        estoque["valor_entrada"] = entrada
    r = client.post("/api/v1/produtos/", json={
        "nome": f"Produto {codigo}", "codigo_produto": codigo,
        "unidade_medida": "UN", "estoque": estoque,
    }, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _movimentar(client, header, produto_id, tipo, quantidade, custo_unitario=None, observacao=None):
    payload = {"tipo": tipo, "quantidade": quantidade}
    if custo_unitario is not None:
        payload["custo_unitario"] = custo_unitario
    if observacao is not None:
        payload["observacao"] = observacao
    return client.post(f"/api/v1/produtos/{produto_id}/movimentacoes", json=payload, headers=header)


def _movimentacoes(client, header, produto_id):
    r = client.get("/api/v1/produtos/movimentacoes", params={"produto_id": produto_id}, headers=header)
    assert r.status_code == 200, r.text
    # Ordena por id: dentro do mesmo segundo o created_at empata e a ordem do
    # crud vira loteria. O id e a unica ordem cronologica confiavel aqui.
    return sorted(r.json(), key=lambda m: m["id"])


def _estoque(db_session, produto_id):
    """Estado do estoque direto do banco — nao ha GET /produtos/{id} na API."""
    from app.db.models.estoque import Estoque

    db_session.expire_all()  # a escrita veio de outra sessao (a do TestClient)
    return db_session.get(Estoque, produto_id)


def _funcionario(client, header):
    r = client.post("/api/v1/funcionarios/", json={
        "nome": "Vendedor Teste", "cpf": "11122233396", "contato": "11999999999",
        "usuario": {"nome": "vendedor1", "email": "vend1@empresa.com", "senha": "SenhaForte123!"},
        "endereco": [{"logradouro": "Rua X", "numero": "1", "cep": "12345-678",
                      "bairro": "Centro", "cidade": "Lab City", "estado": "SP"}],
    }, headers=header)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _forma_pagamento(client, header):
    r = client.post("/api/v1/formas-pagamento/", json={"nome": "Dinheiro", "ativo": True}, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _venda_finalizada(client, header, funcionario_id, produto_id, quantidade, fp_id):
    cv = client.post("/api/v1/vendas/", json={"funcionario_id": funcionario_id}, headers=header)
    assert cv.status_code == 201, cv.text
    venda_id = cv.json()["id"]
    add = client.post(f"/api/v1/vendas/{venda_id}/itens", json={
        "tipo_produto": "CADASTRADO", "produto_id": produto_id, "quantidade": quantidade,
    }, headers=header)
    assert add.status_code == 201, add.text
    total = add.json()["financeiro_atualizado"]["total"]
    fin = client.post(f"/api/v1/vendas/{venda_id}/finalizar", json={
        "pagamentos": [{"forma_pagamento_id": fp_id, "valor": total,
                        "parcelado": False, "qtd_parcelas": None}],
    }, headers=header)
    assert fin.status_code == 200, fin.text
    return venda_id, total


def _faturamento(client, header):
    from datetime import date
    hoje = date.today().isoformat()
    r = client.get("/api/v1/relatorios/faturamento", params={"inicio": hoje, "fim": hoje}, headers=header)
    assert r.status_code == 200, r.text
    return r.json()


# ===========================================================================
# FASE 0 — o livro nao pode ter buraco
# ===========================================================================

def test_estoque_inicial_entra_pelo_livro_sem_dobrar(client, db_session):
    """A quantidade inicial do cadastro entra como ENTRADA (0 -> N).

    O estoque nasce zerado e a movimentacao e quem o preenche. Se a quantidade
    ja viesse gravada no cadastro, a ENTRADA somaria em cima e o produto
    comecaria com o dobro.
    """
    header = _auth(client)
    produto_id = _produto(client, header, "P-INI", varejo=15000, entrada=4000, quantidade=5)

    assert _estoque(db_session, produto_id).quantidade == 5

    movs = _movimentacoes(client, header, produto_id)
    assert len(movs) == 1, movs
    assert movs[0]["tipo"] == "ENTRADA"
    assert movs[0]["quantidade_anterior"] == 0
    assert movs[0]["quantidade_posterior"] == 5
    assert movs[0]["custo_unitario"] == 4000


def test_edicao_de_quantidade_no_cadastro_vira_ajuste_no_livro(client, db_session):
    """Corrigir a quantidade pela tela de produto e uma CONTAGEM, e tem que
    aparecer no livro com o antes e o depois.

    Este era o buraco: a edicao gravava `estoque.quantidade` direto e registrava
    so um EDICAO_DADOS com anterior == posterior. As unidades sumiam sem deixar
    quantas eram nem quando foi.
    """
    header = _auth(client)
    produto_id = _produto(client, header, "P-EDIT", varejo=15000, entrada=4000, quantidade=10)

    r = client.put(f"/api/v1/produtos/{produto_id}", json={"estoque": {"quantidade": 3}}, headers=header)
    assert r.status_code == 200, r.text

    assert _estoque(db_session, produto_id).quantidade == 3

    ajustes = [m for m in _movimentacoes(client, header, produto_id) if m["tipo"] == "AJUSTE"]
    assert len(ajustes) == 1, _movimentacoes(client, header, produto_id)
    assert ajustes[0]["quantidade_anterior"] == 10
    assert ajustes[0]["quantidade_posterior"] == 3
    assert ajustes[0]["quantidade"] == 7, "o livro precisa dizer QUANTAS unidades sumiram"


def test_edicao_sem_mexer_na_quantidade_nao_gera_ajuste(client, db_session):
    """Trocar so o preco nao e contagem: gera EDICAO_DADOS, nunca AJUSTE."""
    header = _auth(client)
    produto_id = _produto(client, header, "P-PRECO", varejo=15000, entrada=4000, quantidade=10)

    r = client.put(f"/api/v1/produtos/{produto_id}", json={"estoque": {"valor_varejo": 17000}}, headers=header)
    assert r.status_code == 200, r.text

    movs = _movimentacoes(client, header, produto_id)
    assert [m["tipo"] for m in movs] == ["ENTRADA", "EDICAO_DADOS"], movs
    assert movs[-1]["quantidade_anterior"] == movs[-1]["quantidade_posterior"] == 10


def test_movimentacao_manual_passa_pelo_registro_central(client, db_session):
    """A movimentacao manual do endpoint nao pode ter logica propria de
    quantidade — com duas copias, a entrada manual deixaria de recalcular a
    media e o custo iria drenando sem erro nenhum aparecer."""
    header = _auth(client)
    produto_id = _produto(client, header, "P-MAN", varejo=15000, entrada=4000, quantidade=2)

    r = _movimentar(client, header, produto_id, "ENTRADA", 3, custo_unitario=4000)
    assert r.status_code == 201, r.text
    assert r.json()["quantidade_anterior"] == 2
    assert r.json()["quantidade_posterior"] == 5
    assert _estoque(db_session, produto_id).quantidade == 5


def test_ajuste_manual_recebe_a_quantidade_final_contada(client, db_session):
    """No AJUSTE, `quantidade` e o total contado na prateleira, nao a diferenca."""
    header = _auth(client)
    produto_id = _produto(client, header, "P-AJU", varejo=15000, entrada=4000, quantidade=10)

    r = _movimentar(client, header, produto_id, "AJUSTE", 4, observacao="Contagem")
    assert r.status_code == 201, r.text
    assert r.json()["quantidade_posterior"] == 4
    assert r.json()["quantidade"] == 6
    assert _estoque(db_session, produto_id).quantidade == 4


def test_saida_manual_sem_estoque_e_recusada(client, db_session):
    """Regra preservada: fora da OS, saida sem estoque e recusada."""
    header = _auth(client)
    produto_id = _produto(client, header, "P-NEG", varejo=15000, entrada=4000, quantidade=1)

    r = _movimentar(client, header, produto_id, "SAIDA", 5)
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, r.text


def test_produto_nao_tem_delete_fisico(client, db_session):
    """GUARDA do ON DELETE CASCADE de movimentacoes_estoque.

    Enquanto a exclusao de produto for logica (`ativo`), o CASCADE nunca dispara
    e o livro esta a salvo. No dia em que alguem criar um delete fisico, o
    historico de estoque — e o lucro ja apurado — some junto. Este teste falha
    antes disso acontecer.
    """
    import inspect
    from app.db.crud import produto as produto_crud
    from app.api.v1.endpoints import produto as produto_endpoint

    fonte_crud = inspect.getsource(produto_crud)
    assert "db.delete(produto" not in fonte_crud, (
        "delete fisico de produto apagaria o livro de estoque junto (FK CASCADE)"
    )

    rotas_delete = [
        rota.path
        for rota in produto_endpoint.router.routes
        if "DELETE" in getattr(rota, "methods", set())
    ]
    assert rotas_delete == ["/fotos/{image_id}"], rotas_delete


# ===========================================================================
# FASE 1 — custo medio ponderado e congelamento
# ===========================================================================

@pytest.mark.parametrize(
    "qtd_ant, custo_ant, qtd_ent, custo_ent, esperado",
    [
        (3, 4000, 2, 6000, 4800),   # 3 a 40 + 2 a 60 -> 48
        (0, None, 5, 4000, 4000),   # primeira compra define o custo
        (5, None, 5, 6000, 6000),   # sem custo anterior conhecido, vale a compra
        (-2, 4000, 3, 6000, 6000),  # saldo negativo nao pondera (senao daria 100)
    ],
)
def test_calcular_custo_medio(qtd_ant, custo_ant, qtd_ent, custo_ent, esperado):
    """Saldo negativo e divida de contagem, nao estoque avaliavel: ponderar por
    ele produziria um custo MAIOR que o preco pago."""
    assert calcular_custo_medio(
        quantidade_anterior=qtd_ant,
        custo_anterior=custo_ant,
        quantidade_entrada=qtd_ent,
        custo_entrada=custo_ent,
    ) == esperado


def test_segunda_compra_recalcula_a_media(client, db_session):
    """3 unidades a 40 + 2 a 60 -> media 48, e nao 60."""
    header = _auth(client)
    produto_id = _produto(client, header, "P-MED", varejo=15000, entrada=4000, quantidade=3)

    r = _movimentar(client, header, produto_id, "ENTRADA", 2, custo_unitario=6000)
    assert r.status_code == 201, r.text

    estoque = _estoque(db_session, produto_id)
    assert estoque.custo_medio == 4800
    assert estoque.valor_entrada == 4000, "preco de referencia do cadastro nao e mexido sozinho"


def test_saida_congela_o_custo_do_dia(client, db_session):
    """O custo gravado na saida nao pode mudar depois.

    E o coracao de tudo: comprar mais caro amanha nao pode reescrever o lucro da
    venda de hoje.
    """
    header = _auth(client)
    produto_id = _produto(client, header, "P-CONG", varejo=15000, entrada=4000, quantidade=10)

    saida = _movimentar(client, header, produto_id, "SAIDA", 2, observacao="Perda")
    assert saida.status_code == 201, saida.text
    assert saida.json()["custo_unitario"] == 4000

    # Fornecedor reajustou e a loja comprou mais caro.
    assert _movimentar(client, header, produto_id, "ENTRADA", 8, custo_unitario=9000).status_code == 201
    assert _estoque(db_session, produto_id).custo_medio > 4000

    congelada = [m for m in _movimentacoes(client, header, produto_id) if m["id"] == saida.json()["id"]][0]
    assert congelada["custo_unitario"] == 4000, "o passado nao pode ser reescrito"


def test_devolucao_nao_altera_a_media(client, db_session):
    """ENTRADA sem valor pago e devolucao, nao compra: a media fica intacta e o
    movimento leva a media corrente, para o CMV se anular contra a saida."""
    header = _auth(client)
    produto_id = _produto(client, header, "P-DEV", varejo=15000, entrada=4000, quantidade=5)

    r = _movimentar(client, header, produto_id, "ENTRADA", 5, observacao="Devolucao")
    assert r.status_code == 201, r.text
    assert r.json()["custo_unitario"] == 4000
    assert _estoque(db_session, produto_id).custo_medio in (None, 4000)


def test_ajuste_nao_altera_a_media(client, db_session):
    """Contagem nao e compra: sobra de inventario nao pode baratear o estoque."""
    header = _auth(client)
    produto_id = _produto(client, header, "P-AJM", varejo=15000, entrada=4000, quantidade=3)
    _movimentar(client, header, produto_id, "ENTRADA", 2, custo_unitario=6000)
    media_antes = _estoque(db_session, produto_id).custo_medio

    assert _movimentar(client, header, produto_id, "AJUSTE", 20).status_code == 201

    assert _estoque(db_session, produto_id).custo_medio == media_antes


def test_produto_legado_sem_media_cai_no_preco_de_custo(client, db_session):
    """Produto cadastrado sem custo informado nao inventa media; quando o custo
    e preenchido depois, a saida usa esse valor como melhor palpite."""
    header = _auth(client)
    produto_id = _produto(client, header, "P-LEG", varejo=15000, quantidade=5)
    assert _estoque(db_session, produto_id).custo_medio is None

    r = client.put(f"/api/v1/produtos/{produto_id}", json={"estoque": {"valor_entrada": 3000}}, headers=header)
    assert r.status_code == 200, r.text

    saida = _movimentar(client, header, produto_id, "SAIDA", 1)
    assert saida.json()["custo_unitario"] == 3000


# ===========================================================================
# FASE 2 — CMV e lucro no relatorio
# ===========================================================================

def test_lucro_desconta_o_custo_da_peca(client, db_session):
    """O caso da loja: vendeu por 150, a peca custou 40 -> sobrou 110.

    Antes o relatorio so mostrava os 150.
    """
    _seed_contador_venda(db_session)
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma_pagamento(client, header)
    produto_id = _produto(client, header, "P-LUC", varejo=15000, entrada=4000, quantidade=10)

    _venda_finalizada(client, header, funcionario_id, produto_id, 1, fp_id)

    rel = _faturamento(client, header)
    assert rel["faturamento_total"] == 15000
    assert rel["cmv"] == 4000
    assert rel["lucro_bruto"] == 11000
    assert rel["margem_percentual"] == pytest.approx(73.33, abs=0.01)
    assert rel["saidas_sem_custo"] == 0


def test_venda_cancelada_devolve_o_custo_ao_cmv(client, db_session):
    """Estorno entra como credito: a peca voltou, o custo dela sai do CMV.

    E o que o congelamento no livro da de graca — sem isso, cada cancelamento
    viraria lucro fantasma que alguem teria que caçar na mao.
    """
    _seed_contador_venda(db_session)
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma_pagamento(client, header)
    produto_id = _produto(client, header, "P-CANC", varejo=15000, entrada=4000, quantidade=10)

    venda_id, _ = _venda_finalizada(client, header, funcionario_id, produto_id, 2, fp_id)
    assert _faturamento(client, header)["cmv"] == 8000

    cancel = client.post(f"/api/v1/vendas/{venda_id}/cancelar", json={"motivo": "cliente desistiu da compra"}, headers=header)
    assert cancel.status_code == 200, cancel.text

    rel = _faturamento(client, header)
    assert rel["cmv"] == 0, "a peca voltou para a prateleira"
    assert rel["faturamento_total"] == 0


def test_relatorio_avisa_quando_ha_saida_sem_custo(client, db_session):
    """Movimentacao sem custo apurado (dado legado) nao vira lucro inventado:
    entra como zero no CMV e o contador denuncia que o lucro esta subestimado."""
    from app.db.models.movimentacao_estoque import MovimentacaoEstoque

    _seed_contador_venda(db_session)
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma_pagamento(client, header)
    produto_id = _produto(client, header, "P-SEM", varejo=15000, entrada=4000, quantidade=10)

    _venda_finalizada(client, header, funcionario_id, produto_id, 1, fp_id)

    # Simula a linha legada: existe no livro, mas sem custo gravado.
    mov = (
        db_session.query(MovimentacaoEstoque)
        .filter(MovimentacaoEstoque.produto_id == produto_id, MovimentacaoEstoque.tipo == "SAIDA")
        .first()
    )
    mov.custo_unitario = None
    db_session.commit()

    rel = _faturamento(client, header)
    assert rel["cmv"] == 0
    assert rel["saidas_sem_custo"] == 1
    assert rel["lucro_bruto"] == rel["faturamento_liquido"], "sem custo apurado, o lucro fica inflado"


# ===========================================================================
# CUSTO NA OS SEM CADASTRAR PECA + SIGILO NA VIA DO CLIENTE
# ===========================================================================

def _cliente(client, header):
    r = client.post("/api/v1/clientes/cliente_pf", json={
        "nome": "João Pedro Silva", "cpf": "98765432100", "tipo": "PF", "celular": "11987654321",
        "endereco": [{"logradouro": "Rua das Flores", "numero": "100", "bairro": "Centro",
                      "cidade": "Campinas", "estado": "SP", "cep": "13010-000"}],
    }, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _os_com_itens(client, header, cliente_id, serie, itens):
    r = client.post("/api/v1/ordens-servico/", json={
        "cliente_id": cliente_id, "prioridade": "NORMAL", "defeito_relatado": "Nao carrega",
        "dados_adicionais": {},
        "objeto": {"marca": "Samsung", "modelo": "A20", "numero_serie": serie, "dados_adicionais": {}},
        "itens": itens,
    }, headers=header)
    return r


def _servico(nome, valor, **extra):
    base = {"tipo": "SERVICO", "nome": nome, "unidade_medida": "UN",
            "quantidade": 1, "valor_unitario": valor}
    base.update(extra)
    return base


def test_custo_declarado_na_os_entra_no_lucro(client, db_session):
    """O caso real da oficina: lanca so o servico de R$ 150, sem cadastrar peca,
    mas declara que gastou R$ 40 — e o relatorio fecha em R$ 110."""
    header = _auth(client)
    cliente_id = _cliente(client, header)
    fp_id = _forma_pagamento(client, header)

    r = _os_com_itens(client, header, cliente_id, "SN-CUSTO",
                      [_servico("Troca de conector de carga", 15000, custo_unitario=4000)])
    assert r.status_code == status.HTTP_201_CREATED, r.text
    numero = r.json()["numero_os"]

    fin = client.put(f"/api/v1/ordens-servico/{numero}/finalizar", json={
        "situacao_equipamento": "REPARADO", "garantia": "90 dias",
        "pagamentos": [{"forma_pagamento_id": fp_id, "valor": 15000}],
    }, headers=header)
    assert fin.status_code == 200, fin.text

    rel = _faturamento(client, header)
    assert rel["faturamento_total"] == 15000
    assert rel["cmv"] == 4000, "o gasto declarado precisa pesar no custo"
    assert rel["lucro_bruto"] == 11000


def test_custo_declarado_nunca_vai_para_o_cliente(client, db_session):
    """GUARDA DE SIGILO: o custo é interno. Se algum dia ele passar a sair na
    resposta que alimenta as vias impressas, este teste cai."""
    header = _auth(client)
    cliente_id = _cliente(client, header)

    r = _os_com_itens(client, header, cliente_id, "SN-SIGILO",
                      [_servico("Troca de tela", 30000, custo_unitario=12000)])
    assert r.status_code == status.HTTP_201_CREATED, r.text
    item = r.json()["itens"][0]

    # O valor cobrado sai; o valor pago pela peca e so numero interno.
    assert item["valor_unitario"] == 30000
    assert item["custo_unitario"] == 12000, "a loja precisa ler o proprio custo"
    # A prova de sigilo mora no frontend (nenhum template imprime custo_unitario);
    # aqui garantimos que o campo esta separado do valor cobrado e nao o polui.
    assert item["valor_total"] == 30000, "custo nao pode vazar para o total cobrado"


def test_item_reprovado_nao_gera_custo(client, db_session):
    """Cliente recusou: o servico nao foi feito e o gasto nao aconteceu."""
    header = _auth(client)
    cliente_id = _cliente(client, header)
    fp_id = _forma_pagamento(client, header)

    r = _os_com_itens(client, header, cliente_id, "SN-REPROV", [
        _servico("Troca de tela", 30000, custo_unitario=12000, status_aprovacao="REPROVADO"),
        _servico("Limpeza", 5000, custo_unitario=1000),
    ])
    assert r.status_code == status.HTTP_201_CREATED, r.text
    numero = r.json()["numero_os"]

    fin = client.put(f"/api/v1/ordens-servico/{numero}/finalizar", json={
        "situacao_equipamento": "REPARADO", "garantia": "90 dias",
        "pagamentos": [{"forma_pagamento_id": fp_id, "valor": 5000}],
    }, headers=header)
    assert fin.status_code == 200, fin.text

    assert _faturamento(client, header)["cmv"] == 1000


def test_peca_embutida_vale_zero_e_fica_fora_da_via(client, db_session):
    """Peca embutida sai do estoque e entra no custo, mas nao e listada.

    O valor zero e obrigatorio: as vias imprimem as linhas visiveis E o total da
    OS, entao uma linha escondida com valor faria o documento do cliente nao
    fechar — pior do que ver a peca.
    """
    header = _auth(client)
    cliente_id = _cliente(client, header)
    produto_id = _produto(client, header, "P-EMB", varejo=8000, entrada=4000, quantidade=10)

    r = _os_com_itens(client, header, cliente_id, "SN-EMB", [
        _servico("Troca de conector", 15000),
        {"tipo": "PRODUTO", "nome": "Conector de carga", "unidade_medida": "UN",
         "quantidade": 1, "valor_unitario": 0, "visivel_cliente": False, "item_id": produto_id},
    ])
    assert r.status_code == status.HTTP_201_CREATED, r.text
    body = r.json()

    embutida = [i for i in body["itens"] if not i["visivel_cliente"]]
    assert len(embutida) == 1
    assert embutida[0]["valor_total"] == 0
    assert body["valor_total"] == 15000, "o cliente paga so o servico"


def test_peca_embutida_com_valor_e_recusada(client, db_session):
    """Sem esta trava, a via impressa listaria linhas que nao somam o total."""
    header = _auth(client)
    cliente_id = _cliente(client, header)

    r = _os_com_itens(client, header, cliente_id, "SN-EMB2", [
        {"tipo": "PRODUTO", "nome": "Conector", "unidade_medida": "UN",
         "quantidade": 1, "valor_unitario": 4000, "visivel_cliente": False},
    ])
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, r.text


def test_item_cobrado_nao_pode_valer_zero(client, db_session):
    """Regra antiga preservada: linha visivel com valor zero nao faz sentido."""
    header = _auth(client)
    cliente_id = _cliente(client, header)

    r = _os_com_itens(client, header, cliente_id, "SN-ZERO",
                      [_servico("Servico de graca", 0)])
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, r.text


def test_peca_do_catalogo_nao_conta_custo_duas_vezes(client, db_session):
    """Item COM produto_id tira custo do livro de estoque. Se o custo declarado
    a mao tambem contasse, o CMV dobraria."""
    header = _auth(client)
    cliente_id = _cliente(client, header)
    fp_id = _forma_pagamento(client, header)
    produto_id = _produto(client, header, "P-DUP", varejo=8000, entrada=4000, quantidade=10)

    r = _os_com_itens(client, header, cliente_id, "SN-DUP", [
        {"tipo": "PRODUTO", "nome": "Conector", "unidade_medida": "UN", "quantidade": 1,
         "valor_unitario": 8000, "custo_unitario": 4000, "item_id": produto_id},
    ])
    assert r.status_code == status.HTTP_201_CREATED, r.text
    numero = r.json()["numero_os"]

    fin = client.put(f"/api/v1/ordens-servico/{numero}/finalizar", json={
        "situacao_equipamento": "REPARADO", "garantia": "90 dias",
        "pagamentos": [{"forma_pagamento_id": fp_id, "valor": 8000}],
    }, headers=header)
    assert fin.status_code == 200, fin.text

    assert _faturamento(client, header)["cmv"] == 4000, "conta uma vez so, pelo livro"


# ===========================================================================
# VENDA — item avulso (nao passa pelo estoque)
# ===========================================================================

def _venda_com_avulso(client, header, funcionario_id, fp_id, descricao, valor, custo=None, quantidade=1):
    """Cria venda -> adiciona item AVULSO -> finaliza."""
    cv = client.post("/api/v1/vendas/", json={"funcionario_id": funcionario_id}, headers=header)
    assert cv.status_code == 201, cv.text
    venda_id = cv.json()["id"]

    payload = {
        "tipo_produto": "AVULSO", "descricao_avulsa": descricao,
        "valor_unitario": valor, "quantidade": quantidade,
    }
    if custo is not None:
        payload["custo_unitario"] = custo
    add = client.post(f"/api/v1/vendas/{venda_id}/itens", json=payload, headers=header)
    assert add.status_code == 201, add.text

    total = add.json()["financeiro_atualizado"]["total"]
    fin = client.post(f"/api/v1/vendas/{venda_id}/finalizar", json={
        "pagamentos": [{"forma_pagamento_id": fp_id, "valor": total,
                        "parcelado": False, "qtd_parcelas": None}],
    }, headers=header)
    assert fin.status_code == 200, fin.text
    return venda_id, add.json()["produto_adicionado"]


def test_avulso_com_custo_entra_no_lucro(client, db_session):
    """Item avulso nao movimenta estoque, entao o custo dele so existe se for
    declarado. Sem isso ele entrava no relatorio como receita pura."""
    _seed_contador_venda(db_session)
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma_pagamento(client, header)

    _venda_com_avulso(client, header, funcionario_id, fp_id, "Cabo HDMI", valor=8000, custo=3000)

    rel = _faturamento(client, header)
    assert rel["faturamento_total"] == 8000
    assert rel["cmv"] == 3000
    assert rel["lucro_bruto"] == 5000


def test_avulso_sem_custo_nao_inventa_custo(client, db_session):
    """Nao declarar custo significa "nao sei", nao "custou zero" — mas o efeito
    no relatorio e lucro inflado. Documentado aqui de proposito."""
    _seed_contador_venda(db_session)
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma_pagamento(client, header)

    _venda_com_avulso(client, header, funcionario_id, fp_id, "Cabo sem custo", valor=8000)

    rel = _faturamento(client, header)
    assert rel["cmv"] == 0
    assert rel["lucro_bruto"] == 8000


def test_avulso_custo_e_interno_e_separado_do_preco(client, db_session):
    """GUARDA DE SIGILO: o custo nao pode contaminar o que o cliente ve."""
    _seed_contador_venda(db_session)
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma_pagamento(client, header)

    _, item = _venda_com_avulso(client, header, funcionario_id, fp_id, "Cabo", valor=8000, custo=3000)

    assert item["valor_unitario"] == 8000
    assert item["custo_unitario"] == 3000, "a loja precisa ler o proprio custo"
    assert item["subtotal"] == 8000, "custo nao entra no que o cliente paga"
    assert item["total"] == 8000


def test_produto_cadastrado_recusa_custo_manual(client, db_session):
    """Com produto do catalogo quem manda e o livro de estoque. Aceitar um custo
    manual aqui criaria dois numeros para a mesma peca — e o CMV somaria os dois."""
    _seed_contador_venda(db_session)
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    produto_id = _produto(client, header, "P-CAD", varejo=8000, entrada=3000, quantidade=5)

    cv = client.post("/api/v1/vendas/", json={"funcionario_id": funcionario_id}, headers=header)
    venda_id = cv.json()["id"]

    r = client.post(f"/api/v1/vendas/{venda_id}/itens", json={
        "tipo_produto": "CADASTRADO", "produto_id": produto_id,
        "quantidade": 1, "custo_unitario": 3000,
    }, headers=header)
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, r.text
