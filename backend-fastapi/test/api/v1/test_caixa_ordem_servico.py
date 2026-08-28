# ---------------------------------------------------------------------------
# A OS no livro do dinheiro.
#
# O fechamento de caixa sempre SOMOU a origem ORDEM_SERVICO
# (crud/sessao_caixa.py), mas nada nunca escreveu com ela: havia leitor sem
# escritor. Numa loja com o caixa ligado, receber uma OS em dinheiro enchia a
# gaveta sem o sistema saber, e o turno fechava com SOBRA todo dia.
#
# O PRIMEIRO teste deste arquivo e o mais importante: com o caixa DESLIGADO --
# o padrao, e o estado das lojas em producao -- finalizar uma OS tem que gravar
# exatamente o que gravava antes, e o livro tem que ficar VAZIO. Se ele falhar,
# a mudanca deixou de ser aditiva e nao pode ir para a loja.
# ---------------------------------------------------------------------------

from datetime import date, timedelta

from starlette import status

from app.db.models.configuracao_vendas import ConfiguracaoVendas
from app.db.models.movimentacao_financeira import MovimentacaoFinanceira
from app.db.models.ordem_servico_pagamento import OrdemServicoPagamento

TEST_USER_EMAIL = "os.caixa@example.com"
TEST_USER_PASSWORD = "senhaSegura321"


# ===========================================================================
# HELPERS
# ===========================================================================

def _auth(client):
    client.post("/api/v1/usuarios/", json={
        "nome": "Dono da Oficina", "email": TEST_USER_EMAIL, "senha": TEST_USER_PASSWORD,
    })
    login = client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": "hwid-os-caixa",
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post("/api/v1/empresas/", json={
        "razao_social": "Oficina Caixa LTDA", "nome_fantasia": "Oficina", "is_cnpj": True,
        "documento": "12345678000177", "regime_tributario": "Simples Nacional",
        "celular": "11999996666", "segmento": "assistencia_tecnica",
        "endereco": [{"logradouro": "Rua A", "numero": "10", "bairro": "Centro",
                      "cidade": "São Paulo", "estado": "SP", "cep": "01310-100"}],
    }, headers=header)
    return header


def _config_caixa(db_session, **flags):
    cfg = db_session.query(ConfiguracaoVendas).first()
    if not cfg:
        cfg = ConfiguracaoVendas(empresa_id=1)
        db_session.add(cfg)
    for chave, valor in flags.items():
        setattr(cfg, chave, valor)
    db_session.commit()
    return cfg


def _funcionario(client, header):
    r = client.post("/api/v1/funcionarios/", json={
        "nome": "Tecnico", "cpf": "11122233355", "contato": "11999999999",
        "usuario": {"nome": "tec", "email": "tec@empresa.com", "senha": "SenhaForte123!"},
        "endereco": [{"logradouro": "Rua X", "numero": "1", "cep": "12345-678",
                      "bairro": "Centro", "cidade": "Lab City", "estado": "SP"}],
    }, headers=header)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _forma(client, header, nome="Dinheiro"):
    r = client.post("/api/v1/formas-pagamento/", json={"nome": nome, "ativo": True},
                    headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _cliente(client, header):
    r = client.post("/api/v1/clientes/cliente_pf", json={
        "nome": "Cliente OS", "cpf": "98765432199", "tipo": "PF", "celular": "11988887777",
        "endereco": [{"logradouro": "Rua Y", "numero": "10", "bairro": "Centro",
                      "cidade": "Campinas", "estado": "SP", "cep": "13010-000"}],
    }, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _abrir_caixa(client, header, saldo=10000):
    r = client.post("/api/v1/caixa/abrir", json={"saldo_inicial": saldo}, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text


def _criar_os(client, header, cliente_id, funcionario_id, serie, valor):
    r = client.post("/api/v1/ordens-servico/", json={
        "cliente_id": cliente_id, "prioridade": "NORMAL", "defeito_relatado": "Não liga",
        "dados_adicionais": {}, "funcionario_id": funcionario_id,
        "objeto": {"marca": "Dell", "modelo": "Inspiron", "numero_serie": serie,
                   "dados_adicionais": {}},
        "itens": [{"tipo": "SERVICO", "nome": "Reparo", "unidade_medida": "UN",
                   "quantidade": 1, "valor_unitario": valor}],
    }, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    return r.json()["numero_os"]


def _finalizar(client, header, numero, fp_id, valor, vencimento=None):
    pagamento = {"forma_pagamento_id": fp_id, "valor": valor}
    if vencimento:
        pagamento["vencimento"] = vencimento.isoformat()
    r = client.put(f"/api/v1/ordens-servico/{numero}/finalizar", json={
        "situacao_equipamento": "REPARADO", "garantia": "90 dias",
        "pagamentos": [pagamento],
    }, headers=header)
    assert r.status_code == 200, r.text
    return r.json()


def _cenario(client, header, db_session, valor=15000, caixa_ligado=True):
    _config_caixa(db_session, controlar_caixa=caixa_ligado)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)
    cliente_id = _cliente(client, header)
    if caixa_ligado:
        _abrir_caixa(client, header)
    return funcionario_id, fp_id, cliente_id


def _movimentos_de_os(db_session):
    return (
        db_session.query(MovimentacaoFinanceira)
        .filter(MovimentacaoFinanceira.origem == "ORDEM_SERVICO")
        .order_by(MovimentacaoFinanceira.id)
        .all()
    )


# ===========================================================================
# INÉRCIA — o teste que precisa passar para a mudança poder ir para a loja
# ===========================================================================

def test_com_caixa_desligado_a_os_grava_igual_e_o_livro_fica_vazio(client, db_session):
    header = _auth(client)
    funcionario_id, fp_id, cliente_id = _cenario(
        client, header, db_session, caixa_ligado=False
    )
    numero = _criar_os(client, header, cliente_id, funcionario_id, "SN-INERCIA", 15000)
    _finalizar(client, header, numero, fp_id, 15000)

    # A OS grava o pagamento como sempre gravou...
    pagamentos = db_session.query(OrdemServicoPagamento).all()
    assert len(pagamentos) == 1
    assert pagamentos[0].valor == 15000
    assert pagamentos[0].sessao_caixa_id is None

    # ...e o livro do dinheiro continua intocado.
    assert db_session.query(MovimentacaoFinanceira).count() == 0


# ===========================================================================
# COM CAIXA LIGADO — o buraco que esta onda fecha
# ===========================================================================

def test_os_finalizada_entra_no_livro_do_dinheiro(client, db_session):
    header = _auth(client)
    funcionario_id, fp_id, cliente_id = _cenario(client, header, db_session)
    numero = _criar_os(client, header, cliente_id, funcionario_id, "SN-1", 15000)
    _finalizar(client, header, numero, fp_id, 15000)

    movimentos = _movimentos_de_os(db_session)
    assert len(movimentos) == 1, "a OS tem que escrever na origem que o caixa já soma"
    assert movimentos[0].tipo == "ENTRADA"
    assert movimentos[0].valor == 15000
    assert movimentos[0].sessao_caixa_id is not None
    assert movimentos[0].ordem_servico_pagamento_id is not None


def test_o_dinheiro_da_os_aparece_no_fechamento(client, db_session):
    """O sintoma que o defeito causava: gaveta cheia e turno fechando com sobra."""
    header = _auth(client)
    funcionario_id, fp_id, cliente_id = _cenario(client, header, db_session)
    numero = _criar_os(client, header, cliente_id, funcionario_id, "SN-2", 15000)
    _finalizar(client, header, numero, fp_id, 15000)

    resumo = client.get("/api/v1/caixa/atual", headers=header).json()
    # Troco de abertura (10000) + a OS (15000).
    assert resumo["saldo_esperado_dinheiro"] == 25000


def test_pagamento_de_os_com_vencimento_futuro_nao_entra_na_gaveta(client, db_session):
    """Promessa não é dinheiro — a mesma regra que a venda já aplicava."""
    header = _auth(client)
    funcionario_id, fp_id, cliente_id = _cenario(client, header, db_session)
    numero = _criar_os(client, header, cliente_id, funcionario_id, "SN-3", 15000)
    _finalizar(client, header, numero, fp_id, 15000,
               vencimento=date.today() + timedelta(days=30))

    assert _movimentos_de_os(db_session) == []


# ===========================================================================
# REABERTURA
# ===========================================================================

def test_reabrir_sem_pagamento_real_devolve_o_dinheiro_ao_livro(client, db_session):
    """Reabrir com cliente_pagou=False apaga os pagamentos. Sem o estorno, as
    linhas do livro ficariam contando dinheiro que nunca entrou, e o turno
    passaria a fechar com FALTA — o espelho do defeito original."""
    header = _auth(client)
    funcionario_id, fp_id, cliente_id = _cenario(client, header, db_session)
    numero = _criar_os(client, header, cliente_id, funcionario_id, "SN-4", 15000)
    _finalizar(client, header, numero, fp_id, 15000)

    r = client.put(f"/api/v1/ordens-servico/{numero}/reabrir",
                   json={"cliente_pagou": False}, headers=header)
    assert r.status_code == 200, r.text

    movimentos = _movimentos_de_os(db_session)
    assert len(movimentos) == 2, "estorno INSERE o contrário, nunca apaga"
    assert movimentos[0].tipo == "ENTRADA"
    assert movimentos[1].tipo == "SAIDA"
    assert movimentos[0].valor == movimentos[1].valor

    resumo = client.get("/api/v1/caixa/atual", headers=header).json()
    assert resumo["saldo_esperado_dinheiro"] == 10000, "volta ao troco de abertura"


def test_reabrir_com_pagamento_real_nao_estorna(client, db_session):
    """cliente_pagou=True preserva o pagamento como crédito: o dinheiro entrou
    de verdade e continua na gaveta."""
    header = _auth(client)
    funcionario_id, fp_id, cliente_id = _cenario(client, header, db_session)
    numero = _criar_os(client, header, cliente_id, funcionario_id, "SN-5", 15000)
    _finalizar(client, header, numero, fp_id, 15000)

    r = client.put(f"/api/v1/ordens-servico/{numero}/reabrir",
                   json={"cliente_pagou": True}, headers=header)
    assert r.status_code == 200, r.text

    assert len(_movimentos_de_os(db_session)) == 1, "nada a estornar"


def test_refinalizar_nao_duplica_o_dinheiro(client, db_session):
    """`os.pagamentos` carrega os antigos junto; relançá-los duplicaria o que
    já entrou. Só os pagamentos DESTA finalização vão para o livro."""
    header = _auth(client)
    funcionario_id, fp_id, cliente_id = _cenario(client, header, db_session)
    numero = _criar_os(client, header, cliente_id, funcionario_id, "SN-6", 15000)
    _finalizar(client, header, numero, fp_id, 15000)

    client.put(f"/api/v1/ordens-servico/{numero}/reabrir",
               json={"cliente_pagou": True}, headers=header)
    # Refinaliza sem cobrar de novo: o crédito anterior já cobre o total.
    r = client.put(f"/api/v1/ordens-servico/{numero}/finalizar", json={
        "situacao_equipamento": "REPARADO", "garantia": "90 dias", "pagamentos": [],
    }, headers=header)
    assert r.status_code == 200, r.text

    assert len(_movimentos_de_os(db_session)) == 1, "o dinheiro entrou uma vez só"


# ===========================================================================
# PROMESSA -> CONTA A RECEBER (Onda 2A)
#
# O sistema sempre soube separar dinheiro de promessa; o que faltava era a
# promessa virar registro. Estes testes travam a geracao pelos DOIS lados.
# ===========================================================================

def test_os_a_prazo_gera_conta_a_receber(client, db_session):
    from app.db.models.conta_receber import ContaReceber

    header = _auth(client)
    funcionario_id, fp_id, cliente_id = _cenario(client, header, db_session)
    numero = _criar_os(client, header, cliente_id, funcionario_id, "SN-R1", 15000)
    vence = date.today() + timedelta(days=30)
    _finalizar(client, header, numero, fp_id, 15000, vencimento=vence)

    contas = db_session.query(ContaReceber).all()
    assert len(contas) == 1
    assert contas[0].valor == 15000
    assert contas[0].vencimento == vence
    assert contas[0].cliente_id == cliente_id
    assert contas[0].ordem_servico_pagamento_id is not None
    assert numero in contas[0].descricao
    # E o dinheiro NAO entrou na gaveta -- promessa nao e caixa.
    assert _movimentos_de_os(db_session) == []


def test_os_paga_na_hora_nao_gera_conta_a_receber(client, db_session):
    from app.db.models.conta_receber import ContaReceber

    header = _auth(client)
    funcionario_id, fp_id, cliente_id = _cenario(client, header, db_session)
    numero = _criar_os(client, header, cliente_id, funcionario_id, "SN-R2", 15000)
    _finalizar(client, header, numero, fp_id, 15000)

    assert db_session.query(ContaReceber).count() == 0
    assert len(_movimentos_de_os(db_session)) == 1


def test_refinalizar_nao_duplica_a_divida_do_cliente(client, db_session):
    """Uma OS reaberta passa de novo pelos mesmos pagamentos; sem idempotencia
    a divida do cliente dobraria a cada refinalizacao."""
    from app.db.models.conta_receber import ContaReceber

    header = _auth(client)
    funcionario_id, fp_id, cliente_id = _cenario(client, header, db_session)
    numero = _criar_os(client, header, cliente_id, funcionario_id, "SN-R3", 15000)
    vence = date.today() + timedelta(days=30)
    _finalizar(client, header, numero, fp_id, 15000, vencimento=vence)

    client.put(f"/api/v1/ordens-servico/{numero}/reabrir",
               json={"cliente_pagou": True}, headers=header)
    r = client.put(f"/api/v1/ordens-servico/{numero}/finalizar", json={
        "situacao_equipamento": "REPARADO", "garantia": "90 dias", "pagamentos": [],
    }, headers=header)
    assert r.status_code == 200, r.text

    assert db_session.query(ContaReceber).count() == 1, "a dívida nasce uma vez só"


def test_conta_a_receber_nasce_mesmo_com_o_caixa_desligado(client, db_session):
    """Amarrar o contas a receber ao controle de caixa esconderia a dívida de
    quem não usa gaveta — e é a maioria."""
    from app.db.models.conta_receber import ContaReceber

    header = _auth(client)
    funcionario_id, fp_id, cliente_id = _cenario(
        client, header, db_session, caixa_ligado=False
    )
    numero = _criar_os(client, header, cliente_id, funcionario_id, "SN-R4", 15000)
    _finalizar(client, header, numero, fp_id, 15000,
               vencimento=date.today() + timedelta(days=15))

    assert db_session.query(ContaReceber).count() == 1
    assert db_session.query(MovimentacaoFinanceira).count() == 0
