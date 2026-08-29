# ---------------------------------------------------------------------------
# Testes do Fluxo de Caixa — Onda 3.
#
# O teste que mais importa aqui é o do SALDO NÃO DECLARADO: enquanto o dono não
# disser quanto tem, a projeção não pode fingir que parte de zero. Zero é um
# saldo; "não sei" não é. Se ele um dia falhar, a tela volta a mostrar uma
# linha que parece dinheiro e não é.
# ---------------------------------------------------------------------------

from datetime import date, timedelta

from starlette import status

TEST_USER_EMAIL = "fluxo.dono@example.com"
TEST_USER_PASSWORD = "senhaSegura789"


# ===========================================================================
# HELPERS
# ===========================================================================

def _auth(client):
    client.post("/api/v1/usuarios/", json={
        "nome": "Dona do Fluxo", "email": TEST_USER_EMAIL, "senha": TEST_USER_PASSWORD,
    })
    login = client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": "hwid-fluxo",
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post("/api/v1/empresas/", json={
        "razao_social": "Fluxo LTDA", "nome_fantasia": "Fluxo", "is_cnpj": True,
        "documento": "12345678000188", "regime_tributario": "Simples Nacional",
        "celular": "11999997777", "segmento": "assistencia_tecnica",
        "endereco": [{"logradouro": "Av. Brasil", "numero": "500", "bairro": "Centro",
                      "cidade": "São Paulo", "estado": "SP", "cep": "01310-100"}],
    }, headers=header)
    return header


def _informar_saldo(client, header, centavos: int):
    """Declara o saldo na primeira conta ativa (a gaveta semeada pelo backend)."""
    contas = client.get("/api/v1/financeiro/contas-bancarias", headers=header).json()
    assert contas, "o backend semeia a gaveta no primeiro acesso"
    r = client.patch(
        f"/api/v1/financeiro/contas-bancarias/{contas[0]['id']}",
        json={"saldo_informado": centavos}, headers=header,
    )
    assert r.status_code == status.HTTP_200_OK, r.text
    return r.json()


def _pagar(client, header, valor: int, dias: int, descricao="Fornecedor"):
    r = client.post("/api/v1/financeiro/contas-pagar", json={
        "descricao": descricao, "valor": valor,
        "vencimento": (date.today() + timedelta(days=dias)).isoformat(),
    }, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    return r.json()


def _receber(client, header, valor: int, dias: int, descricao="Fiado"):
    r = client.post("/api/v1/financeiro/contas-receber", json={
        "descricao": descricao, "valor": valor,
        "vencimento": (date.today() + timedelta(days=dias)).isoformat(),
    }, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    return r.json()


def _fluxo(client, header, dias=30):
    r = client.get(f"/api/v1/financeiro/fluxo-caixa?dias={dias}", headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    return r.json()


# ===========================================================================
# O SALDO DE PARTIDA
# ===========================================================================

def test_sem_saldo_declarado_a_projecao_avisa_em_vez_de_supor_zero(client, db_session):
    """Nao saber quanto tem nao e a mesma coisa que ter zero.

    A tela usa esta flag para pedir o número antes de desenhar a linha. Sem ela,
    o dono leria a projeção como se fosse o saldo dele.
    """
    header = _auth(client)
    _pagar(client, header, 50000, dias=3)

    fluxo = _fluxo(client, header)

    assert fluxo["saldo_declarado"] is False
    assert fluxo["saldo_informado_em"] is None
    assert fluxo["saldo_inicial"] == 0
    # A projeção continua sendo calculada: o que muda é o aviso da tela.
    assert fluxo["total_saidas"] == 50000


def test_saldo_informado_carimba_a_data_no_servidor(client, db_session):
    """A data é a prova de quando o retrato foi tirado — o cliente não a escolhe."""
    header = _auth(client)
    conta = _informar_saldo(client, header, 320000)

    assert conta["saldo_informado"] == 320000
    assert conta["saldo_informado_em"] == date.today().isoformat()

    fluxo = _fluxo(client, header)
    assert fluxo["saldo_declarado"] is True
    assert fluxo["saldo_inicial"] == 320000
    assert fluxo["saldo_informado_em"] == date.today().isoformat()


def test_saldo_pode_ser_negativo(client, db_session):
    """Conta corrente no vermelho é saldo, não erro de digitação."""
    header = _auth(client)
    _informar_saldo(client, header, -45000)
    assert _fluxo(client, header)["saldo_inicial"] == -45000


def test_conta_desativada_sai_do_saldo_de_partida(client, db_session):
    """Dinheiro numa conta que a loja não usa mais não financia o mês."""
    header = _auth(client)
    contas = client.get("/api/v1/financeiro/contas-bancarias", headers=header).json()
    client.patch(f"/api/v1/financeiro/contas-bancarias/{contas[0]['id']}",
                 json={"saldo_informado": 100000}, headers=header)
    assert _fluxo(client, header)["saldo_inicial"] == 100000

    client.patch(f"/api/v1/financeiro/contas-bancarias/{contas[0]['id']}",
                 json={"ativo": False}, headers=header)
    assert _fluxo(client, header)["saldo_inicial"] == 0


# ===========================================================================
# A RÉGUA
# ===========================================================================

def test_a_regua_acumula_dia_a_dia_a_partir_do_saldo(client, db_session):
    header = _auth(client)
    _informar_saldo(client, header, 100000)
    _receber(client, header, 20000, dias=2)
    _pagar(client, header, 50000, dias=5)

    fluxo = _fluxo(client, header)
    linha = fluxo["linha"]

    assert len(linha) == 2, "só dias COM movimento entram na régua"
    assert linha[0]["data"] == (date.today() + timedelta(days=2)).isoformat()
    assert linha[0]["entradas"] == 20000
    assert linha[0]["saldo"] == 120000
    assert linha[1]["saidas"] == 50000
    assert linha[1]["saldo"] == 70000

    assert fluxo["saldo_final"] == 70000
    assert fluxo["total_entradas"] == 20000
    assert fluxo["total_saidas"] == 50000
    assert fluxo["primeiro_dia_negativo"] is None


def test_avisa_o_primeiro_dia_em_que_o_dinheiro_acaba(client, db_session):
    """O PRIMEIRO dia negativo, não o último: é a data em que dá para agir."""
    header = _auth(client)
    _informar_saldo(client, header, 30000)
    _pagar(client, header, 50000, dias=4, descricao="Aluguel")
    _pagar(client, header, 10000, dias=9, descricao="Luz")

    fluxo = _fluxo(client, header)

    assert fluxo["primeiro_dia_negativo"] == (date.today() + timedelta(days=4)).isoformat()
    assert fluxo["menor_saldo"] == -30000
    assert fluxo["menor_saldo_em"] == (date.today() + timedelta(days=9)).isoformat()


def test_sem_nada_agendado_o_fundo_do_poco_e_o_proprio_saldo(client, db_session):
    header = _auth(client)
    _informar_saldo(client, header, 80000)

    fluxo = _fluxo(client, header)
    assert fluxo["linha"] == []
    assert fluxo["menor_saldo"] == 80000
    assert fluxo["menor_saldo_em"] is None, "o fundo é hoje, e hoje não é um dia da régua"


def test_a_janela_corta_o_que_vence_depois(client, db_session):
    header = _auth(client)
    _informar_saldo(client, header, 100000)
    _pagar(client, header, 70000, dias=45, descricao="Seguro")

    assert _fluxo(client, header, dias=30)["linha"] == []
    assert len(_fluxo(client, header, dias=60)["linha"]) == 1
    assert _fluxo(client, header, dias=60)["saldo_final"] == 30000


def test_hoje_entra_na_janela(client, db_session):
    """Os proximos 30 dias comecam hoje de manha, nao amanha."""
    header = _auth(client)
    _pagar(client, header, 15000, dias=0, descricao="Vence hoje")

    fluxo = _fluxo(client, header)
    assert len(fluxo["linha"]) == 1
    assert fluxo["linha"][0]["data"] == date.today().isoformat()


def test_baixa_tira_o_documento_da_projecao(client, db_session):
    """Projeção é do que está EM ABERTO — pagou, sai da régua."""
    header = _auth(client)
    _informar_saldo(client, header, 100000)
    conta = _pagar(client, header, 40000, dias=6)
    assert _fluxo(client, header)["saldo_final"] == 60000

    client.post(f"/api/v1/financeiro/contas-pagar/{conta['id']}/pagar",
                json={}, headers=header)

    fluxo = _fluxo(client, header)
    assert fluxo["linha"] == []
    assert fluxo["saldo_final"] == 100000, "o saldo declarado não anda sozinho"


# ===========================================================================
# O ATRASADO
# ===========================================================================

def test_atrasado_fica_fora_da_regua_e_vira_aviso(client, db_session):
    """Conta vencida não tem dia futuro para ocupar.

    Empurrá-la para hoje inventaria um aperto que talvez não exista — o boleto
    pode ter sido pago no banco sem baixa aqui, e o fiado atrasado pode nunca
    chegar.
    """
    header = _auth(client)
    _informar_saldo(client, header, 100000)
    _pagar(client, header, 25000, dias=-10, descricao="Fornecedor atrasado")
    _receber(client, header, 8000, dias=-3, descricao="Fiado atrasado")

    fluxo = _fluxo(client, header)

    assert fluxo["linha"] == [], "nada vencido entra na régua"
    assert fluxo["saldo_final"] == 100000, "e nada vencido move o saldo previsto"
    assert fluxo["atrasado_a_pagar"] == 25000
    assert fluxo["atrasado_a_receber"] == 8000


# ===========================================================================
# LANÇAMENTOS DO DIA
# ===========================================================================

def test_o_dia_lista_o_que_o_compoe_com_entrada_antes_de_saida(client, db_session):
    header = _auth(client)
    _informar_saldo(client, header, 50000)
    _pagar(client, header, 30000, dias=7, descricao="Fornecedor")
    _receber(client, header, 12000, dias=7, descricao="Fiado do Joao")

    dia = _fluxo(client, header)["linha"][0]

    assert dia["saldo"] == 32000
    assert [item["tipo"] for item in dia["lancamentos"]] == ["ENTRADA", "SAIDA"]
    assert dia["lancamentos"][0]["descricao"] == "Fiado do Joao"
    assert dia["lancamentos"][1]["valor"] == 30000, "valor positivo; o sinal é o tipo"
