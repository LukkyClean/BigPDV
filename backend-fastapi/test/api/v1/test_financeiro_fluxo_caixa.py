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


# ===========================================================================
# PAINEL "PRECISA DE ATENCAO" (Visao Geral)
# ===========================================================================

def _alertas(client, header):
    hoje = date.today()
    primeiro = hoje.replace(day=1)
    ultimo = (primeiro + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    r = client.get(
        f"/api/v1/financeiro/resumo?inicio={primeiro}&fim={ultimo}", headers=header
    )
    assert r.status_code == status.HTTP_200_OK, r.text
    return {a["codigo"]: a for a in r.json()["alertas"]}


def test_loja_nova_e_avisada_de_que_falta_o_saldo(client, db_session):
    """Sem saldo nao ha projecao, e o dono nao tem como adivinhar isso sozinho."""
    header = _auth(client)
    alertas = _alertas(client, header)
    assert "SALDO_NUNCA_INFORMADO" in alertas
    assert alertas["SALDO_NUNCA_INFORMADO"]["severidade"] == "ATENCAO"


def test_conta_vencida_e_critica_e_traz_o_valor(client, db_session):
    header = _auth(client)
    _informar_saldo(client, header, 100000)
    _pagar(client, header, 25000, dias=-5, descricao="Fornecedor atrasado")

    alerta = _alertas(client, header)["CONTAS_VENCIDAS"]
    assert alerta["severidade"] == "CRITICO"
    assert alerta["valor"] == 25000


def test_fiado_atrasado_vira_alerta_de_cobranca(client, db_session):
    header = _auth(client)
    _informar_saldo(client, header, 100000)
    _receber(client, header, 7000, dias=-3, descricao="Fiado do Joao")

    alerta = _alertas(client, header)["FIADO_ATRASADO"]
    assert alerta["valor"] == 7000
    assert alerta["severidade"] == "ATENCAO"


def test_o_dia_em_que_o_dinheiro_acaba_vira_alerta_critico(client, db_session):
    """O unico alerta que olha para FRENTE -- e o mais valioso do painel."""
    header = _auth(client)
    _informar_saldo(client, header, 30000)
    _pagar(client, header, 50000, dias=4, descricao="Aluguel")

    alerta = _alertas(client, header)["CAIXA_NEGATIVO"]
    assert alerta["severidade"] == "CRITICO"
    assert alerta["data"] == (date.today() + timedelta(days=4)).isoformat()
    assert alerta["valor"] == -20000, "o fundo do poco"


def test_critico_vem_antes_de_atencao(client, db_session):
    """A ordem E a informacao: o que resolver hoje primeiro."""
    header = _auth(client)
    _informar_saldo(client, header, 10000)
    _pagar(client, header, 25000, dias=-5)      # CRITICO
    _receber(client, header, 7000, dias=-3)     # ATENCAO

    hoje = date.today()
    primeiro = hoje.replace(day=1)
    ultimo = (primeiro + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    lista = client.get(
        f"/api/v1/financeiro/resumo?inicio={primeiro}&fim={ultimo}", headers=header
    ).json()["alertas"]

    severidades = [a["severidade"] for a in lista]
    assert severidades == sorted(severidades, key=lambda s: 0 if s == "CRITICO" else 1)
    assert lista[0]["severidade"] == "CRITICO"


def test_loja_em_dia_nao_recebe_alerta_nenhum(client, db_session):
    """Painel que grita todo dia deixa de ser lido. Vazio e boa noticia."""
    header = _auth(client)
    _informar_saldo(client, header, 100000)

    assert _alertas(client, header) == {}


# ===========================================================================
# GRAVIDADE POR LIMIAR (Business Central) E TEMPO (Odoo)
#
# O Business Central colore o "Cue" por limiar, e o limiar e DIGITADO pelo
# administrador. Aqui ele e derivado do porte da loja -- lojista nao abre tela
# de setup para dizer quanto e muito dinheiro. Do Odoo vem a outra metade: nas
# atividades dele a cor sai do PRAZO, entao valor e tempo decidem juntos.
# ===========================================================================

def test_valor_pequeno_para_a_loja_nao_e_critico(client, db_session):
    """R$ 50 vencidos ontem nao acorda ninguem."""
    header = _auth(client)
    _informar_saldo(client, header, 100000)
    _pagar(client, header, 5000, dias=-1, descricao="Cafe")

    assert _alertas(client, header)["CONTAS_VENCIDAS"]["severidade"] == "ATENCAO"


def test_valor_material_para_a_loja_e_critico(client, db_session):
    """Acima do piso de R$ 200 (a loja de teste nao fatura), vira critico."""
    header = _auth(client)
    _informar_saldo(client, header, 100000)
    _pagar(client, header, 25000, dias=-1, descricao="Fornecedor")

    assert _alertas(client, header)["CONTAS_VENCIDAS"]["severidade"] == "CRITICO"


def test_atraso_longo_e_critico_mesmo_com_valor_pequeno(client, db_session):
    """A metade do Odoo: R$ 50 vencidos ha tres meses e outro problema.

    Valor OU tempo -- qualquer um dos dois basta. Sem esta regra, a divida
    pequena e antiga (a que vira negativacao) ficaria para sempre em cinza.
    """
    header = _auth(client)
    _informar_saldo(client, header, 100000)
    _pagar(client, header, 5000, dias=-95, descricao="Cafe esquecido")

    alerta = _alertas(client, header)["CONTAS_VENCIDAS"]
    assert alerta["severidade"] == "CRITICO"
    assert alerta["quantidade"] == 95, "o tempo viaja para a tela graduar o texto"


def test_aperto_distante_e_atencao_e_nao_critico(client, db_session):
    """Faltando 20 dias ainda da para agir sem susto."""
    header = _auth(client)
    _informar_saldo(client, header, 30000)
    _pagar(client, header, 50000, dias=20, descricao="Aluguel")

    alerta = _alertas(client, header)["CAIXA_NEGATIVO"]
    assert alerta["severidade"] == "ATENCAO"
    assert alerta["quantidade"] == 20


# ===========================================================================
# ADIAR (o snooze do NetSuite, sem o "dispensar para sempre")
# ===========================================================================

def test_adiar_cala_o_alerta_e_ele_volta_depois(client, db_session):
    from app.db.models.alerta_dispensado import AlertaDispensado

    header = _auth(client)
    _informar_saldo(client, header, 100000)
    _pagar(client, header, 25000, dias=-2)
    assert "CONTAS_VENCIDAS" in _alertas(client, header)

    r = client.post("/api/v1/financeiro/alertas/CONTAS_VENCIDAS/adiar?dias=7",
                    headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    assert "CONTAS_VENCIDAS" not in _alertas(client, header)

    # Vencido o prazo, o aviso volta -- e volta com o numero de HOJE, porque o
    # alerta e recalculado e so entao filtrado.
    registro = db_session.query(AlertaDispensado).one()
    registro.dispensado_ate = date.today() - timedelta(days=1)
    db_session.commit()

    assert "CONTAS_VENCIDAS" in _alertas(client, header)


def test_adiar_de_novo_estende_em_vez_de_empilhar(client, db_session):
    from app.db.models.alerta_dispensado import AlertaDispensado

    header = _auth(client)
    _informar_saldo(client, header, 100000)
    _pagar(client, header, 25000, dias=-2)

    client.post("/api/v1/financeiro/alertas/CONTAS_VENCIDAS/adiar?dias=7", headers=header)
    client.post("/api/v1/financeiro/alertas/CONTAS_VENCIDAS/adiar?dias=30", headers=header)

    registros = db_session.query(AlertaDispensado).all()
    assert len(registros) == 1, "uma linha por empresa/codigo"
    assert registros[0].dispensado_ate == date.today() + timedelta(days=30)


def test_adiar_nao_esconde_os_outros_alertas(client, db_session):
    """Calar um aviso nao cala o painel."""
    header = _auth(client)
    _pagar(client, header, 25000, dias=-2)

    client.post("/api/v1/financeiro/alertas/CONTAS_VENCIDAS/adiar?dias=7", headers=header)

    alertas = _alertas(client, header)
    assert "CONTAS_VENCIDAS" not in alertas
    assert "SALDO_NUNCA_INFORMADO" in alertas


def test_codigo_inventado_e_recusado(client, db_session):
    """A rota nao vira porta de entrada de linha inventada na tabela."""
    header = _auth(client)
    r = client.post("/api/v1/financeiro/alertas/QUALQUER_COISA/adiar", headers=header)
    assert r.status_code == status.HTTP_400_BAD_REQUEST


def test_silencio_tem_teto(client, db_session):
    """Calar por um ano seria esconder problema, nao adiar."""
    header = _auth(client)
    r = client.post("/api/v1/financeiro/alertas/CONTAS_VENCIDAS/adiar?dias=365",
                    headers=header)
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
