# ---------------------------------------------------------------------------
# Alertas de tendência (Fase 3) e projeção de 12 meses (Fase 4).
#
# Alerta de tendência erra mais que alerta de estado: "vencido" é fato,
# "caindo" é leitura. Por isso metade deste arquivo testa o caso que NÃO deve
# disparar — um limiar frouxo enche o painel de alarme falso, e um painel que
# grita todo mês deixa de ser lido.
#
# A projeção é a leitura mais arriscada do módulo. O teste que mais importa é o
# que prova que ela NÃO EXISTE sem histórico: três pontos desenham qualquer
# coisa, e o dono decide em cima do que a tela mostrar.
# ---------------------------------------------------------------------------

from datetime import date, datetime, timedelta

from starlette import status

from app.db.models.contador_venda import ContadorVenda
from app.db.models.venda import Venda

TEST_USER_EMAIL = "tendencia.dono@example.com"
TEST_USER_PASSWORD = "senhaSegura789"


# ===========================================================================
# HELPERS
# ===========================================================================

def _auth(client):
    client.post("/api/v1/usuarios/", json={
        "nome": "Dono da Tendencia", "email": TEST_USER_EMAIL, "senha": TEST_USER_PASSWORD,
    })
    login = client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": "hwid-tend",
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post("/api/v1/empresas/", json={
        "razao_social": "Tendencia LTDA", "nome_fantasia": "Tendencia", "is_cnpj": True,
        "documento": "12345678000188", "regime_tributario": "Simples Nacional",
        "celular": "11999997777", "segmento": "assistencia_tecnica",
        "endereco": [{"logradouro": "Av. Brasil", "numero": "500", "bairro": "Centro",
                      "cidade": "São Paulo", "estado": "SP", "cep": "01310-100"}],
    }, headers=header)
    return header


def _funcionario(client, header):
    r = client.post("/api/v1/funcionarios/", json={
        "nome": "Tecnico", "cpf": "11122233355", "contato": "11999999999",
        "usuario": {"nome": "tec", "email": "tec.tend@empresa.com", "senha": "SenhaForte123!"},
        "endereco": [{"logradouro": "Rua X", "numero": "1", "cep": "12345-678",
                      "bairro": "Centro", "cidade": "Lab City", "estado": "SP"}],
    }, headers=header)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _forma(client, header):
    r = client.post("/api/v1/formas-pagamento/", json={"nome": "Dinheiro", "ativo": True},
                    headers=header)
    return r.json()["id"] if r.status_code == 201 else 1


# Contador de codigo: dois meses com a MESMA receita gerariam o mesmo codigo de
# produto, e o cadastro recusa duplicado com 409.
_SEQUENCIA = {"n": 0}


def _produto(client, header, valor):
    _SEQUENCIA["n"] += 1
    r = client.post("/api/v1/produtos/", json={
        "nome": f"Produto {valor}", "codigo_produto": f"P{_SEQUENCIA['n']}",
        "unidade_medida": "UN",
        "estoque": {"valor_varejo": valor, "quantidade": 999},
    }, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _mes_atras(n: int) -> datetime:
    hoje = date.today()
    ano, mes = hoje.year, hoje.month - n
    while mes <= 0:
        mes += 12
        ano -= 1
    return datetime(ano, mes, 15, 12, 0, 0)


def _receita_em(db_session, client, header, funcionario_id, fp_id, valor, quando):
    """Uma venda de `valor` centavos, carimbada no mês pedido."""
    if not db_session.query(ContadorVenda).first():
        db_session.add(ContadorVenda(id=1, proximo_numero=1))
        db_session.commit()

    produto_id = _produto(client, header, valor)
    venda_id = client.post("/api/v1/vendas/", json={"funcionario_id": funcionario_id},
                           headers=header).json()["id"]
    add = client.post(f"/api/v1/vendas/{venda_id}/itens", json={
        "tipo_produto": "CADASTRADO", "produto_id": produto_id, "quantidade": 1,
    }, headers=header)
    assert add.status_code == 201, add.text
    total = add.json()["financeiro_atualizado"]["total"]
    client.post(f"/api/v1/vendas/{venda_id}/finalizar", json={
        "pagamentos": [{"forma_pagamento_id": fp_id, "valor": total,
                        "parcelado": False, "qtd_parcelas": None}],
    }, headers=header)

    registro = db_session.query(Venda).filter(Venda.id == venda_id).first()
    registro.criado_em = quando
    db_session.commit()


def _alertas(client, header):
    hoje = date.today()
    primeiro = hoje.replace(day=1)
    ultimo = (primeiro + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    r = client.get(f"/api/v1/financeiro/resumo?inicio={primeiro}&fim={ultimo}",
                   headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    return {a["codigo"]: a for a in r.json()["alertas"]}


def _projecao(client, header):
    r = client.get("/api/v1/financeiro/projecao", headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    return r.json()


# ===========================================================================
# RECEITA CAINDO — e o caso que NÃO deve disparar
# ===========================================================================

def test_receita_caindo_tres_meses_seguidos_alerta(client, db_session):
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)

    for n, valor in ((4, 100000), (3, 80000), (2, 60000), (1, 40000)):
        _receita_em(db_session, client, header, funcionario_id, fp_id, valor, _mes_atras(n))

    alerta = _alertas(client, header)["RECEITA_CAINDO"]
    assert alerta["severidade"] == "CRITICO", "caiu 60% no periodo"
    assert alerta["quantidade"] == 3


def test_um_mes_ruim_no_meio_nao_e_tendencia(client, db_session):
    """O caso que mais importa não disparar.

    Loja pequena tem mês ruim. Chamar isso de tendência ensinaria o dono a
    ignorar o painel — e junto some o aviso que importava.
    """
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)

    for n, valor in ((4, 100000), (3, 60000), (2, 90000), (1, 95000)):
        _receita_em(db_session, client, header, funcionario_id, fp_id, valor, _mes_atras(n))

    assert "RECEITA_CAINDO" not in _alertas(client, header)


def test_sem_historico_nao_ha_alerta_de_tendencia(client, db_session):
    """Dizer "sua receita esta caindo" com dois meses seria transformar acaso
    em diagnostico."""
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)

    _receita_em(db_session, client, header, funcionario_id, fp_id, 100000, _mes_atras(2))
    _receita_em(db_session, client, header, funcionario_id, fp_id, 50000, _mes_atras(1))

    alertas = _alertas(client, header)
    assert "RECEITA_CAINDO" not in alertas
    assert "ORIGEM_CAINDO" not in alertas


# ===========================================================================
# ORIGEM CAINDO
# ===========================================================================

def test_origem_que_encolheu_vira_alerta_com_o_rotulo(client, db_session):
    """O backend manda o ROTULO (dado), nao a frase pronta."""
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)

    for n in (4, 3, 2):
        _receita_em(db_session, client, header, funcionario_id, fp_id, 100000, _mes_atras(n))
    _receita_em(db_session, client, header, funcionario_id, fp_id, 20000, _mes_atras(1))

    alerta = _alertas(client, header)["ORIGEM_CAINDO"]
    assert alerta["rotulo"] == "Vendas"
    assert alerta["quantidade"] == 80, "caiu 80% contra a media de tres meses"


# ===========================================================================
# PROJEÇÃO
# ===========================================================================

def test_sem_seis_meses_a_projecao_nao_existe(client, db_session):
    """O teste mais importante da fase: tres pontos desenham qualquer coisa."""
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)
    for n in (3, 2, 1):
        _receita_em(db_session, client, header, funcionario_id, fp_id, 100000, _mes_atras(n))

    projecao = _projecao(client, header)
    assert projecao["disponivel"] is False
    assert projecao["meses_faltando"] == 3
    assert projecao["meses"] == []


def test_com_seis_meses_projeta_pela_media(client, db_session):
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)
    for n in range(6, 0, -1):
        _receita_em(db_session, client, header, funcionario_id, fp_id, 100000, _mes_atras(n))

    projecao = _projecao(client, header)
    assert projecao["disponivel"] is True
    assert projecao["receita_mensal"] == 100000, "media dos tres ultimos"
    assert projecao["receita_12_meses"] == 1200000
    assert len(projecao["meses"]) == 12
    assert projecao["meses"][0]["mes"] > date.today().strftime("%Y-%m"), "comeca no mes que vem"
    assert projecao["meses"][-1]["acumulado"] == projecao["resultado_12_meses"]


def test_a_faixa_e_mais_larga_para_a_loja_instavel(client, db_session):
    """Loja de altos e baixos precisa saber que o sistema sabe menos sobre ela."""
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)
    for n, valor in ((6, 20000), (5, 200000), (4, 30000), (3, 180000), (2, 25000), (1, 190000)):
        _receita_em(db_session, client, header, funcionario_id, fp_id, valor, _mes_atras(n))

    instavel = _projecao(client, header)
    assert instavel["margem"] >= 0.4, "oscilacao enorme abre a faixa"
    assert instavel["piso_12_meses"] < instavel["resultado_12_meses"] < instavel["teto_12_meses"]


def test_a_projecao_nunca_extrapola_inclinacao(client, db_session):
    """Reta, nao tendencia.

    Se a projecao extrapolasse a queda, ela prometeria uma data de falencia. Com
    seis pontos isso erra feio, entao todos os meses projetados sao iguais.
    """
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)
    for n, valor in ((6, 200000), (5, 170000), (4, 140000), (3, 110000), (2, 80000), (1, 50000)):
        _receita_em(db_session, client, header, funcionario_id, fp_id, valor, _mes_atras(n))

    meses = _projecao(client, header)["meses"]
    assert len({m["receita"] for m in meses}) == 1, "todos os meses repetem a media"
