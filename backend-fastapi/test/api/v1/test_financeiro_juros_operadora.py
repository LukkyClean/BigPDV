# ---------------------------------------------------------------------------
# O juros de parcelamento repassado ao cliente NAO e dinheiro da loja.
#
# O caso, contado pelo dono em 05/09/2026: "eu vendo 1.000, simulo o juros na
# maquina, da 150, o cliente paga 1.150 e so cai 1.000 na minha conta, pois a
# empresa do cartao ja desconta o dela".
#
# Ou seja: os 150 nunca encostam na loja. Mesmo assim o sistema os tratava como
# receita em quatro lugares diferentes -- Faturado, livro do dinheiro, conta a
# receber e base de comissao -- porque todos eles leem `Venda.total`, e o total
# ja vem com o `acrescimo` somado dentro.
#
# A invariante que sustenta a correcao (verificada no frontend dos dois lados,
# useFinishSaleModal.ts e OSPagamentoModal.vue):
#
#     acrescimo == soma(juros_valor onde juros_responsavel == CLIENTE)
#
# e, como `total = base + acrescimo`, subtrair o acrescimo devolve a base
# EXATA. Nao e estimativa nem percentual arbitrado.
#
# O contraste com o juros absorvido pela LOJA esta em cada teste de proposito:
# ali o cliente paga o preco combinado, o acrescimo e zero e nada muda. Sem o
# par, uma correcao que zerasse os dois casos passaria despercebida.
# ---------------------------------------------------------------------------

from datetime import date

from fastapi import status

from app.db.models.contador_venda import ContadorVenda

TEST_USER_EMAIL = "teste.jurosoperadora@example.com"
TEST_USER_PASSWORD = "senhaSegura456"

BASE = 100000    # R$ 1.000,00 -- o que a loja vende
JUROS = 15000    # R$    150,00 -- o que a operadora cobra do cliente
BRUTO = BASE + JUROS  # R$ 1.150,00 -- o que o cliente desembolsa


def _seed_contador_venda(db_session):
    if not db_session.query(ContadorVenda).first():
        db_session.add(ContadorVenda(id=1, proximo_numero=1))
        db_session.commit()


def _auth(client):
    client.post("/api/v1/usuarios/", json={
        "nome": "Admin Master", "email": TEST_USER_EMAIL, "senha": TEST_USER_PASSWORD,
    })
    login = client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD,
        "hwid": "test-terminal-hwid",
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}
    r = client.post("/api/v1/empresas/", json={
        "razao_social": "Empresa Juros Operadora LTDA", "nome_fantasia": "JurosOp",
        "is_cnpj": True, "documento": "12345678000199",
        "regime_tributario": "Simples Nacional", "celular": "11999998888",
        "segmento": "assistencia_tecnica",
        "endereco": [{"logradouro": "Av. Paulista", "numero": "1000",
                      "bairro": "Bela Vista", "cidade": "São Paulo",
                      "estado": "SP", "cep": "01310-100"}],
    }, headers=header)
    assert r.status_code == 201, r.text
    return header


def _funcionario(client, header, cargo_id=None):
    r = client.post("/api/v1/funcionarios/", json={
        "nome": "Vendedor Teste", "cpf": "11122233344", "contato": "11999999999",
        "usuario": {"nome": "vendedor1", "email": "vend1@empresa.com",
                    "senha": "SenhaForte123!"},
        "endereco": [{"logradouro": "Rua X", "numero": "1", "cep": "12345-678",
                      "bairro": "Centro", "cidade": "Lab City", "estado": "SP"}],
    }, headers=header)
    assert r.status_code in (200, 201), r.text
    func_id = r.json()["id"]
    if cargo_id is not None:
        lk = client.put(
            f"/api/v1/funcionarios/{func_id}/cargo?cargo_id={cargo_id}", headers=header
        )
        assert lk.status_code == 200, lk.text
    return func_id


def _cargo_com_comissao(client, header, venda_bp):
    r = client.post("/api/v1/cargos/", json={
        "nome": "Vendedor", "permissoes": {},
        "comissao_venda_percentual": venda_bp, "comissao_servico_percentual": 0,
    }, headers=header)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _produto(client, header, codigo="P-JUROS", varejo=BASE, quantidade=10):
    r = client.post("/api/v1/produtos/", json={
        "nome": f"Produto {codigo}", "codigo_produto": codigo, "unidade_medida": "UN",
        "estoque": {"valor_varejo": varejo, "quantidade": quantidade},
    }, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _forma_pagamento(client, header, dias_para_receber=0):
    r = client.post("/api/v1/formas-pagamento/", json={
        "nome": "Cartão de Crédito", "ativo": True,
    }, headers=header)
    assert r.status_code == 201, r.text
    fp_id = r.json()["id"]
    if dias_para_receber:
        u = client.put(f"/api/v1/formas-pagamento/{fp_id}",
                       json={"dias_para_receber": dias_para_receber}, headers=header)
        assert u.status_code == 200, u.text
    return fp_id


def _vender(client, header, funcionario_id, produto_id, fp_id, responsavel="CLIENTE"):
    """Vende 1 item de R$ 1.000 com R$ 150 de juros de parcelamento.

    Monta o payload exatamente como o frontend monta: com CLIENTE o juros vem
    embutido no `valor` do pagamento e soma no `acrescimo` da venda; com LOJA o
    `valor` e so a base e o `acrescimo` fica zerado.
    """
    cv = client.post("/api/v1/vendas/", json={"funcionario_id": funcionario_id},
                     headers=header)
    assert cv.status_code == 201, cv.text
    venda_id = cv.json()["id"]

    add = client.post(f"/api/v1/vendas/{venda_id}/itens", json={
        "tipo_produto": "CADASTRADO", "produto_id": produto_id, "quantidade": 1,
    }, headers=header)
    assert add.status_code == 201, add.text

    repassa = responsavel == "CLIENTE"
    fin = client.post(f"/api/v1/vendas/{venda_id}/finalizar", json={
        "acrescimo": JUROS if repassa else 0,
        "pagamentos": [{
            "forma_pagamento_id": fp_id,
            "valor": BRUTO if repassa else BASE,
            "juros_valor": JUROS,
            "juros_responsavel": responsavel,
            "parcelado": True,
            "qtd_parcelas": 3,
            "bandeira_cartao": "VISA",
        }],
    }, headers=header)
    assert fin.status_code == 200, fin.text
    return venda_id, fin.json()


def _resumo(client, header):
    hoje = date.today()
    r = client.get("/api/v1/financeiro/resumo", params={
        "inicio": hoje.replace(day=1).isoformat(), "fim": hoje.isoformat(),
    }, headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    return r.json()


# ===========================================================================
# O QUE O CLIENTE PAGA -- nao muda, e nao pode mudar
# ===========================================================================

def test_o_cliente_continua_pagando_o_valor_cheio(client, db_session):
    """A venda vale 1.150 no cupom. O comprovante tem que bater com a fatura.

    Este teste existe para travar o que a correcao NAO pode encostar: o dono
    concordou em mexer no financeiro justamente porque o documento do cliente
    fica intacto. Se algum dia alguem "consertar" o total da venda, quebra aqui.
    """
    _seed_contador_venda(db_session)
    header = _auth(client)
    func_id = _funcionario(client, header)
    prod_id = _produto(client, header)
    fp_id = _forma_pagamento(client, header)

    _venda_id, venda = _vender(client, header, func_id, prod_id, fp_id)

    assert venda["total"] == BRUTO, "o cliente desembolsa 1.150"
    assert venda["acrescimo"] == JUROS, "e 150 disso e juros da operadora"
    assert venda["pagamentos"][0]["valor"] == BRUTO
    assert venda["pagamentos"][0]["juros_responsavel"] == "CLIENTE"


# ===========================================================================
# SITE 1 -- FATURADO
# ===========================================================================

def test_faturado_nao_conta_o_juros_da_operadora(client, db_session):
    """O card "Faturado" da Visao Geral deve mostrar 1.000, nao 1.150.

    Era o defeito que o dono viu na tela: o mes inteiro aparecia inflado pelo
    juros que a maquininha reteve.
    """
    _seed_contador_venda(db_session)
    header = _auth(client)
    func_id = _funcionario(client, header)
    prod_id = _produto(client, header)
    fp_id = _forma_pagamento(client, header)

    _vender(client, header, func_id, prod_id, fp_id)

    assert _resumo(client, header)["faturamento"] == BASE


def test_faturado_conta_tudo_quando_a_loja_absorve_o_juros(client, db_session):
    """Contraste: com LOJA o cliente paga 1.000 e a loja fatura 1.000.

    O acrescimo e zero, entao nao ha o que subtrair -- e o numero tem que ficar
    exatamente onde estava antes da correcao.
    """
    _seed_contador_venda(db_session)
    header = _auth(client)
    func_id = _funcionario(client, header)
    prod_id = _produto(client, header)
    fp_id = _forma_pagamento(client, header)

    _venda_id, venda = _vender(client, header, func_id, prod_id, fp_id,
                               responsavel="LOJA")
    assert venda["total"] == BASE, "a loja absorveu: o cliente paga o combinado"
    assert venda["acrescimo"] == 0

    assert _resumo(client, header)["faturamento"] == BASE


# ===========================================================================
# SITE 3 -- LIVRO DO DINHEIRO ("Entrou de fato")
# ===========================================================================

def test_entrou_de_fato_registra_so_o_que_a_loja_recebeu(client, db_session):
    """O livro do dinheiro nao pode registrar os 150 que nao chegaram.

    Anda junto com o Faturado de proposito: corrigir so um dos dois faria a
    tela dizer "R$ 150 a mais que o faturado -- cobranca de outros meses
    entrando", trocando uma mentira por outra.
    """
    _seed_contador_venda(db_session)
    header = _auth(client)
    func_id = _funcionario(client, header)
    prod_id = _produto(client, header)
    fp_id = _forma_pagamento(client, header)

    _vender(client, header, func_id, prod_id, fp_id)

    resumo = _resumo(client, header)
    assert resumo["entrou_caixa"] == BASE
    assert resumo["faturamento"] == resumo["entrou_caixa"], (
        "venda a vista no cartao: o que foi faturado e o que entrou sao o mesmo "
        "numero, e a tela precisa dizer 'tudo que foi faturado entrou'"
    )


# ===========================================================================
# SITE 2 -- CONTA A RECEBER (cartao com prazo)
# ===========================================================================

def test_recebivel_de_cartao_nasce_liquido_com_a_taxa_separada(client, db_session):
    """Com prazo declarado, a venda vira conta a receber -- do valor LIQUIDO.

    O contrato do model ja mandava fazer assim e ninguem cumpria:
    `valor` e "o que a operadora repassa, ja sem a taxa dela" e `taxa` e o
    "retido pela operadora", com `bruto = valor + taxa`. Guardar 1.150 em
    `valor` fazia o Fluxo de Caixa prometer dinheiro que nunca ia cair.
    """
    _seed_contador_venda(db_session)
    header = _auth(client)
    func_id = _funcionario(client, header)
    prod_id = _produto(client, header)
    fp_id = _forma_pagamento(client, header, dias_para_receber=30)

    _vender(client, header, func_id, prod_id, fp_id)

    r = client.get("/api/v1/financeiro/contas-receber", headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    itens = r.json()["itens"]
    assert len(itens) == 1, itens

    conta = itens[0]
    assert conta["valor"] == BASE, "so entra o que a operadora vai depositar"
    assert conta["taxa"] == JUROS, "o retido fica registrado, nao sumido"
    assert conta["valor"] + conta["taxa"] == BRUTO, "bruto = valor + taxa"


# ===========================================================================
# SITE 6 -- COMISSAO
# ===========================================================================

def test_comissao_nao_incide_sobre_o_juros_da_operadora(client, db_session):
    """5% de 1.000 = R$ 50. Antes da correcao o sistema pagava 5% de 1.150.

    ATENCAO -- esta correcao REDUZ o valor pago ao vendedor: de R$ 57,50 para
    R$ 50,00 no exemplo. Foi decisao explicita do dono em 05/09/2026, pelo
    argumento de que a loja nunca recebeu os R$ 150 e por isso nao ha de onde
    tirar comissao. Avisar a equipe antes de instalar.
    """
    _seed_contador_venda(db_session)
    header = _auth(client)
    cargo_id = _cargo_com_comissao(client, header, venda_bp=500)  # 5,00%
    func_id = _funcionario(client, header, cargo_id=cargo_id)
    prod_id = _produto(client, header)
    fp_id = _forma_pagamento(client, header)

    _vender(client, header, func_id, prod_id, fp_id)

    hoje = date.today().isoformat()
    r = client.get(f"/api/v1/relatorios/comissoes?inicio={hoje}&fim={hoje}",
                   headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text

    alvo = next((i for i in r.json()["itens"] if i["funcionario_id"] == func_id), None)
    assert alvo is not None, r.json()["itens"]
    assert alvo["faturamento_vendas"] == BASE, "a base da comissao e o liquido"
    assert alvo["comissao_vendas"] == 5000, "5% de 1.000, e nao os 5.750 de antes"


# ===========================================================================
# O DETALHE DO CUSTO -- o card "Custo do que vendeu" aberto
# ===========================================================================

def test_detalhe_do_custo_fecha_com_o_total_do_resumo(client, db_session):
    """A amarração que dá sentido ao detalhamento: ele TEM que fechar.

    Um detalhe que não bate com o total piora a desconfiança em vez de
    resolvê-la -- e o motivo de existir é justamente o oposto: em 05/09/2026 o
    dono passou uma tarde conferindo R$ 846 de CMV no papel sem ter onde abrir
    o número.
    """
    _seed_contador_venda(db_session)
    header = _auth(client)
    func_id = _funcionario(client, header)
    prod_id = _produto(client, header)
    fp_id = _forma_pagamento(client, header)

    _vender(client, header, func_id, prod_id, fp_id)

    hoje = date.today()
    r = client.get("/api/v1/financeiro/custo-detalhe", params={
        "inicio": hoje.replace(day=1).isoformat(), "fim": hoje.isoformat(),
    }, headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    detalhe = r.json()

    assert detalhe["total"] == _resumo(client, header)["custo_mercadorias"]
    assert len(detalhe["linhas"]) >= 1, detalhe
    linha = detalhe["linhas"][0]
    assert linha["origem"] == "VENDA"
    assert linha["fonte"] == "ESTOQUE", "peça do catálogo: custo vem do livro"
