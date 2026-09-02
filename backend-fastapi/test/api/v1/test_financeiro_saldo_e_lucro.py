# ---------------------------------------------------------------------------
# O saldo que ANDA e o lucro que desconta o custo (02/09/2026).
#
# Dois defeitos que o uso real achou e nenhum teste pegava, porque nenhum teste
# perguntava o que o DONO pergunta:
#
#   1. "vendi o dia inteiro e o Fluxo de Caixa nao subiu"
#      O saldo era a foto que o dono declarou, e nada no sistema a movia.
#   2. "servico de 160 com peca de 60, o lucro apareceu 160"
#      O custo da peca so existia no modulo de Relatorios.
#
# O caso que abriu o chamado esta em `test_o_caso_da_bateria_de_60_num_servico_de_160`,
# e ele e o teste que mais importa deste arquivo: e a conta que o dono fez de
# cabeca e o sistema errou.
#
# ARMADILHAS PROTEGIDAS AQUI, porque as tres derrubam o saldo em silencio:
#   - abertura e sangria sao TRANSFERENCIA e nao podem mexer no saldo;
#   - o instante da ancora impede a venda da manha de ser contada duas vezes;
#   - compra de mercadoria sai do caixa mas nao do lucro.
# ---------------------------------------------------------------------------

from datetime import date, timedelta

from starlette import status

from app.db.models.conta_bancaria import ContaBancaria
from app.db.models.configuracao_vendas import ConfiguracaoVendas

TEST_USER_EMAIL = "saldo.dono@example.com"
TEST_USER_PASSWORD = "senhaSegura789"


# ===========================================================================
# HELPERS
# ===========================================================================

def _auth(client):
    client.post("/api/v1/usuarios/", json={
        "nome": "Dono do Saldo", "email": TEST_USER_EMAIL, "senha": TEST_USER_PASSWORD,
    })
    login = client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": "hwid-saldo",
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post("/api/v1/empresas/", json={
        "razao_social": "Saldo LTDA", "nome_fantasia": "Saldo", "is_cnpj": True,
        "documento": "12345678000188", "regime_tributario": "Simples Nacional",
        "celular": "11999997777", "segmento": "assistencia_tecnica",
        "endereco": [{"logradouro": "Av. Brasil", "numero": "500", "bairro": "Centro",
                      "cidade": "São Paulo", "estado": "SP", "cep": "01310-100"}],
    }, headers=header)
    return header


def _conta_id(client, header):
    """A gaveta que o backend semeia no primeiro acesso."""
    contas = client.get("/api/v1/financeiro/contas-bancarias", headers=header).json()
    assert contas, "o backend semeia 'Caixa da loja' na primeira listagem"
    return contas[0]["id"]


def _informar_saldo(client, header, centavos: int):
    r = client.patch(
        f"/api/v1/financeiro/contas-bancarias/{_conta_id(client, header)}",
        json={"saldo_informado": centavos}, headers=header,
    )
    assert r.status_code == status.HTTP_200_OK, r.text
    return r.json()


def _fluxo(client, header, dias=30):
    r = client.get(f"/api/v1/financeiro/fluxo-caixa?dias={dias}", headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    return r.json()


def _resumo(client, header):
    """O resumo do MES CORRENTE, que e o que a Visao Geral abre."""
    hoje = date.today()
    inicio = hoje.replace(day=1)
    r = client.get(
        "/api/v1/financeiro/resumo",
        params={"inicio": inicio.isoformat(), "fim": hoje.isoformat()},
        headers=header,
    )
    assert r.status_code == status.HTTP_200_OK, r.text
    return r.json()


def _funcionario(client, header):
    r = client.post("/api/v1/funcionarios/", json={
        "nome": "Tecnico", "cpf": "11122233355", "contato": "11999999999",
        "usuario": {"nome": "tec", "email": "tec.saldo@empresa.com", "senha": "SenhaForte123!"},
        "endereco": [{"logradouro": "Rua X", "numero": "1", "cep": "12345-678",
                      "bairro": "Centro", "cidade": "Lab City", "estado": "SP"}],
    }, headers=header)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _forma(client, header):
    r = client.post("/api/v1/formas-pagamento/", json={"nome": "Dinheiro", "ativo": True},
                    headers=header)
    if r.status_code == 201:
        return r.json()["id"]
    return client.get("/api/v1/formas-pagamento/", headers=header).json()[0]["id"]


def _cliente(client, header):
    r = client.post("/api/v1/clientes/cliente_pf", json={
        "nome": "Cliente OS", "cpf": "98765432199", "tipo": "PF", "celular": "11988887777",
        "endereco": [{"logradouro": "Rua Y", "numero": "10", "bairro": "Centro",
                      "cidade": "Campinas", "estado": "SP", "cep": "13010-000"}],
    }, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _os_finalizada(client, header, cliente_id, funcionario_id, *, valor,
                   custo_unitario=None, serie="SN-SALDO"):
    """Uma OS de servico, opcionalmente com o 'Custo para a loja' declarado.

    `custo_unitario` e o gasto que a loja teve com a peca comprada na hora --
    aquela que nunca foi cadastrada no estoque, que e o normal na oficina.
    """
    item = {"tipo": "SERVICO", "nome": "Reparo", "unidade_medida": "UN",
            "quantidade": 1, "valor_unitario": valor}
    if custo_unitario is not None:
        item["custo_unitario"] = custo_unitario

    numero = client.post("/api/v1/ordens-servico/", json={
        "cliente_id": cliente_id, "prioridade": "NORMAL", "defeito_relatado": "Nao liga",
        "dados_adicionais": {}, "funcionario_id": funcionario_id,
        "objeto": {"marca": "Dell", "modelo": "Inspiron", "numero_serie": serie,
                   "dados_adicionais": {}},
        "itens": [item],
    }, headers=header).json()["numero_os"]

    r = client.put(f"/api/v1/ordens-servico/{numero}/finalizar", json={
        "situacao_equipamento": "REPARADO", "garantia": "90 dias",
        "pagamentos": [{"forma_pagamento_id": _forma(client, header), "valor": valor}],
    }, headers=header)
    assert r.status_code == 200, r.text
    return numero


def _criar_e_pagar(client, header, *, valor, descricao, plano_conta_id=None):
    corpo = {"descricao": descricao, "valor": valor,
             "vencimento": date.today().isoformat()}
    if plano_conta_id is not None:
        corpo["plano_conta_id"] = plano_conta_id
    r = client.post("/api/v1/financeiro/contas-pagar", json=corpo, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    conta_id = r.json()["id"]

    r = client.post(f"/api/v1/financeiro/contas-pagar/{conta_id}/pagar", json={},
                    headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    return conta_id


def _categoria(client, header, nome, tipo):
    r = client.post("/api/v1/financeiro/plano-contas", json={"nome": nome, "tipo": tipo},
                    headers=header)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


# ===========================================================================
# O SALDO ANDA
# ===========================================================================

def test_o_saldo_sobe_quando_a_loja_vende(client, db_session):
    """O defeito relatado, no menor caso possivel.

    Declarar R$ 500 e faturar uma OS de R$ 150 tem que dar R$ 650. Antes desta
    correcao dava R$ 500 para sempre: o saldo so mudava quando alguem digitava
    outro numero a mao.
    """
    header = _auth(client)
    _informar_saldo(client, header, 50000)
    assert _fluxo(client, header)["saldo_inicial"] == 50000

    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)
    _os_finalizada(client, header, cliente_id, funcionario_id, valor=15000)

    fluxo = _fluxo(client, header)
    assert fluxo["saldo_inicial"] == 65000
    # As duas metades, que sao o que a tela mostra para o dono conferir.
    assert fluxo["saldo_ancora"] == 50000
    assert fluxo["saldo_movimentado"] == 15000


def test_o_saldo_desce_quando_a_loja_paga(client, db_session):
    header = _auth(client)
    _informar_saldo(client, header, 50000)

    _criar_e_pagar(client, header, valor=8990, descricao="Internet")

    fluxo = _fluxo(client, header)
    assert fluxo["saldo_movimentado"] == -8990
    assert fluxo["saldo_inicial"] == 50000 - 8990


def test_abertura_e_sangria_nao_mexem_no_saldo_da_loja(client, db_session):
    """Transferencia nao e dinheiro entrando nem saindo.

    O troco da abertura ja estava no cofre ontem; a sangria tira da gaveta e poe
    no cofre. Se qualquer um dos dois entrasse no saldo, a loja ganharia dinheiro
    do nada TODO dia em que abrisse o caixa -- e o erro cresceria sem parar.
    """
    header = _auth(client)
    _informar_saldo(client, header, 50000)

    config = db_session.query(ConfiguracaoVendas).first()
    if not config:
        config = ConfiguracaoVendas(empresa_id=1)
        db_session.add(config)
    config.controlar_caixa = True
    db_session.commit()

    abertura = client.post("/api/v1/caixa/abrir", json={"saldo_inicial": 20000},
                           headers=header)
    assert abertura.status_code in (200, 201), abertura.text

    sangria = client.post("/api/v1/caixa/sangria",
                          json={"valor": 5000, "motivo": "Levei ao banco"},
                          headers=header)
    assert sangria.status_code in (200, 201), sangria.text

    fluxo = _fluxo(client, header)
    assert fluxo["saldo_movimentado"] == 0, (
        "abertura e sangria sao transferencia: nao mudam quanto a loja TEM"
    )
    assert fluxo["saldo_inicial"] == 50000


def test_a_venda_anterior_a_declaracao_nao_e_contada_duas_vezes(client, db_session):
    """A armadilha do instante da ancora.

    O dono vende de manha, confere a gaveta a tarde e digita o que contou --
    e o que ele contou JA INCLUI a venda da manha. Sem o instante, ela entraria
    de novo e o saldo sairia inflado.
    """
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)

    # Manha: a venda acontece ANTES de o dono declarar.
    _os_finalizada(client, header, cliente_id, funcionario_id, valor=20000)

    # Tarde: ele conta a gaveta e acha R$ 700 (os 500 que ja tinha + os 200).
    _informar_saldo(client, header, 70000)

    fluxo = _fluxo(client, header)
    assert fluxo["saldo_movimentado"] == 0
    assert fluxo["saldo_inicial"] == 70000, "a venda da manha ja estava no que ele contou"

    # E a venda DEPOIS da declaracao entra normalmente.
    _os_finalizada(client, header, cliente_id, funcionario_id, valor=3000,
                   serie="SN-SALDO-2")
    assert _fluxo(client, header)["saldo_inicial"] == 73000


def test_conta_sem_ancora_nao_inventa_saldo(client, db_session):
    """Sem ponto de partida nao ha saldo, e o movimento sozinho nao vira um.

    Se contasse, uma loja que nunca declarou nada apareceria com saldo NEGATIVO
    no primeiro boleto pago -- que e pior que nao mostrar numero nenhum.
    """
    header = _auth(client)
    _criar_e_pagar(client, header, valor=8990, descricao="Internet")

    fluxo = _fluxo(client, header)
    assert fluxo["saldo_declarado"] is False
    assert fluxo["saldo_inicial"] == 0
    assert fluxo["saldo_movimentado"] == 0


def test_conta_desativada_sai_do_saldo(client, db_session):
    """Dinheiro que a loja nao usa mais nao pode sustentar projecao."""
    header = _auth(client)
    conta_id = _conta_id(client, header)
    _informar_saldo(client, header, 50000)
    assert _fluxo(client, header)["saldo_inicial"] == 50000

    r = client.patch(f"/api/v1/financeiro/contas-bancarias/{conta_id}",
                     json={"ativo": False}, headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text

    assert _fluxo(client, header)["saldo_inicial"] == 0


# ===========================================================================
# O LUCRO DESCONTA O CUSTO
# ===========================================================================

def test_o_caso_da_bateria_de_60_num_servico_de_160(client, db_session):
    """O chamado que abriu esta correcao, numero por numero.

    Servico de R$ 160, bateria de R$ 60 comprada na hora e declarada no "Custo
    para a loja" do item. O lucro tem que ser R$ 100 -- e aparecia R$ 160,
    porque o custo so existia no modulo de Relatorios.
    """
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)

    _os_finalizada(client, header, cliente_id, funcionario_id,
                   valor=16000, custo_unitario=6000)

    resumo = _resumo(client, header)
    assert resumo["faturamento"] == 16000
    assert resumo["custo_mercadorias"] == 6000
    assert resumo["resultado"] == 10000, "faturado - custo da peca - despesas"
    assert resumo["lucro_bruto"] == 10000


def test_despesa_desconta_do_lucro_e_compra_de_mercadoria_nao(client, db_session):
    """A distincao que impede a mesma peca de ser descontada duas vezes.

    Internet e despesa: sai do lucro no mes em que e paga.
    Compra de mercadoria e CUSTO: o dinheiro virou estoque, e so sai do lucro
    quando a peca for vendida (pelo CMV). Nos dois casos o dinheiro sai do
    CAIXA -- por isso `saiu_caixa` conta os dois.
    """
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)
    _os_finalizada(client, header, cliente_id, funcionario_id, valor=50000)

    _criar_e_pagar(client, header, valor=8990, descricao="Internet")

    # A categoria semeada como CUSTO pelo proprio sistema.
    planos = client.get("/api/v1/financeiro/plano-contas", headers=header).json()
    mercadoria = next(p for p in planos if p["nome"] == "Fornecedores / Mercadoria")
    assert mercadoria["tipo"] == "CUSTO", "comprar mercadoria nao e despesa"
    _criar_e_pagar(client, header, valor=30000, descricao="Pecas do fornecedor",
                   plano_conta_id=mercadoria["id"])

    resumo = _resumo(client, header)
    assert resumo["despesas_pagas"] == 8990
    assert resumo["compras_estoque"] == 30000
    assert resumo["resultado"] == 50000 - 8990, "a compra de estoque nao sai do lucro"
    # Mas os dois sairam do caixa.
    assert resumo["saiu_caixa"] == 8990 + 30000
    assert resumo["sobrou_caixa"] == 50000 - 8990 - 30000


def test_conta_sem_categoria_conta_como_despesa(client, db_session):
    """O lado seguro do erro.

    Uma compra nao classificada some do lucro no mes da compra, o que
    SUBESTIMA o lucro. Trata-la como custo inventaria lucro que nao existe --
    e lucro inventado o dono so descobre quando o dinheiro nao esta la.
    """
    header = _auth(client)
    _criar_e_pagar(client, header, valor=4000, descricao="Nao sei o que foi")

    resumo = _resumo(client, header)
    assert resumo["despesas_pagas"] == 4000
    assert resumo["compras_estoque"] == 0


def test_a_loja_pode_marcar_a_propria_categoria_como_compra_de_mercadoria(client, db_session):
    """Sem isto, quem criou "Compra de pecas" a mao fica com o lucro errado para sempre."""
    header = _auth(client)
    plano_id = _categoria(client, header, "Compra de pecas", "DESPESA")
    _criar_e_pagar(client, header, valor=12000, descricao="Pecas",
                   plano_conta_id=plano_id)

    assert _resumo(client, header)["despesas_pagas"] == 12000

    r = client.patch(f"/api/v1/financeiro/plano-contas/{plano_id}",
                     json={"tipo": "CUSTO"}, headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text

    # A correcao alcanca o mes que ja passou: o lucro e recalculado na leitura.
    resumo = _resumo(client, header)
    assert resumo["despesas_pagas"] == 0
    assert resumo["compras_estoque"] == 12000


def test_categoria_em_uso_nao_pode_virar_receita(client, db_session):
    """DESPESA <-> CUSTO e correcao; envolver RECEITA inverte o sinal do dinheiro."""
    header = _auth(client)
    plano_id = _categoria(client, header, "Contador", "DESPESA")
    _criar_e_pagar(client, header, valor=20000, descricao="Honorarios",
                   plano_conta_id=plano_id)

    r = client.patch(f"/api/v1/financeiro/plano-contas/{plano_id}",
                     json={"tipo": "RECEITA"}, headers=header)
    assert r.status_code == status.HTTP_400_BAD_REQUEST, r.text


# ===========================================================================
# O ENDERECO DO DINHEIRO
# ===========================================================================

def test_o_dinheiro_da_os_cai_numa_conta(client, db_session):
    """Movimento sem conta e dinheiro que entrou e nao aparece em saldo nenhum.

    Ate 02/09/2026 `registrar_movimento` nem aceitava conta bancaria, e toda
    venda e toda OS nasciam com a coluna nula.
    """
    from app.db.models.movimentacao_financeira import MovimentacaoFinanceira

    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)
    _os_finalizada(client, header, cliente_id, funcionario_id, valor=15000)

    movimentos = (
        db_session.query(MovimentacaoFinanceira)
        .filter(MovimentacaoFinanceira.origem == "ORDEM_SERVICO")
        .all()
    )
    assert movimentos, "a OS finalizada tem que escrever no livro"
    principal = db_session.query(ContaBancaria).filter(
        ContaBancaria.empresa_id == 1
    ).first()
    for movimento in movimentos:
        assert movimento.conta_bancaria_id == principal.id


def test_linha_antiga_sem_conta_entra_no_saldo_da_principal(client, db_session):
    """As orfas nao podem sumir do saldo.

    Elas existem por dois motivos legitimos: sao anteriores a coluna, ou a conta
    para onde apontavam foi apagada (a FK e SET NULL, para linha de dinheiro
    nunca desaparecer). Descarta-las deixaria o saldo ABAIXO do real -- que e o
    proprio defeito que esta correcao veio consertar.
    """
    from app.db.models.movimentacao_financeira import MovimentacaoFinanceira

    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)
    _informar_saldo(client, header, 50000)
    _os_finalizada(client, header, cliente_id, funcionario_id, valor=15000)

    # Simula a linha antiga: o dinheiro andou, mas sem endereco.
    movimento = (
        db_session.query(MovimentacaoFinanceira)
        .filter(MovimentacaoFinanceira.origem == "ORDEM_SERVICO")
        .first()
    )
    movimento.conta_bancaria_id = None
    db_session.commit()

    assert _fluxo(client, header)["saldo_inicial"] == 65000


# ===========================================================================
# A PROJECAO USA O SALDO NOVO
# ===========================================================================

def test_a_projecao_parte_do_saldo_de_hoje_e_nao_da_declaracao_velha(client, db_session):
    """O elo que fecha a conta do dono.

    Declarou R$ 100, vendeu R$ 500 e tem R$ 200 de conta a vencer: a projecao
    tem que terminar em R$ 400. Com a foto parada terminava em -R$ 100 e a tela
    anunciava que o dinheiro ia acabar -- com a gaveta cheia.
    """
    header = _auth(client)
    _informar_saldo(client, header, 10000)

    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)
    _os_finalizada(client, header, cliente_id, funcionario_id, valor=50000)

    r = client.post("/api/v1/financeiro/contas-pagar", json={
        "descricao": "Fornecedor", "valor": 20000,
        "vencimento": (date.today() + timedelta(days=5)).isoformat(),
    }, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text

    fluxo = _fluxo(client, header)
    assert fluxo["saldo_inicial"] == 60000
    assert fluxo["saldo_final"] == 40000
    assert fluxo["primeiro_dia_negativo"] is None, (
        "com a gaveta cheia, a tela nao pode anunciar que o dinheiro vai acabar"
    )
