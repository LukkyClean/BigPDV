# ---------------------------------------------------------------------------
# O livro do dinheiro NÃO depende mais do controle de caixa (29/08/2026).
#
# Antes, venda e OS só escreviam em `movimentacoes_financeiras` com
# `controlar_caixa` ligado E turno aberto. A loja que trabalha sem gaveta abria
# o Extrato e não via venda nenhuma -- como se o dinheiro nunca tivesse entrado.
#
# O que este arquivo protege é a metade DELICADA da mudança: sem turno, a linha
# nasce com `sessao_caixa_id` NULO, e é isso que mantém o fechamento das lojas
# que usam gaveta exatamente como era. Se um dia um teste daqui falhar dizendo
# que a sessão não é nula, o dinheiro de quem não usa caixa passou a cair no
# turno de alguém.
# ---------------------------------------------------------------------------

from datetime import date, timedelta

from starlette import status

from app.db.models.configuracao_vendas import ConfiguracaoVendas
from app.db.models.movimentacao_financeira import MovimentacaoFinanceira
from app.db.models.sessao_caixa import SessaoCaixa

TEST_USER_EMAIL = "livro.dono@example.com"
TEST_USER_PASSWORD = "senhaSegura789"


# ===========================================================================
# HELPERS
# ===========================================================================

def _auth(client):
    client.post("/api/v1/usuarios/", json={
        "nome": "Dono sem Gaveta", "email": TEST_USER_EMAIL, "senha": TEST_USER_PASSWORD,
    })
    login = client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": "hwid-livro",
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post("/api/v1/empresas/", json={
        "razao_social": "Sem Gaveta LTDA", "nome_fantasia": "Sem Gaveta", "is_cnpj": True,
        "documento": "12345678000188", "regime_tributario": "Simples Nacional",
        "celular": "11999997777", "segmento": "assistencia_tecnica",
        "endereco": [{"logradouro": "Av. Brasil", "numero": "500", "bairro": "Centro",
                      "cidade": "São Paulo", "estado": "SP", "cep": "01310-100"}],
    }, headers=header)
    return header


def _config_caixa(db_session, **campos):
    config = db_session.query(ConfiguracaoVendas).first()
    if not config:
        config = ConfiguracaoVendas(empresa_id=1)
        db_session.add(config)
    for campo, valor in campos.items():
        setattr(config, campo, valor)
    db_session.commit()


def _funcionario(client, header):
    r = client.post("/api/v1/funcionarios/", json={
        "nome": "Tecnico", "cpf": "11122233355", "contato": "11999999999",
        "usuario": {"nome": "tec", "email": "tec.livro@empresa.com", "senha": "SenhaForte123!"},
        "endereco": [{"logradouro": "Rua X", "numero": "1", "cep": "12345-678",
                      "bairro": "Centro", "cidade": "Lab City", "estado": "SP"}],
    }, headers=header)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _forma(client, header, nome="Dinheiro"):
    r = client.post("/api/v1/formas-pagamento/", json={"nome": nome, "ativo": True},
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


def _os_finalizada(client, header, cliente_id, funcionario_id, serie="SN-LIVRO",
                   valor=15000, vencimento=None):
    numero = client.post("/api/v1/ordens-servico/", json={
        "cliente_id": cliente_id, "prioridade": "NORMAL", "defeito_relatado": "Nao liga",
        "dados_adicionais": {}, "funcionario_id": funcionario_id,
        "objeto": {"marca": "Dell", "modelo": "Inspiron", "numero_serie": serie,
                   "dados_adicionais": {}},
        "itens": [{"tipo": "SERVICO", "nome": "Reparo", "unidade_medida": "UN",
                   "quantidade": 1, "valor_unitario": valor}],
    }, headers=header).json()["numero_os"]

    fp_id = _forma(client, header)
    pagamento = {"forma_pagamento_id": fp_id, "valor": valor}
    if vencimento:
        pagamento["vencimento"] = vencimento.isoformat()
    r = client.put(f"/api/v1/ordens-servico/{numero}/finalizar", json={
        "situacao_equipamento": "REPARADO", "garantia": "90 dias",
        "pagamentos": [pagamento],
    }, headers=header)
    assert r.status_code == 200, r.text
    return numero


# ===========================================================================
# SEM CONTROLE DE CAIXA
# ===========================================================================

def test_os_sem_controle_de_caixa_entra_no_livro_sem_turno(client, db_session):
    header = _auth(client)
    _config_caixa(db_session, controlar_caixa=False)
    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)

    _os_finalizada(client, header, cliente_id, funcionario_id, valor=15000)

    movimentos = db_session.query(MovimentacaoFinanceira).all()
    assert len(movimentos) == 1
    assert movimentos[0].origem == "ORDEM_SERVICO"
    assert movimentos[0].valor == 15000
    # A linha que protege quem USA gaveta: sem turno, sessão nula.
    assert movimentos[0].sessao_caixa_id is None
    assert db_session.query(SessaoCaixa).count() == 0


def test_o_extrato_enxerga_a_loja_que_nao_usa_caixa(client, db_session):
    """O motivo da mudança, do ponto de vista de quem abre a tela."""
    header = _auth(client)
    _config_caixa(db_session, controlar_caixa=False)
    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)

    _os_finalizada(client, header, cliente_id, funcionario_id, valor=15000)

    extrato = client.get("/api/v1/financeiro/extrato", headers=header).json()
    assert extrato["total_itens"] == 1
    assert extrato["total_entradas"] == 15000
    assert extrato["itens"][0]["origem"] == "ORDEM_SERVICO"


def test_promessa_continua_fora_do_livro_sem_caixa(client, db_session):
    """A regra da promessa é ORTOGONAL a esta mudança, e sobreviveu inteira.

    Vencimento futuro vira conta a receber; o movimento nasce no dia do
    pagamento. Se isto quebrar, uma OS fiado passa a contar como dinheiro que
    entrou -- e o extrato mente para cima.
    """
    from app.db.models.conta_receber import ContaReceber

    header = _auth(client)
    _config_caixa(db_session, controlar_caixa=False)
    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)

    _os_finalizada(client, header, cliente_id, funcionario_id, valor=15000,
                   vencimento=date.today() + timedelta(days=20))

    assert db_session.query(ContaReceber).count() == 1
    assert db_session.query(MovimentacaoFinanceira).count() == 0


def test_reabrir_sem_pagamento_estorna_mesmo_sem_caixa(client, db_session):
    """A prova de "entrou" passou a ser o LIVRO, não o carimbo de sessão.

    Antes, o estorno pulava todo pagamento com `sessao_caixa_id` nulo -- e sem
    controle de caixa TODOS são nulos. A entrada ficaria no extrato sem a saída
    que a desfaz, para sempre.
    """
    header = _auth(client)
    _config_caixa(db_session, controlar_caixa=False)
    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)
    numero = _os_finalizada(client, header, cliente_id, funcionario_id, valor=15000)

    r = client.put(f"/api/v1/ordens-servico/{numero}/reabrir",
                   json={"cliente_pagou": False}, headers=header)
    assert r.status_code == 200, r.text

    movimentos = db_session.query(MovimentacaoFinanceira).order_by(
        MovimentacaoFinanceira.id
    ).all()
    assert len(movimentos) == 2, "a entrada e o estorno que a desfaz"
    assert movimentos[0].tipo == "ENTRADA"
    assert movimentos[1].tipo == "SAIDA"
    assert movimentos[1].valor == 15000


def test_reabrir_com_pagamento_real_nao_estorna_sem_caixa(client, db_session):
    """cliente_pagou=True: o dinheiro entrou de verdade e continua com a loja."""
    header = _auth(client)
    _config_caixa(db_session, controlar_caixa=False)
    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)
    numero = _os_finalizada(client, header, cliente_id, funcionario_id, valor=15000)

    client.put(f"/api/v1/ordens-servico/{numero}/reabrir",
               json={"cliente_pagou": True}, headers=header)

    assert db_session.query(MovimentacaoFinanceira).count() == 1, "nada a estornar"


# ===========================================================================
# COM CONTROLE DE CAIXA, MAS SEM TURNO ABERTO
# ===========================================================================

def test_com_caixa_ligado_e_sem_turno_a_linha_nasce_sem_sessao(client, db_session):
    """O terceiro ambiente: a loja liga o controle mas vende fora de turno.

    Era o buraco mais silencioso dos três -- a loja acreditava estar
    registrando tudo.
    """
    header = _auth(client)
    # `exigir_caixa_aberto` fica desligado: é o que permite vender sem turno.
    _config_caixa(db_session, controlar_caixa=True, exigir_caixa_aberto=False)
    funcionario_id = _funcionario(client, header)
    cliente_id = _cliente(client, header)

    _os_finalizada(client, header, cliente_id, funcionario_id, valor=9000)

    movimentos = db_session.query(MovimentacaoFinanceira).all()
    assert len(movimentos) == 1
    assert movimentos[0].sessao_caixa_id is None
    assert db_session.query(SessaoCaixa).count() == 0
