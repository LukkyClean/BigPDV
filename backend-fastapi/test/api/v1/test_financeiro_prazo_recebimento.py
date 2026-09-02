# ---------------------------------------------------------------------------
# Prazo de recebimento por forma de pagamento (02/09/2026).
#
# Dinheiro de cartao nao esta na conta no dia da venda: a maquininha deposita
# depois. Ate aqui o sistema tratava todo recebimento como dinheiro que ja
# entrou, e o saldo do Fluxo de Caixa mostrava na conta um valor que so chegaria
# amanha.
#
# O QUE ESTE ARQUIVO PROTEGE, na ordem do que doi mais se quebrar:
#
#   1. PRAZO ZERO NAO MUDA NADA. E o padrao de toda forma, e e o comportamento
#      que tres lojas em producao tem hoje. Se este teste falhar, a atualizacao
#      quebrou o caixa de quem nunca pediu nada.
#   2. FIADO NUNCA ENTRA SOZINHO. A baixa automatica so alcanca o que nasceu
#      marcado. Se ela alcancar fiado, o sistema passa a inventar que o cliente
#      pagou -- e o dono so descobre quando o dinheiro nao esta la.
#   3. A TAREFA SE RECUPERA. Loja fecha na sexta e abre na segunda; o que
#      venceu no fim de semana entra todo no boot de segunda.
# ---------------------------------------------------------------------------

from datetime import date, timedelta

from starlette import status

from app.db.models.conta_receber import ContaReceber
from app.db.models.movimentacao_financeira import MovimentacaoFinanceira
from app.services import financeiro_receber as receber_service

TEST_USER_EMAIL = "prazo.dono@example.com"
TEST_USER_PASSWORD = "senhaSegura789"


# ===========================================================================
# HELPERS
# ===========================================================================

def _auth(client):
    client.post("/api/v1/usuarios/", json={
        "nome": "Dono do Prazo", "email": TEST_USER_EMAIL, "senha": TEST_USER_PASSWORD,
    })
    login = client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": "hwid-prazo",
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post("/api/v1/empresas/", json={
        "razao_social": "Prazo LTDA", "nome_fantasia": "Prazo", "is_cnpj": True,
        "documento": "12345678000188", "regime_tributario": "Simples Nacional",
        "celular": "11999997777", "segmento": "assistencia_tecnica",
        "endereco": [{"logradouro": "Av. Brasil", "numero": "500", "bairro": "Centro",
                      "cidade": "São Paulo", "estado": "SP", "cep": "01310-100"}],
    }, headers=header)
    return header


def _forma(client, header, nome, dias=None, conta_bancaria_id=None):
    r = client.post("/api/v1/formas-pagamento/", json={"nome": nome, "ativo": True},
                    headers=header)
    if r.status_code == 201:
        fp_id = r.json()["id"]
    else:
        fp_id = next(
            f["id"] for f in client.get("/api/v1/formas-pagamento/", headers=header).json()
            if f["nome"].lower() == nome.lower()
        )
    if dias is not None or conta_bancaria_id is not None:
        corpo = {}
        if dias is not None:
            corpo["dias_para_receber"] = dias
        if conta_bancaria_id is not None:
            corpo["conta_bancaria_id"] = conta_bancaria_id
        r = client.put(f"/api/v1/formas-pagamento/{fp_id}", json=corpo, headers=header)
        assert r.status_code == status.HTTP_200_OK, r.text
    return fp_id


def _funcionario(client, header):
    r = client.post("/api/v1/funcionarios/", json={
        "nome": "Tecnico", "cpf": "11122233355", "contato": "11999999999",
        "usuario": {"nome": "tec", "email": "tec.prazo@empresa.com", "senha": "SenhaForte123!"},
        "endereco": [{"logradouro": "Rua X", "numero": "1", "cep": "12345-678",
                      "bairro": "Centro", "cidade": "Lab City", "estado": "SP"}],
    }, headers=header)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _cliente(client, header):
    r = client.post("/api/v1/clientes/cliente_pf", json={
        "nome": "Cliente OS", "cpf": "98765432199", "tipo": "PF", "celular": "11988887777",
        "endereco": [{"logradouro": "Rua Y", "numero": "10", "bairro": "Centro",
                      "cidade": "Campinas", "estado": "SP", "cep": "13010-000"}],
    }, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _os_finalizada(client, header, cliente_id, funcionario_id, *, valor, forma_id,
                   serie="SN-PRAZO", vencimento=None):
    numero = client.post("/api/v1/ordens-servico/", json={
        "cliente_id": cliente_id, "prioridade": "NORMAL", "defeito_relatado": "Nao liga",
        "dados_adicionais": {}, "funcionario_id": funcionario_id,
        "objeto": {"marca": "Dell", "modelo": "Inspiron", "numero_serie": serie,
                   "dados_adicionais": {}},
        "itens": [{"tipo": "SERVICO", "nome": "Reparo", "unidade_medida": "UN",
                   "quantidade": 1, "valor_unitario": valor}],
    }, headers=header).json()["numero_os"]

    pagamento = {"forma_pagamento_id": forma_id, "valor": valor}
    if vencimento:
        pagamento["vencimento"] = vencimento.isoformat()

    r = client.put(f"/api/v1/ordens-servico/{numero}/finalizar", json={
        "situacao_equipamento": "REPARADO", "garantia": "90 dias",
        "pagamentos": [pagamento],
    }, headers=header)
    assert r.status_code == 200, r.text
    return numero


def _informar_saldo(client, header, centavos):
    contas = client.get("/api/v1/financeiro/contas-bancarias", headers=header).json()
    r = client.patch(f"/api/v1/financeiro/contas-bancarias/{contas[0]['id']}",
                     json={"saldo_informado": centavos}, headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    return contas[0]["id"]


def _fluxo(client, header, dias=30):
    r = client.get(f"/api/v1/financeiro/fluxo-caixa?dias={dias}", headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    return r.json()


# ===========================================================================
# O PADRAO NAO MUDA NADA
# ===========================================================================

def test_sem_prazo_declarado_o_dinheiro_entra_na_hora(client, db_session):
    """O comportamento de tres lojas em producao, travado.

    Toda forma nasce com prazo ZERO, e zero e exatamente como sempre foi. Se
    este teste falhar, a atualizacao quebrou o caixa de quem nunca pediu nada.
    """
    header = _auth(client)
    conta_id = _informar_saldo(client, header, 10000)
    forma_id = _forma(client, header, "Dinheiro")

    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)
    _os_finalizada(client, header, cliente_id, funcionario_id,
                   valor=20000, forma_id=forma_id)

    fluxo = _fluxo(client, header)
    assert fluxo["saldo_entrou"] == 20000, "sem prazo, o dinheiro entra hoje"
    assert fluxo["saldo_inicial"] == 30000
    assert fluxo["total_entradas"] == 0, "nao virou promessa nenhuma"

    assert db_session.query(ContaReceber).count() == 0


# ===========================================================================
# COM PRAZO: O DINHEIRO ENTRA NO DIA CERTO
# ===========================================================================

def test_cartao_com_prazo_vira_previsao_e_nao_saldo_de_hoje(client, db_session):
    """O pedido do dono: 'passo hoje, cai amanha'.

    A venda no cartao nao pode subir o saldo de hoje -- o dinheiro nao esta na
    conta. Ela aparece em 'Vai entrar' no dia em que a operadora deposita.
    """
    header = _auth(client)
    _informar_saldo(client, header, 10000)
    forma_id = _forma(client, header, "Cartao de Credito", dias=1)

    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)
    _os_finalizada(client, header, cliente_id, funcionario_id,
                   valor=46886, forma_id=forma_id)

    fluxo = _fluxo(client, header)
    assert fluxo["saldo_entrou"] == 0, "o dinheiro do cartao nao esta na conta hoje"
    assert fluxo["saldo_inicial"] == 10000
    assert fluxo["total_entradas"] == 46886, "esta previsto para entrar"

    # E cai no dia certo, com a marca que autoriza a baixa sozinha.
    cobranca = db_session.query(ContaReceber).one()
    assert cobranca.vencimento == date.today() + timedelta(days=1)
    assert cobranca.baixa_automatica is True


def test_a_baixa_automatica_poe_o_dinheiro_no_caixa_no_vencimento(client, db_session):
    """Chegou o dia: o dinheiro entra sem ninguem clicar."""
    header = _auth(client)
    _informar_saldo(client, header, 10000)
    forma_id = _forma(client, header, "Cartao de Credito", dias=1)

    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)
    _os_finalizada(client, header, cliente_id, funcionario_id,
                   valor=46886, forma_id=forma_id)

    # O dia seguinte chega.
    amanha = date.today() + timedelta(days=1)
    assert receber_service.baixar_automaticas(db_session, hoje=amanha) == 1

    fluxo = _fluxo(client, header)
    assert fluxo["saldo_entrou"] == 46886
    assert fluxo["saldo_inicial"] == 10000 + 46886
    assert fluxo["total_entradas"] == 0, "saiu da previsao: ja entrou"


def test_a_baixa_automatica_recupera_o_fim_de_semana(client, db_session):
    """Loja fecha na sexta e abre na segunda.

    A consulta e por 'vencimento <= hoje', e nao '= hoje'. Sem isso, todo dia em
    que a maquina ficasse desligada perderia o deposito daquele dia PARA SEMPRE
    -- o defeito classico de agendamento em maquina de loja.
    """
    header = _auth(client)
    _informar_saldo(client, header, 0)
    forma_id = _forma(client, header, "Cartao de Credito", dias=1)

    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)
    for i, valor in enumerate((10000, 20000, 30000)):
        _os_finalizada(client, header, cliente_id, funcionario_id,
                       valor=valor, forma_id=forma_id, serie=f"SN-FDS-{i}")

    # Ninguem ligou a maquina por tres dias.
    depois = date.today() + timedelta(days=3)
    assert receber_service.baixar_automaticas(db_session, hoje=depois) == 3

    assert _fluxo(client, header)["saldo_entrou"] == 60000


def test_baixa_automatica_e_idempotente(client, db_session):
    """Rodar de novo nao duplica: a baixa muda o status e a consulta so ve PENDENTE."""
    header = _auth(client)
    _informar_saldo(client, header, 0)
    forma_id = _forma(client, header, "Cartao de Credito", dias=1)

    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)
    _os_finalizada(client, header, cliente_id, funcionario_id,
                   valor=25000, forma_id=forma_id)

    amanha = date.today() + timedelta(days=1)
    assert receber_service.baixar_automaticas(db_session, hoje=amanha) == 1
    assert receber_service.baixar_automaticas(db_session, hoje=amanha) == 0

    entradas = (
        db_session.query(MovimentacaoFinanceira)
        .filter(MovimentacaoFinanceira.origem == "RECEBIMENTO")
        .count()
    )
    assert entradas == 1


# ===========================================================================
# A LINHA QUE NAO PODE SER CRUZADA
# ===========================================================================

def test_fiado_nunca_entra_sozinho(client, db_session):
    """A distincao que separa 'a maquininha deposita' de 'inventar que o cliente pagou'.

    Fiado tambem e conta a receber e tambem tem vencimento futuro -- chega pelo
    mesmo caminho. O que o separa e a MARCA, posta so quando a forma tem prazo
    declarado. Se este teste falhar, o sistema passa a dar por recebido dinheiro
    que ninguem trouxe.
    """
    header = _auth(client)
    _informar_saldo(client, header, 0)
    # Dinheiro NAO tem prazo: a data veio de um acordo com o cliente.
    forma_id = _forma(client, header, "Dinheiro")

    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)
    _os_finalizada(client, header, cliente_id, funcionario_id, valor=30000,
                   forma_id=forma_id, vencimento=date.today() + timedelta(days=10))

    cobranca = db_session.query(ContaReceber).one()
    assert cobranca.baixa_automatica is False

    muito_depois = date.today() + timedelta(days=60)
    assert receber_service.baixar_automaticas(db_session, hoje=muito_depois) == 0
    assert _fluxo(client, header)["saldo_entrou"] == 0


def test_data_digitada_a_mao_vence_o_prazo_da_forma(client, db_session):
    """A forma so diz o PADRAO. Combinou outra data com o cliente, manda a combinada."""
    header = _auth(client)
    forma_id = _forma(client, header, "Cartao de Credito", dias=1)

    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)
    combinado = date.today() + timedelta(days=15)
    _os_finalizada(client, header, cliente_id, funcionario_id, valor=30000,
                   forma_id=forma_id, vencimento=combinado)

    cobranca = db_session.query(ContaReceber).one()
    assert cobranca.vencimento == combinado


def test_o_dinheiro_cai_na_conta_declarada_na_forma(client, db_session):
    """Cartao cai no banco, dinheiro fica na gaveta."""
    header = _auth(client)
    _informar_saldo(client, header, 0)

    r = client.post("/api/v1/financeiro/contas-bancarias",
                    json={"nome": "Conta da empresa", "tipo": "BANCO"}, headers=header)
    assert r.status_code in (200, 201), r.text
    banco_id = r.json()["id"]

    forma_id = _forma(client, header, "Cartao de Credito", dias=1,
                      conta_bancaria_id=banco_id)

    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)
    _os_finalizada(client, header, cliente_id, funcionario_id,
                   valor=40000, forma_id=forma_id)

    receber_service.baixar_automaticas(db_session, hoje=date.today() + timedelta(days=1))

    movimento = (
        db_session.query(MovimentacaoFinanceira)
        .filter(MovimentacaoFinanceira.origem == "RECEBIMENTO")
        .one()
    )
    assert movimento.conta_bancaria_id == banco_id


def test_prazo_absurdo_e_recusado(client, db_session):
    """Um digito a mais nao pode virar entrada daqui a tres anos."""
    header = _auth(client)
    fp_id = _forma(client, header, "Cartao de Credito")

    r = client.put(f"/api/v1/formas-pagamento/{fp_id}",
                     json={"dias_para_receber": 3650}, headers=header)
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, r.text
