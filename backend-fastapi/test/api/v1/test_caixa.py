# ---------------------------------------------------------------------------
# Testes do turno de caixa (fase 2 do PDV).
#
# O teste mais importante deste arquivo e o PRIMEIRO: com o controle de caixa
# desligado -- que e o padrao e o estado das tres lojas em producao -- finalizar
# uma venda tem que gravar exatamente o que gravava antes, e o livro do dinheiro
# tem que ficar VAZIO. Se um dia ele falhar, a inercia que o plano prometeu
# deixou de existir e a fase nao pode ir para a loja.
# ---------------------------------------------------------------------------

from datetime import date, timedelta

import pytest
from starlette import status

from app.db.models.configuracao_vendas import ConfiguracaoVendas
from app.db.models.contador_venda import ContadorVenda
from app.db.models.movimentacao_financeira import MovimentacaoFinanceira
from app.db.models.sessao_caixa import SessaoCaixa
from app.db.models.venda import Venda
from app.db.models.venda_pagamento import PagamentoVenda

TEST_USER_EMAIL = "caixa.operador@example.com"
TEST_USER_PASSWORD = "senhaSegura456"


# ===========================================================================
# HELPERS
# ===========================================================================

def _auth(client):
    client.post("/api/v1/usuarios/", json={
        "nome": "Dono da Adega", "email": TEST_USER_EMAIL, "senha": TEST_USER_PASSWORD,
    })
    login = client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": "test-terminal-hwid",
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post("/api/v1/empresas/", json={
        "razao_social": "Adega Teste LTDA", "nome_fantasia": "Adega", "is_cnpj": True,
        "documento": "12345678000199", "regime_tributario": "Simples Nacional",
        "celular": "11999998888", "segmento": "assistencia_tecnica",
        "endereco": [{"logradouro": "Av. Paulista", "numero": "1000", "bairro": "Bela Vista",
                      "cidade": "São Paulo", "estado": "SP", "cep": "01310-100"}],
    }, headers=header)
    return header


def _funcionario(client, header):
    r = client.post("/api/v1/funcionarios/", json={
        "nome": "Operador Caixa", "cpf": "11122233344", "contato": "11999999999",
        "usuario": {"nome": "opcaixa", "email": "opcaixa@empresa.com", "senha": "SenhaForte123!"},
        "endereco": [{"logradouro": "Rua X", "numero": "1", "cep": "12345-678",
                      "bairro": "Centro", "cidade": "Lab City", "estado": "SP"}],
    }, headers=header)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _forma(client, header, nome="Dinheiro"):
    r = client.post("/api/v1/formas-pagamento/", json={"nome": nome, "ativo": True}, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _produto(client, header, codigo="ADEGA-1", varejo=1200, quantidade=100):
    r = client.post("/api/v1/produtos/", json={
        "nome": f"Produto {codigo}", "codigo_produto": codigo, "unidade_medida": "UN",
        "estoque": {"valor_varejo": varejo, "quantidade": quantidade},
    }, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _config_caixa(db_session, **flags):
    """Liga/desliga as chaves do caixa direto no banco.

    Direto e nao pela API de configuracoes de proposito: o objetivo do teste e a
    regra do caixa, nao o caminho da tela de configuracao.
    """
    cfg = db_session.query(ConfiguracaoVendas).first()
    if not cfg:
        cfg = ConfiguracaoVendas(empresa_id=1)
        db_session.add(cfg)
    for chave, valor in flags.items():
        setattr(cfg, chave, valor)
    db_session.commit()
    return cfg


def _venda_finalizada(client, header, db_session, funcionario_id, produto_id, fp_id,
                      quantidade=2, vencimento=None):
    if not db_session.query(ContadorVenda).first():
        db_session.add(ContadorVenda(id=1, proximo_numero=1))
        db_session.commit()

    cv = client.post("/api/v1/vendas/", json={"funcionario_id": funcionario_id}, headers=header)
    assert cv.status_code == 201, cv.text
    venda_id = cv.json()["id"]

    add = client.post(f"/api/v1/vendas/{venda_id}/itens", json={
        "tipo_produto": "CADASTRADO", "produto_id": produto_id, "quantidade": quantidade,
    }, headers=header)
    assert add.status_code == 201, add.text
    total = add.json()["financeiro_atualizado"]["total"]

    pagamento = {"forma_pagamento_id": fp_id, "valor": total,
                 "parcelado": False, "qtd_parcelas": None}
    if vencimento:
        pagamento["vencimento"] = vencimento.isoformat()

    fin = client.post(f"/api/v1/vendas/{venda_id}/finalizar",
                      json={"pagamentos": [pagamento]}, headers=header)
    return venda_id, total, fin


# ===========================================================================
# 1. A PROVA DA INERCIA -- o teste que autoriza esta fase a ir para a loja
# ===========================================================================

def test_com_caixa_desligado_a_venda_grava_igual_e_o_livro_fica_vazio(client, db_session):
    """Estado das tres lojas em producao: nada muda para elas.

    Com `controlar_caixa` desligado (o padrao), finalizar uma venda tem que
    produzir exatamente o mesmo resultado de antes desta fase: numero atribuido,
    status FINALIZADA, estoque baixado, pagamento gravado -- e NENHUMA linha no
    livro do dinheiro.
    """
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)
    produto_id = _produto(client, header)

    # Nao ligamos nada: o padrao ja e desligado.
    venda_id, total, fin = _venda_finalizada(
        client, header, db_session, funcionario_id, produto_id, fp_id
    )
    assert fin.status_code == 200, fin.text

    venda = db_session.query(Venda).filter(Venda.id == venda_id).first()
    assert venda.status.value == "FINALIZADA"
    assert venda.numero_venda == 1
    assert venda.total == total

    # O carimbo do caixa NAO acontece.
    assert venda.sessao_caixa_id is None
    pagamento = db_session.query(PagamentoVenda).filter(PagamentoVenda.venda_id == venda_id).first()
    assert pagamento is not None
    assert pagamento.sessao_caixa_id is None

    # E o livro do dinheiro continua vazio. Esta e a linha que importa.
    assert db_session.query(MovimentacaoFinanceira).count() == 0
    assert db_session.query(SessaoCaixa).count() == 0


def test_com_caixa_desligado_os_endpoints_recusam(client, db_session):
    """A rota existir nao liga o caixa para ninguem."""
    header = _auth(client)
    _funcionario(client, header)
    _config_caixa(db_session, controlar_caixa=False)

    r = client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 10000}, headers=header)
    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert "desligado" in r.json()["detail"].lower()


def test_com_caixa_desligado_sessao_atual_devolve_nulo(client, db_session):
    """A tela pergunta o tempo todo; 'nao ha caixa' e resposta normal, nao erro."""
    header = _auth(client)
    _funcionario(client, header)
    _config_caixa(db_session, controlar_caixa=False)

    r = client.get("/api/v1/caixa/atual", headers=header)
    assert r.status_code == 200
    assert r.json() is None


# ===========================================================================
# 2. ABERTURA
# ===========================================================================

def test_abrir_caixa_registra_o_troco_como_movimento(client, db_session):
    """O troco inicial e dinheiro na gaveta sem venda por tras -- logo, movimento.

    Se ele nao fosse registrado, o fechamento acusaria sobra exatamente do
    tamanho do troco, todo santo dia.
    """
    header = _auth(client)
    _funcionario(client, header)
    _forma(client, header)
    _config_caixa(db_session, controlar_caixa=True)

    r = client.post("/api/v1/caixa/abrir",
                    json={"saldo_inicial": 10000, "terminal_hwid": "PC-CAIXA-1"},
                    headers=header)
    assert r.status_code == 201, r.text
    resumo = r.json()
    assert resumo["saldo_inicial"] == 10000
    assert resumo["saldo_esperado_dinheiro"] == 10000
    assert resumo["status"] == "ABERTO"

    movimentos = db_session.query(MovimentacaoFinanceira).all()
    assert len(movimentos) == 1
    assert movimentos[0].origem == "ABERTURA"
    assert movimentos[0].tipo == "ENTRADA"
    assert movimentos[0].valor == 10000


def test_um_operador_nao_abre_dois_caixas(client, db_session):
    """Ninguem esta em dois caixas ao mesmo tempo.

    E o que permite a finalizacao da venda descobrir o turno pelo operador, sem
    precisar do HWID no checkout.
    """
    header = _auth(client)
    _funcionario(client, header)
    _forma(client, header)
    _config_caixa(db_session, controlar_caixa=True)

    primeiro = client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 5000}, headers=header)
    assert primeiro.status_code == 201

    segundo = client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 5000}, headers=header)
    assert segundo.status_code == status.HTTP_400_BAD_REQUEST
    assert "já tem um caixa aberto" in segundo.json()["detail"].lower()


# ===========================================================================
# 3. SANGRIA E SUPRIMENTO
# ===========================================================================

def test_suprimento_soma_e_sangria_subtrai_da_gaveta(client, db_session):
    header = _auth(client)
    _funcionario(client, header)
    _forma(client, header)
    _config_caixa(db_session, controlar_caixa=True, sangria_exige_autorizacao=False)

    client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 10000}, headers=header)

    sup = client.post("/api/v1/caixa/suprimento",
                      json={"valor": 5000, "motivo": "Reforço de troco"}, headers=header)
    assert sup.status_code == 201, sup.text
    assert sup.json()["saldo_esperado_dinheiro"] == 15000

    san = client.post("/api/v1/caixa/sangria",
                      json={"valor": 3000, "motivo": "Envio ao cofre"}, headers=header)
    assert san.status_code == 201, san.text
    resumo = san.json()
    assert resumo["saldo_esperado_dinheiro"] == 12000
    assert resumo["total_suprimentos"] == 5000
    assert resumo["total_sangrias"] == 3000


def test_sangria_sem_motivo_e_recusada(client, db_session):
    """Motivo e o que transforma 'sumiu dinheiro' em 'saiu R$ 200 para o cofre'."""
    header = _auth(client)
    _funcionario(client, header)
    _forma(client, header)
    _config_caixa(db_session, controlar_caixa=True, sangria_exige_autorizacao=False)
    client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 10000}, headers=header)

    r = client.post("/api/v1/caixa/sangria", json={"valor": 1000}, headers=header)
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_suprimento_nao_exige_autorizacao_mesmo_com_a_trava_ligada(client, db_session):
    """A assimetria e proposital: por dinheiro na gaveta nao cria risco de desvio.

    Travar os dois faria o operador chamar o gerente para colocar troco -- o
    atrito que faz loja desligar o controle e voltar para o caderno.
    """
    header = _auth(client)
    _funcionario(client, header)
    _forma(client, header)
    _config_caixa(db_session, controlar_caixa=True, sangria_exige_autorizacao=True)
    client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 10000}, headers=header)

    r = client.post("/api/v1/caixa/suprimento",
                    json={"valor": 2000, "motivo": "Troco"}, headers=header)
    assert r.status_code == 201, r.text


# ===========================================================================
# 4. A VENDA CAINDO NO CAIXA
# ===========================================================================

def test_venda_finalizada_com_caixa_aberto_entra_no_livro(client, db_session):
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)
    produto_id = _produto(client, header)
    _config_caixa(db_session, controlar_caixa=True)

    client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 10000}, headers=header)

    venda_id, total, fin = _venda_finalizada(
        client, header, db_session, funcionario_id, produto_id, fp_id
    )
    assert fin.status_code == 200, fin.text

    movimento = (
        db_session.query(MovimentacaoFinanceira)
        .filter(MovimentacaoFinanceira.origem == "VENDA")
        .first()
    )
    assert movimento is not None
    assert movimento.valor == total
    assert movimento.tipo == "ENTRADA"

    venda = db_session.query(Venda).filter(Venda.id == venda_id).first()
    assert venda.sessao_caixa_id is not None

    atual = client.get("/api/v1/caixa/atual", headers=header).json()
    assert atual["total_vendas"] == total
    # Venda em dinheiro entra na gaveta, entao o esperado sobe junto.
    assert atual["saldo_esperado_dinheiro"] == 10000 + total


def test_dinheiro_cai_no_turno_de_quem_recebe_e_nao_de_quem_vendeu(client, db_session):
    """`venda.funcionario_id` e o VENDEDOR (comissao); quem recebe e quem esta no caixa.

    Aqui a venda e registrada em nome de um funcionario que NAO abriu caixa
    nenhum, e mesmo assim o dinheiro entra -- no turno de quem finalizou. Numa
    loja onde um atende e outro recebe, o contrario faria o dinheiro sumir do
    fechamento de quem esta com a gaveta na mao.
    """
    header = _auth(client)
    vendedor_id = _funcionario(client, header)
    fp_id = _forma(client, header)
    produto_id = _produto(client, header)
    _config_caixa(db_session, controlar_caixa=True)

    client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 10000}, headers=header)
    sessao = db_session.query(SessaoCaixa).first()
    # O vendedor da venda nao e o dono do turno.
    assert sessao.funcionario_id != vendedor_id

    _, total, fin = _venda_finalizada(
        client, header, db_session, vendedor_id, produto_id, fp_id
    )
    assert fin.status_code == 200, fin.text

    movimento = (
        db_session.query(MovimentacaoFinanceira)
        .filter(MovimentacaoFinanceira.origem == "VENDA")
        .first()
    )
    assert movimento is not None
    assert movimento.sessao_caixa_id == sessao.id
    assert movimento.valor == total


def test_pagamento_com_vencimento_futuro_nao_entra_na_gaveta(client, db_session):
    """Fiado e promessa, nao dinheiro.

    A venda existe e a cobranca fica registrada, mas nada entra no caixa -- senao
    o fechamento acusaria sobra em toda venda a prazo. O movimento nasce no dia
    em que o cliente pagar, e quem vai registrar isso e o modulo financeiro.
    """
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header, nome="Boleto")
    produto_id = _produto(client, header)
    _config_caixa(db_session, controlar_caixa=True)
    client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 10000}, headers=header)

    venda_id, total, fin = _venda_finalizada(
        client, header, db_session, funcionario_id, produto_id, fp_id,
        vencimento=date.today() + timedelta(days=30),
    )
    assert fin.status_code == 200, fin.text

    assert db_session.query(MovimentacaoFinanceira).filter(
        MovimentacaoFinanceira.origem == "VENDA"
    ).count() == 0

    # A venda existe e esta finalizada -- so o dinheiro que nao entrou.
    venda = db_session.query(Venda).filter(Venda.id == venda_id).first()
    assert venda.status.value == "FINALIZADA"


def test_exigir_caixa_aberto_bloqueia_a_venda(client, db_session):
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)
    produto_id = _produto(client, header)
    _config_caixa(db_session, controlar_caixa=True, exigir_caixa_aberto=True)

    # Sem abrir o caixa:
    _, _, fin = _venda_finalizada(client, header, db_session, funcionario_id, produto_id, fp_id)
    assert fin.status_code == status.HTTP_400_BAD_REQUEST
    assert "abra o caixa" in fin.json()["detail"].lower()


def test_exigir_caixa_aberto_desligado_nao_bloqueia_nada(client, db_session):
    """`controlar_caixa` registra; `exigir_caixa_aberto` obriga. Sao separadas."""
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)
    produto_id = _produto(client, header)
    _config_caixa(db_session, controlar_caixa=True, exigir_caixa_aberto=False)

    _, _, fin = _venda_finalizada(client, header, db_session, funcionario_id, produto_id, fp_id)
    assert fin.status_code == 200, fin.text


# ===========================================================================
# 5. FECHAMENTO
# ===========================================================================

def test_fechamento_calcula_a_diferenca_entre_contado_e_esperado(client, db_session):
    header = _auth(client)
    _funcionario(client, header)
    _forma(client, header)
    _config_caixa(db_session, controlar_caixa=True, sangria_exige_autorizacao=False)

    client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 10000}, headers=header)
    client.post("/api/v1/caixa/suprimento", json={"valor": 5000, "motivo": "Troco"}, headers=header)
    client.post("/api/v1/caixa/sangria", json={"valor": 2000, "motivo": "Cofre"}, headers=header)

    # Esperado: 10000 + 5000 - 2000 = 13000. Contamos 12950 (faltam 50 centavos).
    r = client.post("/api/v1/caixa/fechar", json={"saldo_contado": 12950}, headers=header)
    assert r.status_code == 200, r.text
    resumo = r.json()
    assert resumo["status"] == "FECHADO"
    assert resumo["saldo_esperado_dinheiro"] == 13000
    assert resumo["saldo_contado"] == 12950
    assert resumo["diferenca"] == -50

    sessao = db_session.query(SessaoCaixa).first()
    assert sessao.data_fechamento is not None


def test_depois_de_fechar_da_para_abrir_de_novo(client, db_session):
    """Troca de turno: fecha o de quem sai, abre o de quem entra."""
    header = _auth(client)
    _funcionario(client, header)
    _forma(client, header)
    _config_caixa(db_session, controlar_caixa=True)

    client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 10000,
                                             "terminal_hwid": "PC-1"}, headers=header)
    client.post("/api/v1/caixa/fechar", json={"saldo_contado": 10000}, headers=header)

    de_novo = client.post("/api/v1/caixa/abrir",
                          json={"saldo_inicial": 8000, "terminal_hwid": "PC-1"}, headers=header)
    assert de_novo.status_code == 201, de_novo.text
    assert db_session.query(SessaoCaixa).count() == 2


def test_fechamento_cego_esconde_o_esperado_antes_da_contagem(client, db_session):
    """Cego e nao ver ANTES de contar.

    No fechamento o numero volta: esconder depois so impediria o operador de
    assinar o que ele mesmo conferiu.
    """
    header = _auth(client)
    _funcionario(client, header)
    _forma(client, header)
    _config_caixa(db_session, controlar_caixa=True, fechamento_cego=True)
    client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 10000}, headers=header)

    atual = client.get("/api/v1/caixa/atual", headers=header).json()
    assert atual["saldo_esperado_dinheiro"] == 0  # escondido

    fechado = client.post("/api/v1/caixa/fechar", json={"saldo_contado": 9900}, headers=header).json()
    assert fechado["saldo_esperado_dinheiro"] == 10000  # revelado
    assert fechado["diferenca"] == -100


def test_fechar_sem_caixa_aberto_e_recusado(client, db_session):
    header = _auth(client)
    _funcionario(client, header)
    _config_caixa(db_session, controlar_caixa=True)

    r = client.post("/api/v1/caixa/fechar", json={"saldo_contado": 1000}, headers=header)
    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert "nenhum caixa aberto" in r.json()["detail"].lower()
