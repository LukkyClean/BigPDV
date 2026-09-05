# ---------------------------------------------------------------------------
# Testes do módulo de gestão financeira — Onda 1 (contas a pagar).
#
# O teste mais importante deste arquivo é o do ESTORNO: ele prova a regra que
# separa este módulo de uma planilha — o livro do dinheiro só recebe INSERT, e
# desfazer um pagamento gera um movimento contrário em vez de apagar o original.
# Se ele um dia falhar, a trilha de auditoria deixou de existir.
# ---------------------------------------------------------------------------

from datetime import date, timedelta

from starlette import status

from app.db.models.conta_pagar import ContaPagar
from app.db.models.movimentacao_financeira import MovimentacaoFinanceira

TEST_USER_EMAIL = "financeiro.dono@example.com"
TEST_USER_PASSWORD = "senhaSegura789"


# ===========================================================================
# HELPERS
# ===========================================================================

def _auth(client):
    client.post("/api/v1/usuarios/", json={
        "nome": "Dono da Oficina", "email": TEST_USER_EMAIL, "senha": TEST_USER_PASSWORD,
    })
    login = client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": "hwid-financeiro",
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post("/api/v1/empresas/", json={
        "razao_social": "Oficina Financeiro LTDA", "nome_fantasia": "Oficina", "is_cnpj": True,
        "documento": "12345678000188", "regime_tributario": "Simples Nacional",
        "celular": "11999997777", "segmento": "assistencia_tecnica",
        "endereco": [{"logradouro": "Av. Brasil", "numero": "500", "bairro": "Centro",
                      "cidade": "São Paulo", "estado": "SP", "cep": "01310-100"}],
    }, headers=header)
    return header


def _criar_conta(client, header, **kwargs):
    payload = {
        "descricao": "Aluguel de setembro",
        "valor": 250000,
        "vencimento": (date.today() + timedelta(days=5)).isoformat(),
    }
    payload.update(kwargs)
    r = client.post("/api/v1/financeiro/contas-pagar", json=payload, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    return r.json()


# ===========================================================================
# PLANO DE CONTAS
# ===========================================================================

def test_plano_de_contas_e_semeado_no_primeiro_acesso(client, db_session):
    """Lista vazia trava o módulo no primeiro uso — por isso as padrão existem."""
    header = _auth(client)

    r = client.get("/api/v1/financeiro/plano-contas", headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text

    categorias = r.json()
    assert len(categorias) > 0, "o primeiro acesso tem que vir com categorias"
    assert all(c["padrao"] for c in categorias)
    assert any("Aluguel" in c["nome"] for c in categorias)


def test_semeadura_nao_ressuscita_categoria_apagada(client, db_session):
    """Semear pela lista vazia faria as padrão voltarem toda vez que o lojista
    desativasse todas — e ele nunca conseguiria dizer 'não quero nenhuma'."""
    header = _auth(client)

    primeira = client.get("/api/v1/financeiro/plano-contas", headers=header).json()
    quantidade_inicial = len(primeira)

    # Desativa todas
    for c in primeira:
        client.patch(
            f"/api/v1/financeiro/plano-contas/{c['id']}",
            json={"ativo": False}, headers=header,
        )

    segunda = client.get("/api/v1/financeiro/plano-contas", headers=header).json()
    assert len(segunda) == quantidade_inicial, "não pode semear de novo"
    assert all(not c["ativo"] for c in segunda)


def test_categoria_duplicada_e_recusada(client, db_session):
    header = _auth(client)
    client.post("/api/v1/financeiro/plano-contas",
                json={"nome": "Contador"}, headers=header)
    r = client.post("/api/v1/financeiro/plano-contas",
                    json={"nome": "contador"}, headers=header)
    assert r.status_code == status.HTTP_400_BAD_REQUEST


# ===========================================================================
# CADASTRO E EDIÇÃO
# ===========================================================================

def test_conta_nasce_pendente_e_sem_lancamento_no_livro(client, db_session):
    """Cobrança não é movimento: uma conta que ainda não venceu não é dinheiro
    que saiu, e o livro tem que continuar vazio."""
    header = _auth(client)
    conta = _criar_conta(client, header)

    assert conta["status"] == "PENDENTE"
    assert conta["valor_pago"] is None
    assert conta["pago_em"] is None

    movimentos = db_session.query(MovimentacaoFinanceira).all()
    assert movimentos == [], "cadastrar conta NÃO pode escrever no livro"


def test_conta_vencida_e_marcada_na_leitura(client, db_session):
    """`vencida` é derivado de hoje, nunca guardado: uma coluna precisaria de
    alguém rodando à meia-noite, e a loja passa a noite desligada."""
    header = _auth(client)
    conta = _criar_conta(
        client, header, vencimento=(date.today() - timedelta(days=3)).isoformat()
    )
    assert conta["vencida"] is True
    assert conta["dias_para_vencer"] == -3


def test_alterar_vencimento_deixa_rastro(client, db_session):
    header = _auth(client)
    conta = _criar_conta(client, header)
    novo = (date.today() + timedelta(days=20)).isoformat()

    r = client.patch(
        f"/api/v1/financeiro/contas-pagar/{conta['id']}",
        json={"vencimento": novo}, headers=header,
    )
    assert r.status_code == status.HTTP_200_OK, r.text

    hist = client.get(
        f"/api/v1/financeiro/contas-pagar/{conta['id']}/historico", headers=header
    ).json()
    campos = [h["campo"] for h in hist]
    assert "vencimento" in campos, "prorrogar boleto tem que deixar rastro"


def test_cancelar_nao_exclui(client, db_session):
    """'Sumiu uma conta de R$ 3.000' é a pergunta que o módulo tem que responder."""
    header = _auth(client)
    conta = _criar_conta(client, header)

    r = client.delete(f"/api/v1/financeiro/contas-pagar/{conta['id']}", headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    assert r.json()["status"] == "CANCELADA"

    assert db_session.query(ContaPagar).filter_by(id=conta["id"]).first() is not None


# ===========================================================================
# BAIXA
# ===========================================================================

def test_baixa_gera_saida_no_livro_do_dinheiro(client, db_session):
    header = _auth(client)
    conta = _criar_conta(client, header)

    r = client.post(
        f"/api/v1/financeiro/contas-pagar/{conta['id']}/pagar", json={}, headers=header
    )
    assert r.status_code == status.HTTP_200_OK, r.text
    paga = r.json()

    assert paga["status"] == "PAGA"
    assert paga["valor_pago"] == 250000
    assert paga["pago_em"] is not None

    movimentos = db_session.query(MovimentacaoFinanceira).all()
    assert len(movimentos) == 1
    assert movimentos[0].tipo == "SAIDA"
    assert movimentos[0].origem == "DESPESA"
    assert movimentos[0].valor == 250000
    # Pagar fornecedor não é sangria: não pertence a turno de caixa nenhum.
    assert movimentos[0].sessao_caixa_id is None


def test_valor_pago_pode_diferir_do_valor_previsto(client, db_session):
    """Juros por atraso e desconto por antecipação são a regra, não a exceção."""
    header = _auth(client)
    conta = _criar_conta(client, header)

    r = client.post(
        f"/api/v1/financeiro/contas-pagar/{conta['id']}/pagar",
        json={"valor_pago": 265000}, headers=header,
    )
    assert r.status_code == status.HTTP_200_OK, r.text
    assert r.json()["valor"] == 250000, "o previsto não muda"
    assert r.json()["valor_pago"] == 265000, "o realizado é o que saiu"


def test_conta_paga_nao_pode_ser_editada(client, db_session):
    header = _auth(client)
    conta = _criar_conta(client, header)
    client.post(f"/api/v1/financeiro/contas-pagar/{conta['id']}/pagar",
                json={}, headers=header)

    r = client.patch(
        f"/api/v1/financeiro/contas-pagar/{conta['id']}",
        json={"valor": 100}, headers=header,
    )
    assert r.status_code == status.HTTP_400_BAD_REQUEST


def test_pagar_duas_vezes_e_recusado(client, db_session):
    header = _auth(client)
    conta = _criar_conta(client, header)
    url = f"/api/v1/financeiro/contas-pagar/{conta['id']}/pagar"

    assert client.post(url, json={}, headers=header).status_code == 200
    assert client.post(url, json={}, headers=header).status_code == 400
    assert db_session.query(MovimentacaoFinanceira).count() == 1


def test_conta_recorrente_gera_a_do_mes_seguinte_ao_dar_baixa(client, db_session):
    """Redigitar o aluguel doze vezes por ano é o atrito que faz o módulo ser
    abandonado. A próxima nasce com o valor ORIGINAL, não com o pago."""
    header = _auth(client)
    vencimento = date.today().replace(day=10)
    conta = _criar_conta(
        client, header, vencimento=vencimento.isoformat(), recorrente=True
    )

    client.post(f"/api/v1/financeiro/contas-pagar/{conta['id']}/pagar",
                json={"valor_pago": 999999}, headers=header)

    lista = client.get("/api/v1/financeiro/contas-pagar?status=PENDENTE",
                       headers=header).json()
    assert lista["total_itens"] == 1
    proxima = lista["itens"][0]
    assert proxima["valor"] == 250000, "a próxima usa o previsto, não o pago"
    assert proxima["vencimento"] > vencimento.isoformat()
    assert proxima["recorrente"] is True


# ===========================================================================
# ESTORNO — o teste que prova a imutabilidade do livro
# ===========================================================================

def test_estorno_nao_apaga_o_lancamento_original(client, db_session):
    header = _auth(client)
    conta = _criar_conta(client, header)
    client.post(f"/api/v1/financeiro/contas-pagar/{conta['id']}/pagar",
                json={}, headers=header)

    r = client.post(
        f"/api/v1/financeiro/contas-pagar/{conta['id']}/estornar",
        json={"motivo": "lancado na conta errada"}, headers=header,
    )
    assert r.status_code == status.HTTP_200_OK, r.text

    # A conta volta a dever
    assert r.json()["status"] == "PENDENTE"
    assert r.json()["valor_pago"] is None
    assert r.json()["pago_em"] is None

    # O livro tem DOIS lançamentos: o original intacto e o contrário.
    movimentos = db_session.query(MovimentacaoFinanceira).order_by(
        MovimentacaoFinanceira.id
    ).all()
    assert len(movimentos) == 2, "estorno INSERE, nunca apaga"
    assert movimentos[0].tipo == "SAIDA"
    assert movimentos[1].tipo == "ENTRADA"
    assert movimentos[0].valor == movimentos[1].valor
    assert "Estorno" in (movimentos[1].motivo or "")


def test_estorno_exige_motivo(client, db_session):
    header = _auth(client)
    conta = _criar_conta(client, header)
    client.post(f"/api/v1/financeiro/contas-pagar/{conta['id']}/pagar",
                json={}, headers=header)

    r = client.post(f"/api/v1/financeiro/contas-pagar/{conta['id']}/estornar",
                    json={}, headers=header)
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_nao_estorna_conta_que_nao_foi_paga(client, db_session):
    header = _auth(client)
    conta = _criar_conta(client, header)
    r = client.post(f"/api/v1/financeiro/contas-pagar/{conta['id']}/estornar",
                    json={"motivo": "engano"}, headers=header)
    assert r.status_code == status.HTTP_400_BAD_REQUEST


def test_conta_volta_a_ser_pagavel_depois_do_estorno(client, db_session):
    """O ciclo completo: paga, estorna, paga de novo. Três lançamentos no livro."""
    header = _auth(client)
    conta = _criar_conta(client, header)
    base = f"/api/v1/financeiro/contas-pagar/{conta['id']}"

    client.post(f"{base}/pagar", json={}, headers=header)
    client.post(f"{base}/estornar", json={"motivo": "valor errado"}, headers=header)
    r = client.post(f"{base}/pagar", json={"valor_pago": 240000}, headers=header)

    assert r.status_code == status.HTTP_200_OK, r.text
    assert r.json()["valor_pago"] == 240000
    assert db_session.query(MovimentacaoFinanceira).count() == 3


# ===========================================================================
# LISTAGEM E RESUMO
# ===========================================================================

def test_totais_vem_do_filtro_inteiro_e_nao_da_pagina(client, db_session):
    """Somar no frontend daria o total da página; a diferença só apareceria
    quando a loja já tivesse contas o bastante para paginar."""
    header = _auth(client)
    for i in range(5):
        _criar_conta(client, header, descricao=f"Conta {i}", valor=10000)

    r = client.get("/api/v1/financeiro/contas-pagar?limit=2", headers=header)
    dados = r.json()

    assert len(dados["itens"]) == 2, "a página respeita o limite"
    assert dados["total_itens"] == 5
    assert dados["total_pendente"] == 50000, "o total ignora a paginação"


def test_totais_ignoram_o_filtro_de_status(client, db_session):
    """O rodapé mostra pendente, pago e vencido lado a lado — aplicar o status
    faria dois deles virarem zero sempre que o usuário filtrasse por um."""
    header = _auth(client)
    a = _criar_conta(client, header, descricao="A", valor=10000)
    _criar_conta(client, header, descricao="B", valor=30000)
    client.post(f"/api/v1/financeiro/contas-pagar/{a['id']}/pagar",
                json={}, headers=header)

    dados = client.get("/api/v1/financeiro/contas-pagar?status=PENDENTE",
                       headers=header).json()
    assert dados["total_itens"] == 1
    assert dados["total_pendente"] == 30000
    assert dados["total_pago"] == 10000, "o pago continua visível no rodapé"


def test_resumo_desconta_a_despesa_do_faturamento(client, db_session):
    header = _auth(client)
    conta = _criar_conta(client, header, valor=80000)
    client.post(f"/api/v1/financeiro/contas-pagar/{conta['id']}/pagar",
                json={}, headers=header)

    hoje = date.today().isoformat()
    r = client.get(
        f"/api/v1/financeiro/resumo?inicio={hoje}&fim={hoje}", headers=header
    )
    assert r.status_code == status.HTTP_200_OK, r.text
    resumo = r.json()

    assert resumo["despesas_pagas"] == 80000
    # Sem vendas no período, o resultado é o negativo da despesa — e o módulo
    # tem que conseguir dizer isso em vez de mostrar zero.
    assert resumo["resultado"] == resumo["faturamento"] - 80000
    assert resumo["a_pagar_pendente"] == 0


def test_resumo_agrupa_despesa_por_categoria(client, db_session):
    header = _auth(client)
    categorias = client.get("/api/v1/financeiro/plano-contas", headers=header).json()
    aluguel = next(c for c in categorias if "Aluguel" in c["nome"])

    conta = _criar_conta(client, header, valor=120000, plano_conta_id=aluguel["id"])
    client.post(f"/api/v1/financeiro/contas-pagar/{conta['id']}/pagar",
                json={}, headers=header)

    hoje = date.today().isoformat()
    resumo = client.get(
        f"/api/v1/financeiro/resumo?inicio={hoje}&fim={hoje}", headers=header
    ).json()

    linha = next(c for c in resumo["despesas_por_categoria"] if c["nome"] == aluguel["nome"])
    assert linha["total"] == 120000


def test_conta_bancaria_padrao_e_criada_sozinha(client, db_session):
    """O lojista que só usa dinheiro nunca vai cadastrar banco nenhum, e sem
    nenhuma conta a baixa exigiria criar uma antes."""
    header = _auth(client)
    r = client.get("/api/v1/financeiro/contas-bancarias", headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text

    contas = r.json()
    assert len(contas) == 1
    assert contas[0]["tipo"] == "CAIXA"
    assert contas[0]["principal"] is True


def test_recorrente_nao_infla_o_em_aberto_do_mes_visto(client, db_session):
    """O caso que o primeiro uso real pegou.

    Pagar a conta de um mês cria a do mês SEGUINTE pela recorrência. Se o card
    "a pagar em aberto" não tivesse teto de data, uma sairia da soma e a outra
    entraria — e o total ficaria parado depois do pagamento, como se nada
    tivesse sido pago.
    """
    header = _auth(client)
    hoje = date.today()
    primeiro = hoje.replace(day=1)
    ultimo_dia = (primeiro + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    # Duas contas vencendo neste mês; uma delas repete.
    internet = _criar_conta(
        client, header, descricao="Internet", valor=8000,
        vencimento=ultimo_dia.isoformat(), recorrente=True,
    )
    _criar_conta(
        client, header, descricao="Água", valor=7000,
        vencimento=ultimo_dia.isoformat(),
    )

    def em_aberto() -> int:
        r = client.get(
            f"/api/v1/financeiro/resumo?inicio={primeiro}&fim={ultimo_dia}",
            headers=header,
        )
        assert r.status_code == status.HTTP_200_OK, r.text
        return r.json()["a_pagar_pendente"]

    assert em_aberto() == 15000

    client.post(f"/api/v1/financeiro/contas-pagar/{internet['id']}/pagar",
                json={}, headers=header)

    # A internet do mês que vem existe e está pendente...
    todas = client.get("/api/v1/financeiro/contas-pagar?status=PENDENTE",
                       headers=header).json()
    assert todas["total_itens"] == 2, "a recorrência criou a do mês seguinte"

    # ...mas ela vence DEPOIS deste mês, e por isso não entra neste card.
    assert em_aberto() == 7000, "sobrou só a água"


def test_atrasado_de_mes_anterior_continua_no_em_aberto(client, db_session):
    """O teto é só para frente: dívida velha não some com o mês que passou."""
    header = _auth(client)
    hoje = date.today()
    primeiro = hoje.replace(day=1)
    ultimo_dia = (primeiro + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    _criar_conta(
        client, header, descricao="Aluguel atrasado", valor=250000,
        vencimento=(primeiro - timedelta(days=20)).isoformat(),
    )

    resumo = client.get(
        f"/api/v1/financeiro/resumo?inicio={primeiro}&fim={ultimo_dia}", headers=header
    ).json()

    assert resumo["a_pagar_pendente"] == 250000
    assert resumo["a_pagar_vencido"] == 250000


# ===========================================================================
# PARCELAMENTO
#
# Mecanismo DIFERENTE da recorrencia, e os testes daqui existem para travar a
# diferenca: parcelado nasce inteiro (as dez ja sao divida hoje), recorrente
# nasce uma por vez (a luz de dezembro ainda nao tem valor).
# ===========================================================================

def test_parcelamento_gera_todas_as_parcelas_de_uma_vez(client, db_session):
    """Se nascessem conforme o pagamento, o fluxo de caixa de dezembro ficaria
    cego para a parcela de dezembro e diria que sobra dinheiro comprometido."""
    header = _auth(client)
    primeira = _criar_conta(
        client, header, descricao="Cartão Nubank", valor=10000,
        vencimento=date(2026, 9, 10).isoformat(), parcelas=10,
    )

    assert primeira["parcela_numero"] == 1
    assert primeira["parcela_total"] == 10
    # A primeira aponta para si mesma: o grupo é o id dela.
    assert primeira["parcelamento_id"] == primeira["id"]

    lista = client.get("/api/v1/financeiro/contas-pagar?status=PENDENTE",
                       headers=header).json()
    assert lista["total_itens"] == 10
    # Cada parcela vale o valor digitado — nada de dividir e sobrar centavo.
    assert lista["total_pendente"] == 100000

    numeros = sorted(i["parcela_numero"] for i in lista["itens"])
    assert numeros == list(range(1, 11))
    assert {i["parcelamento_id"] for i in lista["itens"]} == {primeira["id"]}


def test_parcelas_caem_um_mes_apos_a_outra(client, db_session):
    header = _auth(client)
    _criar_conta(
        client, header, descricao="Notebook", valor=50000,
        vencimento=date(2026, 11, 15).isoformat(), parcelas=4,
    )
    itens = client.get("/api/v1/financeiro/contas-pagar?status=PENDENTE",
                       headers=header).json()["itens"]
    vencimentos = sorted(i["vencimento"] for i in itens)
    assert vencimentos == ["2026-11-15", "2026-12-15", "2027-01-15", "2027-02-15"]


def test_parcela_de_dia_31_encolhe_em_mes_curto(client, db_session):
    """Dia 31 em mês de 30 cai no dia 30, e NUNCA vaza para o dia 1º do mês
    seguinte — isso atrasaria o alerta em um mês inteiro."""
    header = _auth(client)
    _criar_conta(
        client, header, descricao="Financiamento", valor=20000,
        vencimento=date(2026, 1, 31).isoformat(), parcelas=3,
    )
    itens = client.get("/api/v1/financeiro/contas-pagar?status=PENDENTE",
                       headers=header).json()["itens"]
    vencimentos = sorted(i["vencimento"] for i in itens)
    assert vencimentos == ["2026-01-31", "2026-02-28", "2026-03-31"]


def test_parcelado_e_recorrente_juntos_e_recusado(client, db_session):
    """Aceitar os dois geraria dez parcelas e, na baixa de cada uma, mais uma
    conta 'do mês seguinte' — multiplicando a dívida a cada pagamento."""
    header = _auth(client)
    r = client.post("/api/v1/financeiro/contas-pagar", json={
        "descricao": "Impossível", "valor": 10000,
        "vencimento": date.today().isoformat(),
        "parcelas": 10, "recorrente": True,
    }, headers=header)
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_pagar_uma_parcela_nao_gera_outra(client, db_session):
    """A diferença central: parcelado tem fim, então a baixa não cria nada."""
    header = _auth(client)
    primeira = _criar_conta(
        client, header, descricao="TV em 3x", valor=30000,
        vencimento=date(2026, 9, 5).isoformat(), parcelas=3,
    )
    client.post(f"/api/v1/financeiro/contas-pagar/{primeira['id']}/pagar",
                json={}, headers=header)

    todas = client.get("/api/v1/financeiro/contas-pagar", headers=header).json()
    assert todas["total_itens"] == 3, "a recorrência criaria uma 4ª; o parcelamento não"
    assert todas["total_pago"] == 30000
    assert todas["total_pendente"] == 60000


def test_conta_sem_parcelamento_nao_ganha_marca(client, db_session):
    """1x é conta comum, e não parcelamento de uma parcela — a tela não deve
    mostrar '1/1' em toda conta avulsa."""
    header = _auth(client)
    conta = _criar_conta(client, header, descricao="Conta única", valor=5000)
    assert conta["parcelamento_id"] is None
    assert conta["parcela_numero"] is None
    assert conta["parcela_total"] is None


# ===========================================================================
# RECORRENCIA: DESFAZER A CONSEQUENCIA
#
# Encontrado no uso real: estornar devolvia a conta para pendente mas deixava
# a ocorrencia do mes seguinte, e a loja aparentava dever duas internets.
# ===========================================================================

def _contas_pendentes(client, header):
    return client.get("/api/v1/financeiro/contas-pagar?status=PENDENTE",
                      headers=header).json()


def test_estorno_remove_a_ocorrencia_que_o_pagamento_criou(client, db_session):
    header = _auth(client)
    conta = _criar_conta(client, header, descricao="Internet", valor=8000,
                         recorrente=True)
    base = f"/api/v1/financeiro/contas-pagar/{conta['id']}"

    client.post(f"{base}/pagar", json={}, headers=header)
    assert _contas_pendentes(client, header)["total_itens"] == 1, "nasceu a do mês seguinte"

    client.post(f"{base}/estornar", json={"motivo": "paguei em duplicidade"},
                headers=header)

    pendentes = _contas_pendentes(client, header)
    assert pendentes["total_itens"] == 1, "só a original volta; a gerada some"
    assert pendentes["itens"][0]["id"] == conta["id"]


def test_estornar_e_pagar_de_novo_nao_multiplica_a_divida(client, db_session):
    """O efeito composto do mesmo defeito: cada ciclo criava mais uma."""
    header = _auth(client)
    conta = _criar_conta(client, header, descricao="Internet", valor=8000,
                         recorrente=True)
    base = f"/api/v1/financeiro/contas-pagar/{conta['id']}"

    for _ in range(3):
        client.post(f"{base}/pagar", json={}, headers=header)
        client.post(f"{base}/estornar", json={"motivo": "errado de novo"},
                    headers=header)

    client.post(f"{base}/pagar", json={}, headers=header)

    todas = client.get("/api/v1/financeiro/contas-pagar", headers=header).json()
    assert todas["total_itens"] == 2, "a original mais UMA do mês seguinte, sempre"


def test_estorno_preserva_ocorrencia_que_ja_foi_paga(client, db_session):
    """Se houve decisão de gente no meio, apagar levaria junto um pagamento
    de verdade."""
    header = _auth(client)
    conta = _criar_conta(client, header, descricao="Internet", valor=8000,
                         recorrente=True)
    client.post(f"/api/v1/financeiro/contas-pagar/{conta['id']}/pagar",
                json={}, headers=header)

    proxima = _contas_pendentes(client, header)["itens"][0]
    client.post(f"/api/v1/financeiro/contas-pagar/{proxima['id']}/pagar",
                json={}, headers=header)

    client.post(f"/api/v1/financeiro/contas-pagar/{conta['id']}/estornar",
                json={"motivo": "mês errado"}, headers=header)

    ids = {i["id"] for i in client.get("/api/v1/financeiro/contas-pagar",
                                       headers=header).json()["itens"]}
    assert proxima["id"] in ids, "a ocorrência paga não pode ser apagada"


def test_parcelamento_nao_e_afetado_pelo_estorno(client, db_session):
    """Parcelas nascem juntas no cadastro; nenhuma é consequência da baixa de
    outra, então estornar uma não pode encostar nas demais."""
    header = _auth(client)
    primeira = _criar_conta(client, header, descricao="Cartão", valor=10000,
                            parcelas=3)
    base = f"/api/v1/financeiro/contas-pagar/{primeira['id']}"

    client.post(f"{base}/pagar", json={}, headers=header)
    client.post(f"{base}/estornar", json={"motivo": "engano"}, headers=header)

    assert client.get("/api/v1/financeiro/contas-pagar",
                      headers=header).json()["total_itens"] == 3


# ===========================================================================
# CONTAS A RECEBER — baixa e estorno (Onda 2A)
# ===========================================================================

def _criar_receber(client, header, **kwargs):
    payload = {
        "descricao": "Fiado do Joao",
        "valor": 20000,
        "vencimento": (date.today() + timedelta(days=15)).isoformat(),
    }
    payload.update(kwargs)
    r = client.post("/api/v1/financeiro/contas-receber", json=payload, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    return r.json()


def test_receber_gera_entrada_no_livro(client, db_session):
    from app.db.models.movimentacao_financeira import MovimentacaoFinanceira

    header = _auth(client)
    conta = _criar_receber(client, header)
    assert conta["status"] == "PENDENTE"
    assert conta["automatica"] is False, "lançada à mão"

    r = client.post(f"/api/v1/financeiro/contas-receber/{conta['id']}/receber",
                    json={}, headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    assert r.json()["status"] == "RECEBIDA"
    assert r.json()["valor_recebido"] == 20000

    movimentos = db_session.query(MovimentacaoFinanceira).all()
    assert len(movimentos) == 1
    assert movimentos[0].tipo == "ENTRADA"
    assert movimentos[0].origem == "RECEBIMENTO"
    # Quitar dívida antiga não é venda no PDV: não pertence a turno nenhum.
    assert movimentos[0].sessao_caixa_id is None


def test_recebimento_parcial_registra_o_que_entrou(client, db_session):
    """O cliente devia 200 e trouxe 150 — o livro conta o que entrou."""
    header = _auth(client)
    conta = _criar_receber(client, header)
    r = client.post(f"/api/v1/financeiro/contas-receber/{conta['id']}/receber",
                    json={"valor_recebido": 15000}, headers=header)
    assert r.json()["valor"] == 20000, "o previsto não muda"
    assert r.json()["valor_recebido"] == 15000


def test_estorno_de_recebimento_nao_apaga_o_lancamento(client, db_session):
    from app.db.models.movimentacao_financeira import MovimentacaoFinanceira

    header = _auth(client)
    conta = _criar_receber(client, header)
    base = f"/api/v1/financeiro/contas-receber/{conta['id']}"
    client.post(f"{base}/receber", json={}, headers=header)

    r = client.post(f"{base}/estornar", json={"motivo": "o cheque voltou"}, headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    assert r.json()["status"] == "PENDENTE"
    assert r.json()["valor_recebido"] is None

    movimentos = db_session.query(MovimentacaoFinanceira).order_by(
        MovimentacaoFinanceira.id
    ).all()
    assert len(movimentos) == 2, "estorno INSERE o contrário"
    assert movimentos[0].tipo == "ENTRADA"
    assert movimentos[1].tipo == "SAIDA"


def test_conta_recebida_nao_pode_ser_editada(client, db_session):
    header = _auth(client)
    conta = _criar_receber(client, header)
    client.post(f"/api/v1/financeiro/contas-receber/{conta['id']}/receber",
                json={}, headers=header)
    r = client.patch(f"/api/v1/financeiro/contas-receber/{conta['id']}",
                     json={"valor": 100}, headers=header)
    assert r.status_code == status.HTTP_400_BAD_REQUEST


def test_totais_de_receber_vem_do_filtro_inteiro(client, db_session):
    header = _auth(client)
    a = _criar_receber(client, header, descricao="A", valor=10000)
    _criar_receber(client, header, descricao="B", valor=30000)
    client.post(f"/api/v1/financeiro/contas-receber/{a['id']}/receber",
                json={}, headers=header)

    dados = client.get("/api/v1/financeiro/contas-receber?status=PENDENTE",
                       headers=header).json()
    assert dados["total_itens"] == 1
    assert dados["total_pendente"] == 30000
    assert dados["total_recebido"] == 10000, "o recebido segue visível no rodapé"


def test_cancelar_cobranca_nao_exclui(client, db_session):
    header = _auth(client)
    conta = _criar_receber(client, header)
    r = client.delete(f"/api/v1/financeiro/contas-receber/{conta['id']}", headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    assert r.json()["status"] == "CANCELADA"

    todas = client.get("/api/v1/financeiro/contas-receber", headers=header).json()
    assert todas["total_itens"] == 1, "continua na lista, como cancelada"


def test_juros_de_atraso_fica_separado_do_principal(client, db_session):
    """Juros de mora e receita FINANCEIRA, nao venda: somado ao principal ele
    inflaria o faturamento com dinheiro que nao veio de mercadoria."""
    from app.db.models.movimentacao_financeira import MovimentacaoFinanceira

    header = _auth(client)
    conta = _criar_receber(client, header, valor=20000)

    r = client.post(f"/api/v1/financeiro/contas-receber/{conta['id']}/receber",
                    json={"juros": 1500}, headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    dados = r.json()

    assert dados["valor"] == 20000, "o principal nao muda"
    assert dados["juros"] == 1500
    # Sem valor_recebido no payload, o padrao ja soma os juros.
    assert dados["valor_recebido"] == 21500

    # O livro registra o TOTAL que entrou.
    mov = db_session.query(MovimentacaoFinanceira).one()
    assert mov.valor == 21500


def test_forma_de_pagamento_do_recebimento_vai_para_o_livro(client, db_session):
    from app.db.models.movimentacao_financeira import MovimentacaoFinanceira

    header = _auth(client)
    fp = client.post("/api/v1/formas-pagamento/",
                     json={"nome": "PIX", "ativo": True}, headers=header).json()
    conta = _criar_receber(client, header)

    client.post(f"/api/v1/financeiro/contas-receber/{conta['id']}/receber",
                json={"forma_pagamento_id": fp["id"]}, headers=header)

    mov = db_session.query(MovimentacaoFinanceira).one()
    assert mov.forma_pagamento_id == fp["id"]


def test_estorno_zera_o_juros(client, db_session):
    """O juros existia por causa daquele recebimento; deixa-lo para tras faria a
    proxima baixa somar multa duas vezes."""
    header = _auth(client)
    conta = _criar_receber(client, header, valor=20000)
    base = f"/api/v1/financeiro/contas-receber/{conta['id']}"

    client.post(f"{base}/receber", json={"juros": 1500}, headers=header)
    r = client.post(f"{base}/estornar", json={"motivo": "cobranca indevida"},
                    headers=header)

    assert r.json()["juros"] == 0
    assert r.json()["valor_recebido"] is None


def test_juros_da_maquininha_nao_entra_no_caixa_da_loja(client, db_session):
    """O cliente desembolsa o total, mas o juros do parcelamento vai para a
    operadora. Lancar tudo mostraria saldo que a conta bancaria nao tem."""
    from app.db.models.movimentacao_financeira import MovimentacaoFinanceira

    header = _auth(client)
    conta = _criar_receber(client, header, valor=20000)

    r = client.post(
        f"/api/v1/financeiro/contas-receber/{conta['id']}/receber",
        json={"juros": 1500, "juros_destino": "OPERADORA"}, headers=header,
    )
    assert r.status_code == status.HTTP_200_OK, r.text
    dados = r.json()

    # O documento guarda o que o CLIENTE desembolsou...
    assert dados["valor_recebido"] == 21500
    assert dados["juros"] == 1500
    assert dados["juros_destino"] == "OPERADORA"

    # ...e o livro, o que entrou na LOJA.
    mov = db_session.query(MovimentacaoFinanceira).one()
    assert mov.valor == 20000, "os juros da maquininha nao sao dinheiro da loja"
    assert "operadora" in (mov.motivo or "").lower()


def test_estorno_devolve_so_o_que_tinha_entrado(client, db_session):
    """O juros da operadora nunca virou movimento; estorna-lo tiraria do caixa
    dinheiro que nunca esteve la."""
    from app.db.models.movimentacao_financeira import MovimentacaoFinanceira

    header = _auth(client)
    conta = _criar_receber(client, header, valor=20000)
    base = f"/api/v1/financeiro/contas-receber/{conta['id']}"

    client.post(f"{base}/receber",
                json={"juros": 1500, "juros_destino": "OPERADORA"}, headers=header)
    client.post(f"{base}/estornar", json={"motivo": "engano"}, headers=header)

    movimentos = db_session.query(MovimentacaoFinanceira).order_by(
        MovimentacaoFinanceira.id
    ).all()
    assert len(movimentos) == 2
    assert movimentos[0].valor == movimentos[1].valor == 20000, "entra e sai o mesmo"


def test_multa_por_atraso_continua_entrando_no_caixa(client, db_session):
    """O padrao e LOJA, e o caso da esmagadora maioria."""
    from app.db.models.movimentacao_financeira import MovimentacaoFinanceira

    header = _auth(client)
    conta = _criar_receber(client, header, valor=20000)
    client.post(f"/api/v1/financeiro/contas-receber/{conta['id']}/receber",
                json={"juros": 1500}, headers=header)

    mov = db_session.query(MovimentacaoFinanceira).one()
    assert mov.valor == 21500, "multa por atraso e receita da loja"


def test_resumo_soma_todo_o_a_receber_independente_do_vencimento(client, db_session):
    """O card do receber NÃO tem o teto de data que o a pagar tem.

    Fiado vendido em agosto costuma vencer em setembro, e a Visão Geral não
    deixa avançar de mês — com teto, o dono nunca veria o dinheiro que está na
    rua. Aqui entram os três: o deste mês, o atrasado e o do mês que vem.
    """
    header = _auth(client)
    hoje = date.today()
    primeiro = hoje.replace(day=1)
    ultimo_dia = (primeiro + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    _criar_receber(client, header, descricao="Fiado deste mes", valor=30000,
                   vencimento=ultimo_dia.isoformat())
    _criar_receber(client, header, descricao="Fiado atrasado", valor=12000,
                   vencimento=(primeiro - timedelta(days=10)).isoformat())
    _criar_receber(client, header, descricao="Fiado do mes que vem", valor=99900,
                   vencimento=(ultimo_dia + timedelta(days=5)).isoformat())

    resumo = client.get(
        f"/api/v1/financeiro/resumo?inicio={primeiro}&fim={ultimo_dia}", headers=header
    ).json()

    assert resumo["a_receber_pendente"] == 141900, "o do mês que vem também conta"
    assert resumo["a_receber_vencido"] == 12000


def test_receber_baixado_sai_do_a_receber_sem_mexer_no_resultado(client, db_session):
    """Fiado recebido não é faturamento novo — a venda já foi contada quando fechou.

    Se a baixa somasse em `faturamento`, o mesmo dinheiro apareceria duas vezes:
    uma na venda a prazo e outra no recebimento.
    """
    header = _auth(client)
    hoje = date.today()
    primeiro = hoje.replace(day=1)
    ultimo_dia = (primeiro + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    url = f"/api/v1/financeiro/resumo?inicio={primeiro}&fim={ultimo_dia}"

    conta = _criar_receber(client, header, valor=20000,
                           vencimento=ultimo_dia.isoformat())
    antes = client.get(url, headers=header).json()
    assert antes["a_receber_pendente"] == 20000

    client.post(f"/api/v1/financeiro/contas-receber/{conta['id']}/receber",
                json={}, headers=header)

    depois = client.get(url, headers=header).json()
    assert depois["a_receber_pendente"] == 0, "saiu da rua"
    assert depois["faturamento"] == antes["faturamento"], "não é venda nova"
    assert depois["resultado"] == antes["resultado"]


# ===========================================================================
# DESFAZER O CANCELAMENTO, E CORRIGIR O PARCELAMENTO INTEIRO
#
# Os dois vieram do mesmo dia de uso real (05/09/2026), num emprestimo em 30x:
# o dono cancelou uma parcela sem querer e nao tinha como voltar, e descobriu
# que corrigir a data significava abrir 30 telas -- 72, na outra conta dele.
# ===========================================================================

def _todas(client, header, **params):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    return client.get(f"/api/v1/financeiro/contas-pagar?{q}", headers=header).json()


def test_conta_cancelada_por_engano_volta_para_em_aberto(client, db_session):
    """Cancelar era porta de mão única: a conta saía da lista e não voltava."""
    header = _auth(client)
    conta = _criar_conta(client, header, descricao="Energia Solar", valor=32000)
    base = f"/api/v1/financeiro/contas-pagar/{conta['id']}"

    client.delete(base, headers=header)
    assert client.get(base, headers=header).json()["status"] == "CANCELADA"

    r = client.post(f"{base}/reativar", headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    assert r.json()["status"] == "PENDENTE"
    # A MESMA linha: reativar não recria nada, senão o histórico se perderia.
    assert r.json()["id"] == conta["id"]
    assert r.json()["valor"] == 32000


def test_reativar_so_vale_para_conta_cancelada(client, db_session):
    """Numa conta em aberto o botão não faz sentido, e o backend precisa dizer
    isso — a tela pode falhar em esconder o botão, o contrato não."""
    header = _auth(client)
    conta = _criar_conta(client, header)
    r = client.post(
        f"/api/v1/financeiro/contas-pagar/{conta['id']}/reativar", headers=header
    )
    assert r.status_code == status.HTTP_400_BAD_REQUEST, r.text


def test_corrigir_o_vencimento_arruma_as_parcelas_seguintes(client, db_session):
    """Errou o dia numa compra em 6x: corrige uma e as outras acompanham.

    RE-ANCORA, não copia: cada parcela seguinte recebe o mesmo DIA, mês a mês.
    Copiar a data faria as cinco restantes vencerem todas no mesmo dia.
    """
    header = _auth(client)
    _criar_conta(client, header, descricao="Empréstimo", valor=70000,
                 vencimento=date(2027, 5, 3).isoformat(), parcelas=6)

    itens = sorted(_todas(client, header, limit=50)["itens"],
                   key=lambda c: c["parcela_numero"])
    assert [c["vencimento"] for c in itens[:3]] == [
        "2027-05-03", "2027-06-03", "2027-07-03",
    ]

    # O dono corrige a PRIMEIRA: era dia 3, o certo é 22.
    r = client.patch(
        f"/api/v1/financeiro/contas-pagar/{itens[0]['id']}",
        json={"vencimento": "2027-05-22", "aplicar_nas_proximas": True},
        headers=header,
    )
    assert r.status_code == status.HTTP_200_OK, r.text

    depois = sorted(_todas(client, header, limit=50)["itens"],
                    key=lambda c: c["parcela_numero"])
    assert [c["vencimento"] for c in depois] == [
        "2027-05-22", "2027-06-22", "2027-07-22",
        "2027-08-22", "2027-09-22", "2027-10-22",
    ]


def test_dia_30_encolhe_em_fevereiro_e_volta_em_marco(client, db_session):
    """A pergunta do dono: "tem mês que é de 28 dias, e aí?".

    Encolhe só no mês curto e VOLTA — porque a âncora é a primeira parcela, não
    a parcela anterior. Ancorar na anterior faria 30/jan virar 28/fev e depois
    ficar 28 para sempre, e o erro cresceria em silêncio ao longo das 72.
    """
    header = _auth(client)
    _criar_conta(client, header, descricao="Prestação", valor=70000,
                 vencimento=date(2027, 12, 30).isoformat(), parcelas=4)

    itens = sorted(_todas(client, header, limit=50)["itens"],
                   key=lambda c: c["parcela_numero"])
    assert [c["vencimento"] for c in itens] == [
        "2027-12-30",
        "2028-01-30",
        "2028-02-29",  # ano bissexto: encolhe para o último dia
        "2028-03-30",  # e VOLTA para 30
    ]


def test_propagacao_nao_encosta_no_que_ja_foi_pago(client, db_session):
    """Parcela paga já virou lançamento no livro. Mexer nela faria o relatório
    do mês discordar do movimento."""
    header = _auth(client)
    _criar_conta(client, header, descricao="Financiamento", valor=50000,
                 vencimento=date(2027, 5, 10).isoformat(), parcelas=4)

    itens = sorted(_todas(client, header, limit=50)["itens"],
                   key=lambda c: c["parcela_numero"])
    # Paga a 3ª, depois corrige a 1ª pedindo propagação.
    client.post(f"/api/v1/financeiro/contas-pagar/{itens[2]['id']}/pagar",
                json={}, headers=header)
    client.patch(
        f"/api/v1/financeiro/contas-pagar/{itens[0]['id']}",
        json={"vencimento": "2027-05-25", "aplicar_nas_proximas": True},
        headers=header,
    )

    depois = {c["parcela_numero"]: c for c in _todas(client, header, limit=50)["itens"]}
    assert depois[1]["vencimento"] == "2027-05-25"
    assert depois[2]["vencimento"] == "2027-06-25"
    assert depois[3]["vencimento"] == "2027-07-10", "a paga fica congelada"
    assert depois[4]["vencimento"] == "2027-08-25"


def test_sem_a_flag_so_a_conta_editada_muda(client, db_session):
    """O padrão continua sendo mexer numa só — prorrogar UM boleto é rotina, e
    ninguém quer que isso arraste o parcelamento inteiro."""
    header = _auth(client)
    _criar_conta(client, header, descricao="Compra", valor=30000,
                 vencimento=date(2027, 5, 10).isoformat(), parcelas=3)

    itens = sorted(_todas(client, header, limit=50)["itens"],
                   key=lambda c: c["parcela_numero"])
    client.patch(f"/api/v1/financeiro/contas-pagar/{itens[0]['id']}",
                 json={"vencimento": "2027-05-25"}, headers=header)

    depois = sorted(_todas(client, header, limit=50)["itens"],
                    key=lambda c: c["parcela_numero"])
    assert [c["vencimento"] for c in depois] == [
        "2027-05-25", "2027-06-10", "2027-07-10",
    ]
