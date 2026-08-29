# ---------------------------------------------------------------------------
# Testes da Conciliação — Onda 4.
#
# O teste que mais importa aqui é o do RATEIO: a soma das baixas do lote tem
# que ser EXATAMENTE o que caiu no banco, centavo a centavo. Se ele falhar, o
# livro do dinheiro passa a discordar do extrato — e é justamente essa
# diferença que a tela existe para eliminar.
# ---------------------------------------------------------------------------

from datetime import date, timedelta

from starlette import status

TEST_USER_EMAIL = "conciliacao.dono@example.com"
TEST_USER_PASSWORD = "senhaSegura789"


# ===========================================================================
# HELPERS
# ===========================================================================

def _auth(client):
    client.post("/api/v1/usuarios/", json={
        "nome": "Dono da Conciliacao", "email": TEST_USER_EMAIL,
        "senha": TEST_USER_PASSWORD,
    })
    login = client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD,
        "hwid": "hwid-conciliacao",
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post("/api/v1/empresas/", json={
        "razao_social": "Conciliacao LTDA", "nome_fantasia": "Conciliacao", "is_cnpj": True,
        "documento": "12345678000188", "regime_tributario": "Simples Nacional",
        "celular": "11999997777", "segmento": "assistencia_tecnica",
        "endereco": [{"logradouro": "Av. Brasil", "numero": "500", "bairro": "Centro",
                      "cidade": "São Paulo", "estado": "SP", "cep": "01310-100"}],
    }, headers=header)
    return header


def _receber(client, header, valor: int, dias: int, descricao="Venda no cartao"):
    r = client.post("/api/v1/financeiro/contas-receber", json={
        "descricao": descricao, "valor": valor,
        "vencimento": (date.today() + timedelta(days=dias)).isoformat(),
    }, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    return r.json()


def _conciliacao(client, header, de=-30, ate=60):
    r = client.get(
        "/api/v1/financeiro/conciliacao"
        f"?inicio={(date.today() + timedelta(days=de)).isoformat()}"
        f"&fim={(date.today() + timedelta(days=ate)).isoformat()}",
        headers=header,
    )
    assert r.status_code == status.HTTP_200_OK, r.text
    return r.json()


def _baixar(client, header, dias: int, valor: int, esperado=status.HTTP_200_OK):
    r = client.post("/api/v1/financeiro/conciliacao/baixar-lote", json={
        "data": (date.today() + timedelta(days=dias)).isoformat(),
        "valor_recebido": valor,
    }, headers=header)
    assert r.status_code == esperado, r.text
    return r.json()


# ===========================================================================
# A LISTA
# ===========================================================================

def test_agrupa_por_dia_de_vencimento(client, db_session):
    """O dinheiro chega em lote, não venda a venda — o agrupamento segue isso."""
    header = _auth(client)
    _receber(client, header, 10000, dias=5, descricao="Venda 1")
    _receber(client, header, 25000, dias=5, descricao="Venda 2")
    _receber(client, header, 7000, dias=9, descricao="Venda 3")

    dados = _conciliacao(client, header)

    assert dados["total_previsto"] == 42000
    assert len(dados["dias"]) == 2

    primeiro = dados["dias"][0]
    assert primeiro["data"] == (date.today() + timedelta(days=5)).isoformat()
    assert primeiro["quantidade"] == 2
    assert primeiro["total_previsto"] == 35000
    assert {item["descricao"] for item in primeiro["itens"]} == {"Venda 1", "Venda 2"}


def test_recebida_sai_da_fila_de_conferencia(client, db_session):
    header = _auth(client)
    conta = _receber(client, header, 10000, dias=4)
    assert len(_conciliacao(client, header)["dias"]) == 1

    client.post(f"/api/v1/financeiro/contas-receber/{conta['id']}/receber",
                json={}, headers=header)

    assert _conciliacao(client, header)["dias"] == []


# ===========================================================================
# O RATEIO — o coração da onda
# ===========================================================================

def test_deposito_menor_e_rateado_proporcionalmente(client, db_session):
    """A taxa da operadora não cai igual sobre venda de R$ 20 e de R$ 400."""
    header = _auth(client)
    grande = _receber(client, header, 40000, dias=3, descricao="Venda grande")
    pequena = _receber(client, header, 10000, dias=3, descricao="Venda pequena")

    # Caíram R$ 490 de R$ 500 previstos: R$ 10 de taxa.
    resultado = _baixar(client, header, dias=3, valor=49000)

    assert resultado["quantidade"] == 2
    assert resultado["total_previsto"] == 50000
    assert resultado["total_recebido"] == 49000
    assert resultado["diferenca"] == -1000

    contas = {
        c["id"]: c
        for c in client.get("/api/v1/financeiro/contas-receber",
                            headers=header).json()["itens"]
    }
    assert contas[grande["id"]]["valor_recebido"] == 39200, "80% do depósito"
    assert contas[pequena["id"]]["valor_recebido"] == 9800, "20% do depósito"
    assert contas[grande["id"]]["status"] == "RECEBIDA"


def test_a_soma_das_baixas_e_exatamente_o_deposito(client, db_session):
    """Com centavo quebrado o rateio ainda tem que fechar com o extrato.

    Três contas iguais e um depósito de R$ 100,00 dão 3.333,33 centavos cada.
    Se cada baixa arredondasse por conta própria, a soma daria 9.999 ou 10.001 —
    e o livro do dinheiro discordaria do banco em um centavo, para sempre.
    """
    from app.db.models.movimentacao_financeira import MovimentacaoFinanceira

    header = _auth(client)
    for i in range(3):
        _receber(client, header, 5000, dias=6, descricao=f"Venda {i}")

    _baixar(client, header, dias=6, valor=10000)

    entradas = [
        m.valor for m in db_session.query(MovimentacaoFinanceira)
        .filter(MovimentacaoFinanceira.origem == "RECEBIMENTO").all()
    ]
    assert len(entradas) == 3
    assert sum(entradas) == 10000, "a soma das baixas é o depósito, centavo a centavo"


def test_deposito_exato_baixa_cada_conta_pelo_previsto(client, db_session):
    header = _auth(client)
    _receber(client, header, 12000, dias=2, descricao="A")
    _receber(client, header, 8000, dias=2, descricao="B")

    resultado = _baixar(client, header, dias=2, valor=20000)

    assert resultado["diferenca"] == 0
    valores = sorted(
        c["valor_recebido"]
        for c in client.get("/api/v1/financeiro/contas-receber",
                            headers=header).json()["itens"]
    )
    assert valores == [8000, 12000]


def test_lote_usa_o_mesmo_caminho_da_baixa_manual(client, db_session):
    """Mesmo movimento no livro, mesma trilha — e por isso o mesmo estorno.

    Se o lote tivesse caminho próprio, uma conciliação errada não teria como
    ser desfeita pela tela de Contas a Receber.
    """
    from app.db.models.movimentacao_financeira import MovimentacaoFinanceira

    header = _auth(client)
    conta = _receber(client, header, 15000, dias=7)
    _baixar(client, header, dias=7, valor=14500)

    movimentos = db_session.query(MovimentacaoFinanceira).all()
    assert len(movimentos) == 1
    assert movimentos[0].tipo == "ENTRADA"
    assert movimentos[0].origem == "RECEBIMENTO"
    # Quitar dívida antiga não pertence a turno de caixa nenhum.
    assert movimentos[0].sessao_caixa_id is None

    historico = client.get(
        f"/api/v1/financeiro/contas-receber/{conta['id']}/historico", headers=header
    )
    assert historico.status_code == status.HTTP_200_OK
    assert any(linha["campo"] == "baixa" for linha in historico.json())

    estorno = client.post(
        f"/api/v1/financeiro/contas-receber/{conta['id']}/estornar",
        json={"motivo": "conciliei o dia errado"}, headers=header,
    )
    assert estorno.status_code == status.HTTP_200_OK, estorno.text
    assert estorno.json()["status"] == "PENDENTE"


def test_a_data_da_baixa_e_a_do_lote_nao_a_de_hoje(client, db_session):
    """O dinheiro caiu no dia do repasse; conciliar com atraso não muda isso."""
    header = _auth(client)
    _receber(client, header, 9000, dias=-4, descricao="Repasse de quatro dias atras")

    _baixar(client, header, dias=-4, valor=9000)

    conta = client.get("/api/v1/financeiro/contas-receber",
                       headers=header).json()["itens"][0]
    assert conta["recebido_em"].startswith((date.today() - timedelta(days=4)).isoformat())


# ===========================================================================
# RECUSAS
# ===========================================================================

def test_dia_sem_cobranca_pendente_e_recusado(client, db_session):
    header = _auth(client)
    _baixar(client, header, dias=8, valor=5000, esperado=status.HTTP_400_BAD_REQUEST)


def test_deposito_pequeno_demais_para_o_lote_e_recusado(client, db_session):
    """Antes zerar uma cobrança do que registrar baixa de valor zero.

    Um depósito muito menor que o lote quase sempre é o dia errado, não uma
    taxa de 99% — e a mensagem manda dar baixa uma a uma.
    """
    header = _auth(client)
    _receber(client, header, 100000, dias=3, descricao="Grande")
    _receber(client, header, 100, dias=3, descricao="Minúscula")

    _baixar(client, header, dias=3, valor=100, esperado=status.HTTP_400_BAD_REQUEST)

    # Nada foi baixado: a recusa acontece ANTES de mexer em qualquer conta.
    pendentes = client.get("/api/v1/financeiro/contas-receber?status=PENDENTE",
                           headers=header).json()
    assert pendentes["total_itens"] == 2
