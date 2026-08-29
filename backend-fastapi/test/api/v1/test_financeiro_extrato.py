# ---------------------------------------------------------------------------
# Testes do Extrato — o livro do dinheiro linha a linha.
#
# O teste que mais importa é o do ESTORNO APARECENDO DUAS VEZES: o extrato tem
# que mostrar o pagamento errado E o estorno que o desfez, lado a lado. Um
# extrato que "limpa" o erro não serve para auditoria nenhuma — e a tabela por
# baixo só recebe INSERT justamente para isso.
# ---------------------------------------------------------------------------

from datetime import date, timedelta

from starlette import status

TEST_USER_EMAIL = "extrato.dono@example.com"
TEST_USER_PASSWORD = "senhaSegura789"


# ===========================================================================
# HELPERS
# ===========================================================================

def _auth(client):
    client.post("/api/v1/usuarios/", json={
        "nome": "Dono do Extrato", "email": TEST_USER_EMAIL, "senha": TEST_USER_PASSWORD,
    })
    login = client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": "hwid-extrato",
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post("/api/v1/empresas/", json={
        "razao_social": "Extrato LTDA", "nome_fantasia": "Extrato", "is_cnpj": True,
        "documento": "12345678000188", "regime_tributario": "Simples Nacional",
        "celular": "11999997777", "segmento": "assistencia_tecnica",
        "endereco": [{"logradouro": "Av. Brasil", "numero": "500", "bairro": "Centro",
                      "cidade": "São Paulo", "estado": "SP", "cep": "01310-100"}],
    }, headers=header)
    return header


def _conta_paga(client, header, valor=8000, descricao="Internet"):
    conta = client.post("/api/v1/financeiro/contas-pagar", json={
        "descricao": descricao, "valor": valor,
        "vencimento": date.today().isoformat(),
    }, headers=header).json()
    client.post(f"/api/v1/financeiro/contas-pagar/{conta['id']}/pagar",
                json={}, headers=header)
    return conta


def _extrato(client, header, **params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    r = client.get(f"/api/v1/financeiro/extrato?{query}", headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    return r.json()


# ===========================================================================
# O QUE APARECE
# ===========================================================================

def test_pagamento_aparece_como_saida_com_quem_fez(client, db_session):
    header = _auth(client)
    _conta_paga(client, header, valor=8000, descricao="Aluguel")

    dados = _extrato(client, header)

    assert dados["total_itens"] == 1
    linha = dados["itens"][0]
    assert linha["tipo"] == "SAIDA"
    assert linha["origem"] == "DESPESA"
    assert linha["valor"] == 8000
    assert "Aluguel" in (linha["motivo"] or "")
    # Sem o nome, o extrato responde "saiu dinheiro" e não "quem tirou".
    assert linha["funcionario_nome"]


def test_estorno_aparece_ao_lado_do_erro_e_nao_no_lugar_dele(client, db_session):
    """O extrato conta a história inteira, inclusive a parte constrangedora.

    A tabela por baixo só recebe INSERT: desfazer um pagamento cria a linha
    contrária. Se um dia este teste falhar, o extrato passou a esconder erro —
    e some junto com ele a razão de a tela existir.
    """
    header = _auth(client)
    conta = _conta_paga(client, header, valor=30000, descricao="Energia Solar")
    client.post(f"/api/v1/financeiro/contas-pagar/{conta['id']}/estornar",
                json={"motivo": "Pagamento nao autorizado"}, headers=header)

    dados = _extrato(client, header)

    assert dados["total_itens"] == 2
    # Mais recente primeiro: o estorno encabeça.
    assert dados["itens"][0]["tipo"] == "ENTRADA"
    assert "Pagamento nao autorizado" in dados["itens"][0]["motivo"]
    assert dados["itens"][1]["tipo"] == "SAIDA"

    # E os totais mostram que o dinheiro voltou, sem apagar que ele saiu.
    assert dados["total_saidas"] == 30000
    assert dados["total_entradas"] == 30000
    assert dados["saldo"] == 0


def test_recebimento_aparece_como_entrada(client, db_session):
    header = _auth(client)
    conta = client.post("/api/v1/financeiro/contas-receber", json={
        "descricao": "Fiado do Joao", "valor": 5000,
        "vencimento": date.today().isoformat(),
    }, headers=header).json()
    client.post(f"/api/v1/financeiro/contas-receber/{conta['id']}/receber",
                json={}, headers=header)

    linha = _extrato(client, header)["itens"][0]
    assert linha["tipo"] == "ENTRADA"
    assert linha["origem"] == "RECEBIMENTO"
    assert linha["valor"] == 5000


# ===========================================================================
# FILTROS — a lista e o rodapé têm que concordar
# ===========================================================================

def test_filtro_de_tipo_move_a_lista_e_os_totais_juntos(client, db_session):
    """Rodapé que não fecha com a lista destrói a confiança na tela inteira."""
    header = _auth(client)
    conta = _conta_paga(client, header, valor=10000)
    client.post(f"/api/v1/financeiro/contas-pagar/{conta['id']}/estornar",
                json={"motivo": "engano"}, headers=header)

    saidas = _extrato(client, header, tipo="SAIDA")
    assert saidas["total_itens"] == 1
    assert saidas["total_saidas"] == 10000
    assert saidas["total_entradas"] == 0, "o filtro vale para o rodapé também"

    entradas = _extrato(client, header, tipo="ENTRADA")
    assert entradas["total_itens"] == 1
    assert entradas["total_entradas"] == 10000


def test_filtro_de_origem(client, db_session):
    header = _auth(client)
    _conta_paga(client, header, valor=7000)

    assert _extrato(client, header, origem="DESPESA")["total_itens"] == 1
    assert _extrato(client, header, origem="VENDA")["total_itens"] == 0


def test_periodo_filtra_pelo_dia_do_movimento(client, db_session):
    """No extrato não existe vencimento: o que conta é quando o dinheiro andou.

    Uma conta com vencimento antigo, paga hoje, aparece HOJE — foi hoje que o
    dinheiro saiu.
    """
    header = _auth(client)
    conta = client.post("/api/v1/financeiro/contas-pagar", json={
        "descricao": "Boleto atrasado", "valor": 12000,
        "vencimento": (date.today() - timedelta(days=40)).isoformat(),
    }, headers=header).json()
    client.post(f"/api/v1/financeiro/contas-pagar/{conta['id']}/pagar",
                json={}, headers=header)

    hoje = date.today().isoformat()
    assert _extrato(client, header, inicio=hoje, fim=hoje)["total_itens"] == 1

    ontem = (date.today() - timedelta(days=1)).isoformat()
    assert _extrato(client, header, inicio=ontem, fim=ontem)["total_itens"] == 0
