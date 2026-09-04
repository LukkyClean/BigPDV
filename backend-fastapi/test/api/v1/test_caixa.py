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

from app.core.security import hash_password
from app.db.models.configuracao_seguranca import ConfiguracaoSeguranca
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
    _config_caixa(db_session, controlar_caixa=True)

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
    _config_caixa(db_session, controlar_caixa=True)
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
    _config_caixa(db_session, controlar_caixa=True)
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


def test_sem_caixa_aberto_a_venda_NASCE_e_so_a_finalizacao_e_barrada(client, db_session):
    """A trava do caixa mora na finalizacao, e SO nela.

    Este teste substitui o `test_exigir_caixa_aberto_bloqueia_a_venda_ja_na_criacao`,
    que travava o comportamento anterior. A regra mudou por decisao do dono em
    21/08/2026: montar carrinho nao move dinheiro nenhum, e exigir turno na
    criacao impedia o atendente de montar a venda para o CAIXA receber.

    O que NAO mudou -- e e o que este teste guarda -- e que o dinheiro continua
    barrado sem turno. Se a segunda metade daqui um dia passar a devolver 200, o
    controle da gaveta acabou.
    """
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)
    produto_id = _produto(client, header)
    _config_caixa(db_session, controlar_caixa=True, exigir_caixa_aberto=True)

    # Nasce.
    cv = client.post("/api/v1/vendas/", json={"funcionario_id": funcionario_id}, headers=header)
    assert cv.status_code == 201, cv.text
    venda_id = cv.json()["id"]

    # E aceita item -- montar o carrinho inteiro tem que funcionar.
    add = client.post(f"/api/v1/vendas/{venda_id}/itens", json={
        "tipo_produto": "CADASTRADO", "produto_id": produto_id, "quantidade": 1,
    }, headers=header)
    assert add.status_code == 201, add.text
    total = add.json()["financeiro_atualizado"]["total"]

    # O dinheiro, nao.
    fin = client.post(f"/api/v1/vendas/{venda_id}/finalizar", json={
        "pagamentos": [{"forma_pagamento_id": fp_id, "valor": total,
                        "parcelado": False, "qtd_parcelas": None}],
    }, headers=header)
    assert fin.status_code == status.HTTP_400_BAD_REQUEST, fin.text
    assert "abra o caixa" in fin.json()["detail"].lower()


def test_maquina_retaguarda_monta_venda_sem_turno(client, db_session):
    """O beco da retaguarda, fechado sem uma linha de codigo de terminal.

    A maquina marcada RETAGUARDA esconde a barra do caixa -- e ate 21/08/2026
    continuava sendo cobrada por `exigir_caixa_aberto`. Ficava sem o botao de
    abrir E sem poder vender: o operador nao tinha saida nenhuma.

    Como a trava saiu da criacao, o papel do terminal nem precisa ser consultado
    aqui. O teste existe para provar que a saida existe, venha ela de onde vier.
    """
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    produto_id = _produto(client, header)
    _config_caixa(db_session, controlar_caixa=True, exigir_caixa_aberto=True)

    cv = client.post("/api/v1/vendas/", json={"funcionario_id": funcionario_id}, headers=header)
    assert cv.status_code == 201, cv.text

    add = client.post(f"/api/v1/vendas/{cv.json()['id']}/itens", json={
        "tipo_produto": "CADASTRADO", "produto_id": produto_id, "quantidade": 1,
    }, headers=header)
    assert add.status_code == 201, add.text


def test_fechar_o_caixa_no_meio_ainda_bloqueia_a_finalizacao(client, db_session):
    """A trava da finalizacao e a garantia de verdade, e continua valendo.

    Cenario real: o operador comeca a venda com o caixa aberto, alguem fecha o
    turno, e ele tenta finalizar. O dinheiro nao tem onde cair -- tem que
    recusar, mesmo com a venda ja criada.
    """
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma(client, header)
    produto_id = _produto(client, header)
    _config_caixa(db_session, controlar_caixa=True, exigir_caixa_aberto=True)

    client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 10000}, headers=header)

    if not db_session.query(ContadorVenda).first():
        db_session.add(ContadorVenda(id=1, proximo_numero=1))
        db_session.commit()
    cv = client.post("/api/v1/vendas/", json={"funcionario_id": funcionario_id}, headers=header)
    assert cv.status_code == 201, cv.text
    venda_id = cv.json()["id"]
    add = client.post(f"/api/v1/vendas/{venda_id}/itens", json={
        "tipo_produto": "CADASTRADO", "produto_id": produto_id, "quantidade": 1,
    }, headers=header)
    total = add.json()["financeiro_atualizado"]["total"]

    # O turno fecha com a venda no ar.
    client.post("/api/v1/caixa/fechar", json={"saldo_contado": 10000}, headers=header)

    fin = client.post(f"/api/v1/vendas/{venda_id}/finalizar", json={
        "pagamentos": [{"forma_pagamento_id": fp_id, "valor": total,
                        "parcelado": False, "qtd_parcelas": None}],
    }, headers=header)
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
    _config_caixa(db_session, controlar_caixa=True)

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

    ESCONDIDO E `None`, NAO `0`. Enquanto era zero, a barra do PDV anunciava
    "Em dinheiro na gaveta: R$ 0,00" o dia inteiro numa loja com fechamento cego
    ligado -- com a gaveta cheia e as vendas todas lancadas. Quem esta no balcao
    nao le "esta oculto", le "o sistema nao esta somando minhas vendas".
    Esconder e legitimo; mentir um valor nao e.
    """
    header = _auth(client)
    _funcionario(client, header)
    _forma(client, header)
    _config_caixa(db_session, controlar_caixa=True, fechamento_cego=True)
    client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 10000}, headers=header)

    atual = client.get("/api/v1/caixa/atual", headers=header).json()
    assert atual["saldo_esperado_dinheiro"] is None  # escondido, e nao "zero"

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


# ===========================================================================
# 8. PIN DO GERENTE PARA ABRIR O CAIXA
#
# O teste que mais importa aqui e o ULTIMO: com a trava desligada -- que e o
# padrao e o estado das tres lojas em producao -- o operador abre o caixa
# exatamente como abria. Se ele falhar, a chave nova deixou de ser opcional.
# ===========================================================================

def _cargo_vendas(client, header, nome="Balconista", permissoes=None):
    """Cargo de quem opera o PDV.

    O padrao inclui `manage_sales` DE PROPOSITO: e o cargo real de uma loja --
    quem opera o caixa precisa dele para vender. Foi justamente essa permissao
    que, na primeira ida a loja, fazia o balconista pular a trava.
    """
    r = client.post("/api/v1/cargos/", json={
        "nome": nome,
        "permissoes": permissoes if permissoes is not None else {"view_sales": True, "manage_sales": True},
    }, headers=header)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _operador(client, header, permissoes=None):
    """Funcionario com cargo de vendas e token proprio — nao e master."""
    func_id = _funcionario(client, header)
    cargo_id = _cargo_vendas(client, header, permissoes=permissoes)
    lk = client.put(f"/api/v1/funcionarios/{func_id}/cargo?cargo_id={cargo_id}", headers=header)
    assert lk.status_code == 200, lk.text
    # Login DEPOIS de vincular o cargo: as permissoes viajam no token.
    r = client.post("/api/v1/auth/login", data={
        "username": "opcaixa@empresa.com", "password": "SenhaForte123!",
        "hwid": "test-terminal-hwid",
    })
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _pin_gerente(db_session, pin="4321"):
    """Grava o PIN de gerente hasheado — o MESMO que protege sangria e desconto."""
    cfg = db_session.query(ConfiguracaoSeguranca).first()
    if not cfg:
        cfg = ConfiguracaoSeguranca(empresa_id=1)
        db_session.add(cfg)
    cfg.pin_gerente = hash_password(pin)
    db_session.commit()
    return pin


def test_abrir_caixa_com_a_trava_ligada_pede_pin_do_gerente(client, db_session):
    """Sem PIN recusa com sentinela, PIN errado recusa, PIN certo abre.

    As sentinelas nao sao frase solta: e o contrato que o frontend ja usa para
    abrir o modal de aprovacao em sangria, cancelamento e desconto.
    """
    header = _auth(client)
    _forma(client, header)
    _config_caixa(db_session, controlar_caixa=True, requer_pin_abrir_caixa=True)
    pin = _pin_gerente(db_session)
    h_op = _operador(client, header)

    sem_pin = client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 10000}, headers=h_op)
    assert sem_pin.status_code == 400, sem_pin.text
    assert sem_pin.json()["detail"] == "REQUER_APROVACAO_GERENTE"

    errado = client.post("/api/v1/caixa/abrir",
                         json={"saldo_inicial": 10000, "codigo_gerente": "0000"}, headers=h_op)
    assert errado.status_code == 400, errado.text
    assert errado.json()["detail"] == "PIN_GERENTE_INVALIDO"

    # Nenhuma das duas recusas pode ter deixado turno para tras.
    assert db_session.query(SessaoCaixa).count() == 0

    certo = client.post("/api/v1/caixa/abrir",
                        json={"saldo_inicial": 10000, "codigo_gerente": pin}, headers=h_op)
    assert certo.status_code == 201, certo.text
    assert db_session.query(SessaoCaixa).count() == 1


def test_master_abre_o_caixa_sem_pin_mesmo_com_a_trava_ligada(client, db_session):
    """Quem e dono nao pede licenca a si mesmo — mesma regra da sangria."""
    header = _auth(client)
    _funcionario(client, header)
    _forma(client, header)
    _config_caixa(db_session, controlar_caixa=True, requer_pin_abrir_caixa=True)
    _pin_gerente(db_session)

    r = client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 10000}, headers=header)
    assert r.status_code == 201, r.text


def test_trava_ligada_sem_pin_cadastrado_diz_onde_resolver(client, db_session):
    """Ligar a trava e esquecer o PIN travaria a abertura para sempre.

    E sem caixa aberto a loja nao vende — entao a recusa aqui NAO pode ser a
    sentinela: o modal de PIN abriria e nenhum numero digitado funcionaria. Tem
    que ser a frase que diz onde arrumar.
    """
    header = _auth(client)
    _forma(client, header)
    _config_caixa(db_session, controlar_caixa=True, requer_pin_abrir_caixa=True)
    h_op = _operador(client, header)

    r = client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 10000}, headers=h_op)
    assert r.status_code == 400, r.text
    detail = r.json()["detail"]
    assert detail != "REQUER_APROVACAO_GERENTE"
    assert "Segurança" in detail


def test_fechar_o_caixa_nao_pede_pin(client, db_session):
    """A assimetria e proposital, como a do suprimento.

    Quem abriu precisa conseguir fechar: exigir um gerente no fim do expediente
    deixaria a gaveta aberta ate o dia seguinte — pior para a conferencia do que
    o problema que resolveria.
    """
    header = _auth(client)
    _forma(client, header)
    _config_caixa(db_session, controlar_caixa=True, requer_pin_abrir_caixa=True)
    pin = _pin_gerente(db_session)
    h_op = _operador(client, header)

    abriu = client.post("/api/v1/caixa/abrir",
                        json={"saldo_inicial": 10000, "codigo_gerente": pin}, headers=h_op)
    assert abriu.status_code == 201, abriu.text

    fechou = client.post("/api/v1/caixa/fechar", json={"saldo_contado": 10000}, headers=h_op)
    assert fechou.status_code == 200, fechou.text


def test_com_a_trava_desligada_o_operador_abre_como_sempre(client, db_session):
    """A inercia: a chave nova nasce desligada e nada muda para quem nao a liga.

    E o mesmo compromisso do primeiro teste deste arquivo, agora para a trava de
    abertura. Se este falhar, a chave deixou de ser opcional e nao pode ir para
    a loja.
    """
    header = _auth(client)
    _forma(client, header)
    _config_caixa(db_session, controlar_caixa=True)
    h_op = _operador(client, header)

    r = client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 10000}, headers=h_op)
    assert r.status_code == 201, r.text


def test_manage_sales_NAO_dispensa_o_pin_para_abrir_o_caixa(client, db_session):
    """A regra aqui DIVERGE da sangria, e e isso que faz a chave valer alguma coisa.

    `_validar_autorizacao_sangria` libera quem tem `manage_sales`. Repetir aquela
    lista aqui tornava a trava decoracao: o cargo que opera o PDV precisa de
    `manage_sales` para vender, entao o balconista -- exatamente quem ela existe
    para pegar -- passava direto. Aconteceu na primeira ida a loja, com um cargo
    chamado "Caixa".

    Este teste e o que impede alguem de "uniformizar" as duas listas depois.
    """
    header = _auth(client)
    _forma(client, header)
    _config_caixa(db_session, controlar_caixa=True, requer_pin_abrir_caixa=True)
    pin = _pin_gerente(db_session)
    # O cargo real da loja: vende, gerencia venda, e mesmo assim precisa do PIN.
    h_op = _operador(client, header, permissoes={"view_sales": True, "manage_sales": True})

    r = client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 10000}, headers=h_op)
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == "REQUER_APROVACAO_GERENTE"

    ok = client.post("/api/v1/caixa/abrir",
                     json={"saldo_inicial": 10000, "codigo_gerente": pin}, headers=h_op)
    assert ok.status_code == 201, ok.text


def test_permissao_all_tambem_nao_dispensa_o_pin(client, db_session):
    """`all` e bypass amplo de permissao; trava de supervisao que ele desliga nao trava nada."""
    header = _auth(client)
    _forma(client, header)
    _config_caixa(db_session, controlar_caixa=True, requer_pin_abrir_caixa=True)
    _pin_gerente(db_session)
    h_op = _operador(client, header, permissoes={"all": True})

    r = client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 10000}, headers=h_op)
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == "REQUER_APROVACAO_GERENTE"


# ===========================================================================
# 9. A FILA DO CAIXA -- o atendente monta, o caixa recebe
#
# O teste que decide se esta fase pode ir para a loja e o ULTIMO: com
# `controlar_caixa` desligado, a coluna fica NULL e a lista se comporta como
# sempre se comportou.
# ===========================================================================

def _venda_com_item(client, header, funcionario_id, produto_id, quantidade=1):
    cv = client.post("/api/v1/vendas/", json={"funcionario_id": funcionario_id}, headers=header)
    assert cv.status_code == 201, cv.text
    venda_id = cv.json()["id"]
    add = client.post(f"/api/v1/vendas/{venda_id}/itens", json={
        "tipo_produto": "CADASTRADO", "produto_id": produto_id, "quantidade": quantidade,
    }, headers=header)
    assert add.status_code == 201, add.text
    return venda_id, add.json()["financeiro_atualizado"]["total"]


def test_enviar_ao_caixa_carimba_e_devolver_limpa(client, db_session):
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    produto_id = _produto(client, header)
    _config_caixa(db_session, controlar_caixa=True, usar_fila_do_caixa=True)

    venda_id, _ = _venda_com_item(client, header, funcionario_id, produto_id)

    # Nasce fora da fila.
    detalhe = client.get(f"/api/v1/vendas/{venda_id}", headers=header)
    assert detalhe.json()["enviada_ao_caixa_em"] is None

    env = client.post(f"/api/v1/vendas/{venda_id}/enviar-ao-caixa", headers=header)
    assert env.status_code == 200, env.text
    assert env.json()["enviada_ao_caixa_em"] is not None
    # O status NAO muda -- e a decisao de arquitetura da fase inteira.
    assert env.json()["status"] == "ATIVA"

    dev = client.post(f"/api/v1/vendas/{venda_id}/devolver-para-montagem", headers=header)
    assert dev.status_code == 200, dev.text
    assert dev.json()["enviada_ao_caixa_em"] is None
    assert dev.json()["status"] == "ATIVA"


def test_reenviar_nao_move_o_lugar_na_fila(client, db_session):
    """Idempotente: um clique repetido nao manda o atendente para o fim da fila."""
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    produto_id = _produto(client, header)
    _config_caixa(db_session, controlar_caixa=True, usar_fila_do_caixa=True)

    venda_id, _ = _venda_com_item(client, header, funcionario_id, produto_id)

    primeiro = client.post(f"/api/v1/vendas/{venda_id}/enviar-ao-caixa", headers=header)
    assert primeiro.status_code == 200, primeiro.text
    carimbo = primeiro.json()["enviada_ao_caixa_em"]

    segundo = client.post(f"/api/v1/vendas/{venda_id}/enviar-ao-caixa", headers=header)
    assert segundo.status_code == 200, segundo.text
    assert segundo.json()["enviada_ao_caixa_em"] == carimbo


def test_venda_sem_item_nao_entra_na_fila(client, db_session):
    """Carrinho vazio na fila e ruido: o caixa abre e nao ha o que cobrar."""
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    _config_caixa(db_session, controlar_caixa=True, usar_fila_do_caixa=True)

    cv = client.post("/api/v1/vendas/", json={"funcionario_id": funcionario_id}, headers=header)
    assert cv.status_code == 201, cv.text

    r = client.post(f"/api/v1/vendas/{cv.json()['id']}/enviar-ao-caixa", headers=header)
    assert r.status_code == 400, r.text
    assert "item" in r.json()["detail"].lower()


def test_acrescentar_item_depois_de_enviar_TIRA_da_fila(client, db_session):
    """O caixa nao pode ficar olhando um total que mudou embaixo dele.

    A regra mora em `_recalc_total_sale`, por onde passam acrescentar, alterar e
    remover item e aplicar desconto. Este teste cobre o caminho mais provavel;
    se alguem mudar o ponto de estrangulamento, ele cai.
    """
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    produto_id = _produto(client, header)
    _config_caixa(db_session, controlar_caixa=True, usar_fila_do_caixa=True)

    venda_id, _ = _venda_com_item(client, header, funcionario_id, produto_id)
    assert client.post(f"/api/v1/vendas/{venda_id}/enviar-ao-caixa", headers=header).status_code == 200

    add = client.post(f"/api/v1/vendas/{venda_id}/itens", json={
        "tipo_produto": "CADASTRADO", "produto_id": produto_id, "quantidade": 1,
    }, headers=header)
    assert add.status_code == 201, add.text

    detalhe = client.get(f"/api/v1/vendas/{venda_id}", headers=header)
    assert detalhe.json()["enviada_ao_caixa_em"] is None, "editar tem que tirar da fila"


def test_o_caixa_ve_a_venda_que_o_ATENDENTE_entregou(client, db_session):
    """Sem isto a funcionalidade inteira nao existe.

    A lista recorta por funcionario para quem nao tem visao gerencial -- entao a
    venda do atendente simplesmente nao apareceria para o caixa, que e um
    funcionario comum. Entregar a venda E o ato de compartilha-la, e `na_fila`
    e a unica coisa que fura esse recorte.
    """
    header = _auth(client)
    atendente_id = _funcionario(client, header)
    produto_id = _produto(client, header)
    _config_caixa(db_session, controlar_caixa=True, usar_fila_do_caixa=True)

    cargo_id = _cargo_vendas(client, header, nome="Balconista Fila")
    lk = client.put(f"/api/v1/funcionarios/{atendente_id}/cargo?cargo_id={cargo_id}", headers=header)
    assert lk.status_code == 200, lk.text
    login = client.post("/api/v1/auth/login", data={
        "username": "opcaixa@empresa.com", "password": "SenhaForte123!",
        "hwid": "test-terminal-hwid",
    })
    assert login.status_code == 200, login.text
    h_op = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # As duas vendas sao criadas pelo MASTER, em nome do atendente.
    venda_id, _ = _venda_com_item(client, header, atendente_id, produto_id)
    outra_id, _ = _venda_com_item(client, header, atendente_id, produto_id)
    assert client.post(f"/api/v1/vendas/{venda_id}/enviar-ao-caixa", headers=header).status_code == 200

    # Com `na_fila`, a venda entregue aparece para o operador.
    fila = client.get("/api/v1/vendas/?na_fila=true", headers=h_op)
    assert fila.status_code == 200, fila.text
    ids = [v["id"] for v in fila.json()["vendas"]]
    assert venda_id in ids, ids
    assert outra_id not in ids, "so a entregue entra na fila"


def test_finalizar_da_fila_mantem_o_carimbo_e_o_dinheiro_vai_para_quem_recebe(client, db_session):
    header = _auth(client)
    vendedor_id = _funcionario(client, header)
    fp_id = _forma(client, header)
    produto_id = _produto(client, header)
    _config_caixa(db_session, controlar_caixa=True, usar_fila_do_caixa=True)
    if not db_session.query(ContadorVenda).first():
        db_session.add(ContadorVenda(id=1, proximo_numero=1))
        db_session.commit()

    client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 10000}, headers=header)
    sessao = db_session.query(SessaoCaixa).first()
    assert sessao.funcionario_id != vendedor_id

    venda_id, total = _venda_com_item(client, header, vendedor_id, produto_id)
    assert client.post(f"/api/v1/vendas/{venda_id}/enviar-ao-caixa", headers=header).status_code == 200

    fin = client.post(f"/api/v1/vendas/{venda_id}/finalizar", json={
        "pagamentos": [{"forma_pagamento_id": fp_id, "valor": total,
                        "parcelado": False, "qtd_parcelas": None}],
    }, headers=header)
    assert fin.status_code == 200, fin.text

    # O carimbo SOBREVIVE a finalizacao: `finish_sale` passa `sai_da_fila=False`,
    # senao o registro de que a venda esperou se perderia.
    assert fin.json()["enviada_ao_caixa_em"] is not None

    movimento = (
        db_session.query(MovimentacaoFinanceira)
        .filter(MovimentacaoFinanceira.origem == "VENDA")
        .first()
    )
    assert movimento is not None
    assert movimento.sessao_caixa_id == sessao.id


def test_a_contagem_da_fila_e_subconjunto_das_ativas(client, db_session):
    """Somar as categorias nao pode dar mais que o total -- fila nao e categoria nova."""
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    produto_id = _produto(client, header)
    _config_caixa(db_session, controlar_caixa=True, usar_fila_do_caixa=True)

    a_id, _ = _venda_com_item(client, header, funcionario_id, produto_id)
    _venda_com_item(client, header, funcionario_id, produto_id)
    assert client.post(f"/api/v1/vendas/{a_id}/enviar-ao-caixa", headers=header).status_code == 200

    r = client.get("/api/v1/vendas/status/", headers=header)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["vendas_ativas"] == 2
    assert body["vendas_na_fila"] == 1


def test_com_caixa_desligado_a_fila_nao_existe_e_nada_muda(client, db_session):
    """A prova da inercia da Fase 2.

    Loja sem controle de caixa nao tem fila. A coluna fica NULL, a lista devolve
    o que sempre devolveu, e a contagem nova responde zero. Se este cair, a fase
    nao pode ir para a loja.
    """
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    produto_id = _produto(client, header)
    # Sem _config_caixa: `controlar_caixa` fica no padrao (desligado).

    venda_id, _ = _venda_com_item(client, header, funcionario_id, produto_id)

    lista = client.get("/api/v1/vendas/", headers=header)
    assert lista.status_code == 200, lista.text
    alvo = next(v for v in lista.json()["vendas"] if v["id"] == venda_id)
    assert alvo["enviada_ao_caixa_em"] is None
    assert alvo["status"] == "ATIVA"

    r = client.get("/api/v1/vendas/status/", headers=header)
    assert r.json()["vendas_na_fila"] == 0


def test_com_a_fila_desligada_a_venda_nao_entra_nela(client, db_session):
    """A fila e opcional -- e a loja de um PC so nao a tem.

    `controlar_caixa` responde "esta loja controla a gaveta"; `usar_fila_do_caixa`
    responde "quem monta e quem recebe sao pessoas diferentes". Sao perguntas
    diferentes, e a segunda pode ser NAO numa loja que responde SIM a primeira.

    A tela ja esconde o botao, mas quem garante que nao entra venda na fila de
    uma loja que nao usa fila e a checagem do backend -- o frontend pode estar
    mais novo que a configuracao, e foi assim que a chave do PIN pareceu
    quebrada num teste na loja.
    """
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    produto_id = _produto(client, header)
    # Caixa ligado, fila DESLIGADA -- a combinacao da loja de um PC so.
    _config_caixa(db_session, controlar_caixa=True, usar_fila_do_caixa=False)

    venda_id, _ = _venda_com_item(client, header, funcionario_id, produto_id)

    r = client.post(f"/api/v1/vendas/{venda_id}/enviar-ao-caixa", headers=header)
    assert r.status_code == 400, r.text
    assert "fila do caixa" in r.json()["detail"].lower()

    detalhe = client.get(f"/api/v1/vendas/{venda_id}", headers=header)
    assert detalhe.json()["enviada_ao_caixa_em"] is None


def test_desligar_a_fila_nao_aprisiona_quem_ja_estava_nela(client, db_session):
    """Devolver continua funcionando com a chave desligada.

    Se o dono desligar a fila com vendas dentro, elas precisam poder sair --
    recusar tambem o devolver as deixaria carimbadas para sempre, sem tela
    nenhuma para desfazer.
    """
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    produto_id = _produto(client, header)
    _config_caixa(db_session, controlar_caixa=True, usar_fila_do_caixa=True)

    venda_id, _ = _venda_com_item(client, header, funcionario_id, produto_id)
    assert client.post(f"/api/v1/vendas/{venda_id}/enviar-ao-caixa", headers=header).status_code == 200

    # O dono desliga a chave DEPOIS, com a venda ja na fila.
    _config_caixa(db_session, usar_fila_do_caixa=False)

    dev = client.post(f"/api/v1/vendas/{venda_id}/devolver-para-montagem", headers=header)
    assert dev.status_code == 200, dev.text
    assert dev.json()["enviada_ao_caixa_em"] is None
