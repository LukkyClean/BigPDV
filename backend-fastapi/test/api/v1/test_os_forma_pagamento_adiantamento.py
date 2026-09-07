# ---------------------------------------------------------------------------
# ARQUIVO: test/api/v1/test_os_forma_pagamento_adiantamento.py
# DESCRICAO: Forma de pagamento do adiantamento da OS.
#
# POR QUE ESTE ARQUIVO EXISTE. O adiantamento guardava so o NUMERO
# (`valor_entrada`, centavos). Nao havia como saber depois se o cliente adiantou
# em PIX, dinheiro ou cartao: o resumo da finalizacao mostrava o quanto faltava
# pagar, mas nem o valor adiantado em linha propria, nem a forma -- que nunca
# chegava a ser capturada.
#
# A forma NAO virou linha em `ordem_servico_pagamentos` de proposito: a trava de
# finalizacao e `sum(pagamentos) + valor_entrada == valor_total`, e criar a
# linha contaria o adiantamento duas vezes nas duas lojas em producao. Por isso
# e uma coluna na propria OS.
#
# Estes testes travam: (1) que a forma vai e volta, (2) que OS sem forma
# continua funcionando exatamente como antes, e (3) que zerar o adiantamento nao
# deixa forma pendurada sem valor por tras.
# ---------------------------------------------------------------------------

import pytest
from starlette import status

TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"


def _autenticar_e_criar_empresa(client, segmento: str = "assistencia_tecnica") -> dict:
    client.post("/api/v1/usuarios/", json={
        "nome": "Admin Master",
        "email": TEST_USER_EMAIL,
        "senha": TEST_USER_PASSWORD,
    })
    login = client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
        "hwid": "test-terminal-hwid",
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}

    r = client.post("/api/v1/empresas/", json={
        "razao_social": "Empresa Teste 000199 LTDA",
        "nome_fantasia": "Teste",
        "is_cnpj": True,
        "documento": "12345678000195",
        "regime_tributario": "Simples Nacional",
        "celular": "11999998888",
        "segmento": segmento,
        "endereco": [{
            "logradouro": "Av. Paulista", "numero": "1000", "bairro": "Bela Vista",
            "cidade": "São Paulo", "estado": "SP", "cep": "01310-100",
        }],
    }, headers=header)
    assert r.status_code == 201, r.text
    return header


def _criar_cliente(client, header: dict) -> int:
    r = client.post("/api/v1/clientes/cliente_pf", json={
        "nome": "Claudinha",
        "cpf": "52998224725",
        "tipo": "PF",
        "celular": "11987654321",
        "endereco": [{
            "logradouro": "Rua das Flores", "numero": "100", "bairro": "Centro",
            "cidade": "Campinas", "estado": "SP", "cep": "13010-000",
        }],
    }, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _id_forma_pagamento(client, header: dict, nome: str) -> int:
    """
    Cria a forma no catalogo.

    As formas padrao sao semeadas no startup (core/tarefas.py), mas a fixture
    `db_session` recria as tabelas a cada teste e leva a seed junto -- por isso
    cada teste cria a sua.
    """
    r = client.post(
        "/api/v1/formas-pagamento/",
        json={"nome": nome, "ativo": True},
        headers=header,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# Objeto minimo aceito por cada segmento. Serigrafia gera o identificador
# sozinha (ART-xxxx) e nao pede marca; as outras duas exigem.
OBJETO_POR_SEGMENTO = {
    "assistencia_tecnica": {"marca": "Apple", "modelo": "iPhone 11", "numero_serie": "ABC12345"},
    "oficina_mecanica": {"marca": "Fiat", "modelo": "Uno", "numero_serie": "ABC1D23"},
    "serigrafia": {"modelo": "Logo Claudinha frente"},
}


def _post_os(client, header: dict, cliente_id: int, segmento: str = "assistencia_tecnica", **extra):
    payload = {
        "cliente_id": cliente_id,
        "prioridade": "NORMAL",
        "defeito_relatado": "Tela quebrada",
        "dados_adicionais": {},
        "objeto": OBJETO_POR_SEGMENTO[segmento],
        "itens": [],
    }
    payload.update(extra)
    return client.post("/api/v1/ordens-servico/", json=payload, headers=header)


# =========================
# A forma vai e volta
# =========================

def test_adiantamento_guarda_a_forma_de_pagamento(client, db_session):
    header = _autenticar_e_criar_empresa(client)
    cliente_id = _criar_cliente(client, header)
    pix_id = _id_forma_pagamento(client, header, "PIX")

    r = _post_os(
        client, header, cliente_id,
        valor_entrada=20000,
        forma_pagamento_entrada_id=pix_id,
    )

    assert r.status_code == status.HTTP_201_CREATED, r.text
    corpo = r.json()
    assert corpo["valor_entrada"] == 20000
    # O Read expoe a forma inteira (nome incluso) — e o nome que a tela mostra.
    assert corpo["forma_pagamento_entrada"] is not None
    assert corpo["forma_pagamento_entrada"]["nome"].upper() == "PIX"


def test_adiantamento_sem_forma_continua_funcionando(client, db_session):
    """OS aberta antes do campo existir: valor sem forma e estado valido."""
    header = _autenticar_e_criar_empresa(client)
    cliente_id = _criar_cliente(client, header)

    r = _post_os(client, header, cliente_id, valor_entrada=15000)

    assert r.status_code == status.HTTP_201_CREATED, r.text
    corpo = r.json()
    assert corpo["valor_entrada"] == 15000
    assert corpo["forma_pagamento_entrada"] is None


def test_forma_inexistente_e_recusada(client, db_session):
    """
    A coluna e um FK sem constraint no SQLite (ver migration d3e4f5a6b7c8):
    sem esta validacao um id invalido entraria e viraria forma vazia na tela.
    """
    header = _autenticar_e_criar_empresa(client)
    cliente_id = _criar_cliente(client, header)

    r = _post_os(
        client, header, cliente_id,
        valor_entrada=20000,
        forma_pagamento_entrada_id=999999,
    )

    assert r.status_code == status.HTTP_404_NOT_FOUND, r.text


# =========================
# Os tres segmentos em pe
# =========================

@pytest.mark.parametrize(
    "segmento", ["assistencia_tecnica", "oficina_mecanica", "serigrafia"]
)
def test_adiantamento_com_forma_funciona_em_todos_os_segmentos(client, db_session, segmento):
    """
    O adiantamento nao e dado de segmento: mora na OS, ao lado de desconto e
    taxa de entrega. Informatica e oficina rodam em loja real e serigrafia
    acabou de entrar -- este teste e a prova de que a coluna nova nao
    privilegiou nem quebrou nenhum dos tres.
    """
    header = _autenticar_e_criar_empresa(client, segmento)
    cliente_id = _criar_cliente(client, header)
    pix_id = _id_forma_pagamento(client, header, "PIX")

    r = _post_os(
        client, header, cliente_id, segmento,
        valor_entrada=20000,
        forma_pagamento_entrada_id=pix_id,
    )

    assert r.status_code == status.HTTP_201_CREATED, r.text
    corpo = r.json()
    assert corpo["valor_entrada"] == 20000
    assert corpo["forma_pagamento_entrada"]["nome"].upper() == "PIX"


# =========================
# Edicao
# =========================

def test_edicao_troca_a_forma_do_adiantamento(client, db_session):
    header = _autenticar_e_criar_empresa(client)
    cliente_id = _criar_cliente(client, header)
    pix_id = _id_forma_pagamento(client, header, "PIX")
    dinheiro_id = _id_forma_pagamento(client, header, "Dinheiro")

    criada = _post_os(
        client, header, cliente_id,
        valor_entrada=20000,
        forma_pagamento_entrada_id=pix_id,
    )
    numero_os = criada.json()["numero_os"]

    r = client.put(
        f"/api/v1/ordens-servico/{numero_os}",
        json={"forma_pagamento_entrada_id": dinheiro_id},
        headers=header,
    )

    assert r.status_code == status.HTTP_200_OK, r.text
    assert r.json()["forma_pagamento_entrada"]["nome"].upper() == "DINHEIRO"


def test_zerar_o_adiantamento_limpa_a_forma(client, db_session):
    """
    Sem isto sobraria "pago em PIX" sem valor algum por tras — e a tela
    anunciaria uma forma de pagamento para um adiantamento que nao existe mais.
    """
    header = _autenticar_e_criar_empresa(client)
    cliente_id = _criar_cliente(client, header)
    pix_id = _id_forma_pagamento(client, header, "PIX")

    criada = _post_os(
        client, header, cliente_id,
        valor_entrada=20000,
        forma_pagamento_entrada_id=pix_id,
    )
    numero_os = criada.json()["numero_os"]

    r = client.put(
        f"/api/v1/ordens-servico/{numero_os}",
        json={"valor_entrada": 0},
        headers=header,
    )

    assert r.status_code == status.HTTP_200_OK, r.text
    corpo = r.json()
    assert corpo["valor_entrada"] == 0
    assert corpo["forma_pagamento_entrada"] is None
