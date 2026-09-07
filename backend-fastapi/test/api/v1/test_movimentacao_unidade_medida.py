# ---------------------------------------------------------------------------
# ARQUIVO: test/api/v1/test_movimentacao_unidade_medida.py
# DESCRICAO: A movimentacao devolve a unidade do produto.
#
# POR QUE ESTE ARQUIVO EXISTE. As telas de estoque escreviam " un" na mao, em
# quatro lugares, ignorando o `unidade_medida` que o produto ja traz do
# cadastro. Nao era so rotulo errado: a quantidade e FRACIONADA no banco
# (Float), entao uma sacola comprada por peso aparecia como "2,5 un" -- que se
# le como duas sacolas e meia, sendo 2,5 kg, que podem ser 200 sacolas. No
# painel de transacoes, que e onde se audita quantidade, isso e erro de leitura.
#
# A unidade e LIDA do produto na consulta, e nao desnormalizada como o
# `produto_nome`: o nome preserva como o produto se chamava na epoca; a unidade
# diz COMO a quantidade daquela linha deve ser lida, entao corrigi-la no
# cadastro tem que corrigir o historico junto.
# ---------------------------------------------------------------------------

from starlette import status

TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"


def _auth(client) -> dict:
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
        "endereco": [{
            "logradouro": "Av. Paulista", "numero": "1000", "bairro": "Bela Vista",
            "cidade": "São Paulo", "estado": "SP", "cep": "01310-100",
        }],
    }, headers=header)
    assert r.status_code == 201, r.text
    return header


def _produto(client, header, codigo, unidade, quantidade=0) -> int:
    payload = {
        "nome": f"Produto {codigo}",
        "codigo_produto": codigo,
        "estoque": {"valor_varejo": 3000, "valor_entrada": 3000, "quantidade": quantidade},
    }
    if unidade is not None:
        payload["unidade_medida"] = unidade

    r = client.post("/api/v1/produtos/", json=payload, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _movimentacoes(client, header, produto_id) -> list:
    r = client.get(
        "/api/v1/produtos/movimentacoes",
        params={"produto_id": produto_id},
        headers=header,
    )
    assert r.status_code == status.HTTP_200_OK, r.text
    return r.json()


def test_movimentacao_devolve_a_unidade_do_produto(client, db_session):
    """Sacola comprada por peso: o painel precisa poder escrever 'kg'."""
    header = _auth(client)
    produto_id = _produto(client, header, "SACOLA-KG", unidade="KG", quantidade=5)

    movs = _movimentacoes(client, header, produto_id)

    assert movs, "o cadastro com quantidade inicial gera a ENTRADA no livro"
    assert movs[0]["unidade_medida"] == "KG"


def test_produto_em_unidade_segue_como_sempre(client, db_session):
    """Informatica e oficina cadastram em UN — nada muda para elas."""
    header = _auth(client)
    produto_id = _produto(client, header, "PECA-UN", unidade="UN", quantidade=3)

    movs = _movimentacoes(client, header, produto_id)

    assert movs[0]["unidade_medida"] == "UN"


def test_produto_sem_unidade_nao_quebra(client, db_session):
    """
    `unidade_medida` e opcional no cadastro. Sem ela a resposta traz None e a
    tela cai em "un" -- o comportamento que ja existia.
    """
    header = _auth(client)
    produto_id = _produto(client, header, "SEM-UNIDADE", unidade=None, quantidade=2)

    movs = _movimentacoes(client, header, produto_id)

    assert movs[0]["unidade_medida"] is None


def test_quantidade_fracionada_sobrevive_na_resposta(client, db_session):
    """
    O motivo de tudo isto: 2,5 e um valor legitimo para quem vende por peso.
    Se a quantidade voltasse arredondada, nem o rotulo certo salvaria a leitura.
    """
    header = _auth(client)
    produto_id = _produto(client, header, "SACOLA-FRAC", unidade="KG", quantidade=0)

    r = client.post(
        f"/api/v1/produtos/{produto_id}/movimentacoes",
        json={"tipo": "ENTRADA", "quantidade": 2.5, "custo_unitario": 3000},
        headers=header,
    )
    assert r.status_code == status.HTTP_201_CREATED, r.text

    movs = _movimentacoes(client, header, produto_id)
    entrada = movs[0]

    assert entrada["quantidade"] == 2.5
    assert entrada["quantidade_posterior"] == 2.5
    assert entrada["unidade_medida"] == "KG"
