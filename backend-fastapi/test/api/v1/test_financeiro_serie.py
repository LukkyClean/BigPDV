# ---------------------------------------------------------------------------
# A série mensal que sustenta a tela de Análise (Fase 1).
#
# Dois testes mandam neste arquivo:
#
#   - o do MÊS CORRENTE, que prova que ele não entra na série. Comparar oito
#     dias com um mês inteiro acusaria queda todo início de mês, e é o erro
#     mais fácil de reintroduzir sem perceber.
#
#   - o da LOJA SEM OS, que prova que a origem não existe em vez de existir
#     zerada. É o que mantém a tela honesta num segmento PDV — e o frontend
#     nunca precisa saber que "OS" existe.
# ---------------------------------------------------------------------------

from datetime import date, datetime, timedelta

from starlette import status

from app.db.models.configuracao_vendas import ConfiguracaoVendas
from app.db.models.empresa import Empresa

TEST_USER_EMAIL = "serie.dono@example.com"
TEST_USER_PASSWORD = "senhaSegura789"


# ===========================================================================
# HELPERS
# ===========================================================================

def _auth(client, segmento="assistencia_tecnica"):
    client.post("/api/v1/usuarios/", json={
        "nome": "Dono da Analise", "email": TEST_USER_EMAIL, "senha": TEST_USER_PASSWORD,
    })
    login = client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": "hwid-serie",
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post("/api/v1/empresas/", json={
        "razao_social": "Analise LTDA", "nome_fantasia": "Analise", "is_cnpj": True,
        "documento": "12345678000188", "regime_tributario": "Simples Nacional",
        "celular": "11999997777", "segmento": segmento,
        "endereco": [{"logradouro": "Av. Brasil", "numero": "500", "bairro": "Centro",
                      "cidade": "São Paulo", "estado": "SP", "cep": "01310-100"}],
    }, headers=header)
    return header


def _segmento(db_session, valor: str):
    empresa = db_session.query(Empresa).first()
    empresa.segmento = valor
    db_session.commit()


def _funcionario(client, header):
    r = client.post("/api/v1/funcionarios/", json={
        "nome": "Tecnico", "cpf": "11122233355", "contato": "11999999999",
        "usuario": {"nome": "tec", "email": "tec.serie@empresa.com", "senha": "SenhaForte123!"},
        "endereco": [{"logradouro": "Rua X", "numero": "1", "cep": "12345-678",
                      "bairro": "Centro", "cidade": "Lab City", "estado": "SP"}],
    }, headers=header)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _forma(client, header):
    r = client.post("/api/v1/formas-pagamento/", json={"nome": "Dinheiro", "ativo": True},
                    headers=header)
    return r.json()["id"] if r.status_code == 201 else 1


def _produto(client, header, codigo="SERIE-1"):
    r = client.post("/api/v1/produtos/", json={
        "nome": f"Produto {codigo}", "codigo_produto": codigo, "unidade_medida": "UN",
        "estoque": {"valor_varejo": 5000, "quantidade": 100},
    }, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _venda_em(db_session, client, header, funcionario_id, produto_id, fp_id, quando):
    """Finaliza uma venda e REESCREVE a data para o mes desejado.

    Viajar no tempo pelo banco e o unico jeito de testar serie mensal sem
    esperar trinta dias.
    """
    from app.db.models.contador_venda import ContadorVenda
    from app.db.models.venda import Venda

    if not db_session.query(ContadorVenda).first():
        db_session.add(ContadorVenda(id=1, proximo_numero=1))
        db_session.commit()

    venda_id = client.post("/api/v1/vendas/", json={"funcionario_id": funcionario_id},
                           headers=header).json()["id"]
    add = client.post(f"/api/v1/vendas/{venda_id}/itens", json={
        "tipo_produto": "CADASTRADO", "produto_id": produto_id, "quantidade": 1,
    }, headers=header)
    assert add.status_code == 201, add.text
    total = add.json()["financeiro_atualizado"]["total"]

    fin = client.post(f"/api/v1/vendas/{venda_id}/finalizar", json={
        "pagamentos": [{"forma_pagamento_id": fp_id, "valor": total,
                        "parcelado": False, "qtd_parcelas": None}],
    }, headers=header)
    assert fin.status_code == 200, fin.text

    registro = db_session.query(Venda).filter(Venda.id == venda_id).first()
    registro.criado_em = quando
    db_session.commit()
    return total


def _serie(client, header, meses=12):
    r = client.get(f"/api/v1/financeiro/serie?meses={meses}", headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    return r.json()


def _mes_atras(n: int) -> datetime:
    """Dia 15 de N meses atrás — dia 15 nunca cai fora do mês."""
    hoje = date.today()
    ano, mes = hoje.year, hoje.month - n
    while mes <= 0:
        mes += 12
        ano -= 1
    return datetime(ano, mes, 15, 12, 0, 0)


# ===========================================================================
# O RECORTE
# ===========================================================================

def test_o_mes_corrente_nao_entra_na_serie(client, db_session):
    """Oito dias contra um mês inteiro acusaria queda todo início de mês."""
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)
    produto_id = _produto(client, header)

    # Venda de HOJE: fica de fora.
    _venda_em(db_session, client, header, funcionario_id, produto_id, fp_id,
              datetime.now())

    serie = _serie(client, header)
    meses = [m["mes"] for m in serie["meses"]]

    assert date.today().strftime("%Y-%m") not in meses
    assert all(m["receita"] == 0 for m in serie["meses"])
    assert serie["meses_disponiveis"] == 0, "a loja comecou neste mes"
    assert serie["primeiro_mes"] is None


def test_a_serie_vem_do_mais_antigo_para_o_mais_novo(client, db_session):
    header = _auth(client)
    _funcionario(client, header)

    serie = _serie(client, header, meses=6)
    meses = [m["mes"] for m in serie["meses"]]

    assert len(meses) == 6
    assert meses == sorted(meses), "e a ordem em que se le um grafico"
    assert meses[-1] != date.today().strftime("%Y-%m")


def test_venda_de_mes_passado_entra_com_origem_e_valor(client, db_session):
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)
    produto_id = _produto(client, header)

    total = _venda_em(db_session, client, header, funcionario_id, produto_id, fp_id,
                      _mes_atras(1))

    serie = _serie(client, header)
    mes = next(m for m in serie["meses"] if m["mes"] == _mes_atras(1).strftime("%Y-%m"))

    assert mes["receita"] == total
    venda = next(o for o in mes["origens"] if o["chave"] == "VENDA")
    assert venda["total"] == total
    assert venda["rotulo"] == "Vendas", "o rotulo vem pronto; a tela nao traduz nada"


# ===========================================================================
# HISTÓRICO — o que abre os portões da tela
# ===========================================================================

def test_meses_disponiveis_conta_do_primeiro_movimento(client, db_session):
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)
    produto_id = _produto(client, header)

    _venda_em(db_session, client, header, funcionario_id, produto_id, fp_id, _mes_atras(3))

    serie = _serie(client, header)
    assert serie["primeiro_mes"] == _mes_atras(3).strftime("%Y-%m")
    # Tres meses fechados: o do movimento e os dois seguintes.
    assert serie["meses_disponiveis"] == 3


def test_mes_parado_no_meio_continua_contando_como_historico(client, db_session):
    """Loja que nao vendeu em julho nao deixou de existir em julho.

    Se o mes vazio nao contasse, uma loja de ferias voltaria com o portao
    fechado -- e a comparacao que ela ja tinha direito sumiria da tela.
    """
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)
    produto_id = _produto(client, header)

    _venda_em(db_session, client, header, funcionario_id, produto_id, fp_id, _mes_atras(4))
    _venda_em(db_session, client, header, funcionario_id, produto_id, fp_id, _mes_atras(1))

    serie = _serie(client, header)
    assert serie["meses_disponiveis"] == 4, "conta o buraco do meio"

    vazio = next(m for m in serie["meses"] if m["mes"] == _mes_atras(2).strftime("%Y-%m"))
    assert vazio["receita"] == 0, "o mes vazio existe na serie, com zero"


# ===========================================================================
# SEGMENTO — a origem não existe, em vez de existir zerada
# ===========================================================================

def test_loja_sem_os_nao_recebe_a_origem_de_os(client, db_session):
    """O frontend nunca precisa saber que OS existe.

    Uma origem zerada ocuparia legenda, cor e espaco para nao dizer nada -- e
    numa adega "Servicos" seria exatamente isso.
    """
    header = _auth(client)
    _segmento(db_session, "pdv")
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)
    produto_id = _produto(client, header)
    _venda_em(db_session, client, header, funcionario_id, produto_id, fp_id, _mes_atras(1))

    serie = _serie(client, header)
    chaves = {o["chave"] for m in serie["meses"] for o in m["origens"]}

    assert chaves == {"VENDA"}


def test_origem_zerada_na_janela_inteira_sai(client, db_session):
    """Oficina que passou o periodo sem vender produto nao ganha linha reta."""
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)
    produto_id = _produto(client, header)
    _venda_em(db_session, client, header, funcionario_id, produto_id, fp_id, _mes_atras(1))

    serie = _serie(client, header)
    chaves = {o["chave"] for m in serie["meses"] for o in m["origens"]}

    # Segmento COM OS, mas nenhuma OS finalizada na janela: a origem sai.
    assert chaves == {"VENDA"}


# ===========================================================================
# O NÚMERO TEM QUE BATER COM A VISÃO GERAL
# ===========================================================================

def test_a_serie_bate_com_o_resumo_do_mesmo_mes(client, db_session):
    """Dois numeros para o mesmo mes destruiriam a confianca no modulo inteiro.

    Por isso a serie sai da MESMA fonte do card "Faturado" em vez de recalcular
    por conta propria.
    """
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)
    produto_id = _produto(client, header)
    _venda_em(db_session, client, header, funcionario_id, produto_id, fp_id, _mes_atras(1))

    alvo = _mes_atras(1)
    primeiro = alvo.date().replace(day=1)
    ultimo = (primeiro + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    resumo = client.get(
        f"/api/v1/financeiro/resumo?inicio={primeiro}&fim={ultimo}", headers=header
    ).json()

    mes = next(m for m in _serie(client, header)["meses"]
               if m["mes"] == alvo.strftime("%Y-%m"))

    assert mes["receita"] == resumo["faturamento"]
    assert mes["despesas_pagas"] == resumo["despesas_pagas"]
    assert mes["entrou_caixa"] == resumo["entrou_caixa"]


# ===========================================================================
# PRAZO MEDIO DE RECEBIMENTO
#
# Escolhido em vez do DSO classico (recebiveis / receita x dias) por uma razao
# so: o dono precisa poder conferir. "Seus clientes demoram 23 dias" se prova
# abrindo tres cobrancas e contando no calendario.
# ===========================================================================

def _receber_em(db_session, client, header, valor, criado_em, recebido_em):
    """Cria uma cobranca e reescreve as duas datas -- criacao e recebimento."""
    from app.db.models.conta_receber import ContaReceber

    conta = client.post("/api/v1/financeiro/contas-receber", json={
        "descricao": "Fiado", "valor": valor,
        "vencimento": recebido_em.date().isoformat(),
    }, headers=header).json()
    client.post(f"/api/v1/financeiro/contas-receber/{conta['id']}/receber",
                json={}, headers=header)

    registro = db_session.query(ContaReceber).filter(
        ContaReceber.id == conta["id"]
    ).first()
    registro.criado_em = criado_em
    registro.recebido_em = recebido_em
    db_session.commit()
    return registro


def _mes(serie, quando):
    return next(m for m in serie["meses"] if m["mes"] == quando.strftime("%Y-%m"))


def test_prazo_medio_e_a_media_dos_dias_ate_o_pagamento(client, db_session):
    header = _auth(client)
    _funcionario(client, header)

    alvo = _mes_atras(1)
    # Uma paga em 10 dias, outra em 20: a media e 15.
    _receber_em(db_session, client, header, 10000, alvo - timedelta(days=10), alvo)
    _receber_em(db_session, client, header, 10000, alvo - timedelta(days=20), alvo)

    assert _mes(_serie(client, header), alvo)["prazo_medio_recebimento"] == 15


def test_mes_sem_recebimento_devolve_nulo_e_nao_zero(client, db_session):
    """Zero diria que todo mundo pagou a vista. Nulo diz que nao houve.

    A tela usa essa diferenca: com nulo ela escreve "nenhuma cobranca a prazo
    foi quitada no mes", que e a verdade.
    """
    header = _auth(client)
    _funcionario(client, header)

    serie = _serie(client, header)
    assert all(m["prazo_medio_recebimento"] is None for m in serie["meses"])


def test_recebimento_lancado_antes_da_cobranca_nao_puxa_a_media(client, db_session):
    """Data invertida e digitacao, e contar -5 dias mentiria que a loja recebe rapido."""
    header = _auth(client)
    _funcionario(client, header)

    alvo = _mes_atras(1)
    _receber_em(db_session, client, header, 10000, alvo + timedelta(days=5), alvo)
    _receber_em(db_session, client, header, 10000, alvo - timedelta(days=8), alvo)

    assert _mes(_serie(client, header), alvo)["prazo_medio_recebimento"] == 8
