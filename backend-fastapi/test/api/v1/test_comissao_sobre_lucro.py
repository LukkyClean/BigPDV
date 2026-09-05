# ---------------------------------------------------------------------------
# A comissao sai do LUCRO, nao do faturamento.
#
# O caso, do dono em 05/09/2026, olhando o extrato da propria loja:
# "no serviço de 240 teve gasto de 165 e no de 270 teve gasto de 90 reais.
#  Como eu vou pagar comissão de uma peça? O certo é pagar só o serviço."
#
# Nesta loja a peca vai EMBUTIDA no preco do servico: o cliente ve "Troca de
# Tela R$ 240" e nunca o preco da tela. O padrao de mercado e itemizar (servico
# R$ 75 + peca R$ 165) e comissionar so a linha de servico -- mas isso exporia a
# peca na via do cliente, que a loja nao quer. Entao a base desconta o
# `custo_unitario` declarado no item, que e interno e nunca impresso.
#
# ⚠️ TROCAR A BASE SEM RECALIBRAR O PERCENTUAL E CORTE DE SALARIO.
# 5% de 240 = R$ 12,00; 5% de 75 = R$ 3,75. Margem e um numero menor, entao o
# percentual sobre ela precisa ser maior para o tecnico manter o que ganhava.
# Os testes daqui usam 5% de proposito, para o tamanho da queda ficar visivel.
# ---------------------------------------------------------------------------

from datetime import date

from fastapi import status

from app.db.models.contador_venda import ContadorVenda

TEST_USER_EMAIL = "teste.comissaolucro@example.com"
TEST_USER_PASSWORD = "senhaSegura456"


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
        "razao_social": "Empresa Comissao Lucro LTDA", "nome_fantasia": "ComLucro",
        "is_cnpj": True, "documento": "12345678000199",
        "regime_tributario": "Simples Nacional", "celular": "11999998888",
        "segmento": "assistencia_tecnica",
        "endereco": [{"logradouro": "Av. Paulista", "numero": "1000",
                      "bairro": "Bela Vista", "cidade": "São Paulo",
                      "estado": "SP", "cep": "01310-100"}],
    }, headers=header)
    assert r.status_code == 201, r.text
    return header


def _cargo(client, header, venda_bp=500, servico_bp=500):
    r = client.post("/api/v1/cargos/", json={
        "nome": "Tecnico", "permissoes": {},
        "comissao_venda_percentual": venda_bp,
        "comissao_servico_percentual": servico_bp,
    }, headers=header)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _funcionario(client, header, cargo_id):
    r = client.post("/api/v1/funcionarios/", json={
        "nome": "Alan Tecnico", "cpf": "11122233344", "contato": "11999999999",
        "usuario": {"nome": "alan", "email": "alan@empresa.com",
                    "senha": "SenhaForte123!"},
        "endereco": [{"logradouro": "Rua X", "numero": "1", "cep": "12345-678",
                      "bairro": "Centro", "cidade": "Lab City", "estado": "SP"}],
    }, headers=header)
    assert r.status_code in (200, 201), r.text
    func_id = r.json()["id"]
    lk = client.put(f"/api/v1/funcionarios/{func_id}/cargo?cargo_id={cargo_id}",
                    headers=header)
    assert lk.status_code == 200, lk.text
    return func_id


def _cliente(client, header):
    r = client.post("/api/v1/clientes/cliente_pf", json={
        "tipo": "PF", "nome": "Wilton Cliente", "cpf": "98765432101",
        "celular": "11988887777",
        "endereco": [{"logradouro": "Rua Y", "numero": "2", "cep": "12345-678",
                      "bairro": "Centro", "cidade": "Lab City", "estado": "SP"}],
    }, headers=header)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _forma_pagamento(client, header):
    r = client.post("/api/v1/formas-pagamento/", json={
        "nome": "Dinheiro", "ativo": True,
    }, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _os_servico(client, header, cliente_id, fp_id, serie, valor, custo, func_id):
    """OS com UM item de serviço cujo preço embute a peça.

    `custo_unitario` é o "Custo para a loja" — interno, nunca impresso. É o
    campo que separa a mão de obra do repasse da peça.
    """
    item = {
        "tipo": "SERVICO", "nome": "Troca de Tela", "unidade_medida": "UN",
        "quantidade": 1, "valor_unitario": valor,
    }
    if custo is not None:
        item["custo_unitario"] = custo

    r = client.post("/api/v1/ordens-servico/", json={
        "cliente_id": cliente_id, "prioridade": "NORMAL",
        "defeito_relatado": "Tela quebrada", "dados_adicionais": {},
        "funcionario_id": func_id,
        "objeto": {"marca": "Samsung", "modelo": "A05s", "numero_serie": serie,
                   "dados_adicionais": {}},
        "itens": [item],
    }, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    numero = r.json()["numero_os"]

    rf = client.put(f"/api/v1/ordens-servico/{numero}/finalizar", json={
        "situacao_equipamento": "REPARADO", "garantia": "90 dias",
        "pagamentos": [{"forma_pagamento_id": fp_id, "valor": valor}],
    }, headers=header)
    assert rf.status_code == 200, rf.text
    return numero


def _comissao(client, header, func_id):
    hoje = date.today().isoformat()
    r = client.get(f"/api/v1/relatorios/comissoes?inicio={hoje}&fim={hoje}",
                   headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    alvo = next((i for i in r.json()["itens"] if i["funcionario_id"] == func_id), None)
    assert alvo is not None, r.json()["itens"]
    return alvo


# ===========================================================================
# O CASO DO DONO
# ===========================================================================

def test_comissao_de_servico_desconta_a_peca_embutida(client, db_session):
    """Troca de Tela R$ 240 com tela de R$ 165: comissão sobre R$ 75.

    Antes: 5% de 240 = R$ 12,00 -- o dono pagava comissão sobre a tela.
    Agora: 5% de  75 = R$  3,75 -- só sobre a mão de obra.
    """
    _seed_contador_venda(db_session)
    header = _auth(client)
    cargo_id = _cargo(client, header, servico_bp=500)  # 5,00%
    func_id = _funcionario(client, header, cargo_id)
    cliente_id = _cliente(client, header)
    fp_id = _forma_pagamento(client, header)

    _os_servico(client, header, cliente_id, fp_id, "SN-WILTON",
                valor=24000, custo=16500, func_id=func_id)

    alvo = _comissao(client, header, func_id)
    assert alvo["faturamento_os"] == 7500, "240 − 165 = 75 de mão de obra"
    assert alvo["comissao_servico"] == 375, "5% de 75,00 = R$ 3,75"


def test_servico_sem_peca_comissiona_o_valor_cheio(client, db_session):
    """Formatação de R$ 80 sem peça nenhuma: a base é os R$ 80 inteiros.

    O contraste que prova que a mudança não é um desconto linear -- serviço que
    é 100% mão de obra continua pagando sobre tudo, como sempre pagou.
    """
    _seed_contador_venda(db_session)
    header = _auth(client)
    cargo_id = _cargo(client, header, servico_bp=500)
    func_id = _funcionario(client, header, cargo_id)
    cliente_id = _cliente(client, header)
    fp_id = _forma_pagamento(client, header)

    _os_servico(client, header, cliente_id, fp_id, "SN-FORMAT",
                valor=8000, custo=None, func_id=func_id)

    alvo = _comissao(client, header, func_id)
    assert alvo["faturamento_os"] == 8000
    assert alvo["comissao_servico"] == 400, "5% de 80,00"


def test_custo_em_branco_paga_como_antes(client, db_session):
    """Item sem `custo_unitario` é lido como 100% mão de obra.

    É a MESMA asserção do teste acima por um motivo diferente, e por isso ele
    existe separado: aqui o ponto é o modo de falha. Se o técnico esquecer de
    preencher o custo, o sistema paga sobre o valor cheio -- o erro é a favor do
    funcionário e nunca contra ele, que é o lado certo de errar. Quem quiser
    trocar isso por uma trava tem que decidir antes o que fazer com a OS que já
    foi finalizada sem custo.
    """
    _seed_contador_venda(db_session)
    header = _auth(client)
    cargo_id = _cargo(client, header, servico_bp=1000)  # 10%
    func_id = _funcionario(client, header, cargo_id)
    cliente_id = _cliente(client, header)
    fp_id = _forma_pagamento(client, header)

    _os_servico(client, header, cliente_id, fp_id, "SN-SEMCUSTO",
                valor=24000, custo=None, func_id=func_id)

    alvo = _comissao(client, header, func_id)
    assert alvo["faturamento_os"] == 24000, "sem custo declarado, tudo é mão de obra"
    assert alvo["comissao_servico"] == 2400


def test_o_mes_do_dono_soma_so_a_mao_de_obra(client, db_session):
    """Os dois serviços do print: Wilton 240/165 e Luciana 270/90.

    Mão de obra: 75 + 180 = 255. Antes a base seria 240 + 270 = 510 -- ou seja,
    metade do que o dono pagava de comissão era repasse de peça.
    """
    _seed_contador_venda(db_session)
    header = _auth(client)
    cargo_id = _cargo(client, header, servico_bp=500)
    func_id = _funcionario(client, header, cargo_id)
    cliente_id = _cliente(client, header)
    fp_id = _forma_pagamento(client, header)

    _os_servico(client, header, cliente_id, fp_id, "SN-WILTON",
                valor=24000, custo=16500, func_id=func_id)
    _os_servico(client, header, cliente_id, fp_id, "SN-LUCIANA",
                valor=27000, custo=9000, func_id=func_id)

    alvo = _comissao(client, header, func_id)
    assert alvo["faturamento_os"] == 25500, "75 + 180"
    assert alvo["comissao_servico"] == 1275, "5% de 255,00"


# ===========================================================================
# VENDA DE BALCAO -- a base e a MARGEM
# ===========================================================================

def test_comissao_de_venda_sai_da_margem_e_nao_do_faturamento(client, db_session):
    """Produto vendido a R$ 100 que custou R$ 60: comissão sobre R$ 40.

    Pesquisa de mercado (05/09/2026): os dois modelos existem, mas comissionar
    faturamento faz o vendedor priorizar o item CARO em vez do LUCRATIVO. Numa
    loja de informática, onde a tela tem 30% de margem e a formatação tem 100%,
    a diferença de incentivo é grande -- por isso a base aqui é a margem.
    """
    _seed_contador_venda(db_session)
    header = _auth(client)
    cargo_id = _cargo(client, header, venda_bp=500)
    func_id = _funcionario(client, header, cargo_id)
    fp_id = _forma_pagamento(client, header)

    p = client.post("/api/v1/produtos/", json={
        "nome": "Cabo HDMI", "codigo_produto": "CABO-1", "unidade_medida": "UN",
        "estoque": {"valor_varejo": 10000, "valor_entrada": 6000, "quantidade": 10},
    }, headers=header)
    assert p.status_code == 201, p.text
    produto_id = p.json()["id"]

    cv = client.post("/api/v1/vendas/", json={"funcionario_id": func_id},
                     headers=header)
    assert cv.status_code == 201, cv.text
    venda_id = cv.json()["id"]
    add = client.post(f"/api/v1/vendas/{venda_id}/itens", json={
        "tipo_produto": "CADASTRADO", "produto_id": produto_id, "quantidade": 1,
    }, headers=header)
    assert add.status_code == 201, add.text
    fin = client.post(f"/api/v1/vendas/{venda_id}/finalizar", json={
        "acrescimo": 0,
        "pagamentos": [{"forma_pagamento_id": fp_id, "valor": 10000,
                        "parcelado": False, "qtd_parcelas": None}],
    }, headers=header)
    assert fin.status_code == 200, fin.text

    alvo = _comissao(client, header, func_id)
    assert alvo["faturamento_vendas"] == 4000, "100 − 60 = 40 de margem"
    assert alvo["comissao_vendas"] == 200, "5% de 40,00 = R$ 2,00"


# ===========================================================================
# O EXTRATO -- o papel que o tecnico usa para conferir o proprio pagamento
# ===========================================================================

def test_extrato_mostra_a_mao_de_obra_que_a_comissao_paga(client, db_session):
    """O extrato tem que mostrar a MESMA base que a comissão usa.

    Antes desta mudança havia uma divergência que ninguém tinha notado: o
    extrato somava o valor cheio dos serviços e a comissão saía de outra conta.
    O técnico conferia um número e recebia sobre outro -- e quem não consegue
    conferir o próprio pagamento desconfia dele.
    """
    _seed_contador_venda(db_session)
    header = _auth(client)
    cargo_id = _cargo(client, header, servico_bp=500)
    func_id = _funcionario(client, header, cargo_id)
    cliente_id = _cliente(client, header)
    fp_id = _forma_pagamento(client, header)

    _os_servico(client, header, cliente_id, fp_id, "SN-WILTON",
                valor=24000, custo=16500, func_id=func_id)
    _os_servico(client, header, cliente_id, fp_id, "SN-LUCIANA",
                valor=27000, custo=9000, func_id=func_id)

    hoje = date.today().isoformat()
    r = client.get(
        f"/api/v1/relatorios/extrato-funcionario?funcionario_id={func_id}&inicio={hoje}&fim={hoje}",
        headers=header,
    )
    assert r.status_code == status.HTTP_200_OK, r.text
    body = r.json()

    assert body["valor_total"] == 51000, "o que o cliente pagou: 240 + 270"
    assert body["total_mao_de_obra"] == 25500, "o que a loja ganhou: 75 + 180"

    wilton = next(i for i in body["itens"] if i["valor_total"] == 24000)
    assert wilton["custo"] == 16500
    assert wilton["mao_de_obra"] == 7500

    # A amarração que importa: o extrato e a comissão falam do mesmo número.
    assert body["total_mao_de_obra"] == _comissao(client, header, func_id)["faturamento_os"]
