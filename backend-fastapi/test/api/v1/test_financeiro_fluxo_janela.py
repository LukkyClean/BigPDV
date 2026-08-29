# ---------------------------------------------------------------------------
# Testes do TETO da janela do Fluxo de Caixa.
#
# Arquivo à parte porque o que se prova aqui é o contrato da rota, não a
# projeção: até onde dá para olhar, e o que acontece um dia além disso.
# ---------------------------------------------------------------------------

from datetime import date, timedelta

from starlette import status

TEST_USER_EMAIL = "janela.dono@example.com"
TEST_USER_PASSWORD = "senhaSegura789"


def _auth(client):
    client.post("/api/v1/usuarios/", json={
        "nome": "Dono da Janela", "email": TEST_USER_EMAIL, "senha": TEST_USER_PASSWORD,
    })
    login = client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": "hwid-janela",
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post("/api/v1/empresas/", json={
        "razao_social": "Janela LTDA", "nome_fantasia": "Janela", "is_cnpj": True,
        "documento": "12345678000188", "regime_tributario": "Simples Nacional",
        "celular": "11999997777", "segmento": "assistencia_tecnica",
        "endereco": [{"logradouro": "Av. Brasil", "numero": "500", "bairro": "Centro",
                      "cidade": "São Paulo", "estado": "SP", "cep": "01310-100"}],
    }, headers=header)
    return header


def test_um_ano_e_o_teto_da_janela(client, db_session):
    """360 dias é a maior janela da tela; 365 é o teto da rota.

    Parcela lançada para daqui a onze meses precisa caber: ela nasce inteira no
    parcelamento, e é justamente o tipo de conta que o horizonte longo existe
    para mostrar.
    """
    header = _auth(client)
    client.post("/api/v1/financeiro/contas-pagar", json={
        "descricao": "Ultima parcela",
        "valor": 50000,
        "vencimento": (date.today() + timedelta(days=330)).isoformat(),
    }, headers=header)

    curto = client.get("/api/v1/financeiro/fluxo-caixa?dias=90", headers=header)
    assert curto.json()["linha"] == [], "fora da janela curta"

    longo = client.get("/api/v1/financeiro/fluxo-caixa?dias=360", headers=header)
    assert longo.status_code == status.HTTP_200_OK, longo.text
    assert len(longo.json()["linha"]) == 1
    assert longo.json()["total_saidas"] == 50000

    assert client.get(
        "/api/v1/financeiro/fluxo-caixa?dias=365", headers=header
    ).status_code == status.HTTP_200_OK


def test_alem_de_um_ano_a_rota_recusa(client, db_session):
    """Sem documento lançado lá na frente, a linha viraria uma reta."""
    header = _auth(client)
    r = client.get("/api/v1/financeiro/fluxo-caixa?dias=366", headers=header)
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
