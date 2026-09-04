# ---------------------------------------------------------------------------
# Testes do fuso nos relatorios: o dia e o da LOJA, nao o dia UTC.
#
# O bug que estes testes fixam: o banco grava `criado_em` em UTC e o filtro
# recebia a data local do frontend sem converter. No Brasil (UTC-3) isso fazia
# toda venda feita depois das 21h cair no relatorio do dia SEGUINTE -- ~3h de
# faturamento saindo do lugar todas as noites.
#
# POR QUE ESTES TESTES SAO DETERMINISTICOS (e os de test_custo_estoque nao eram):
# eles nao dependem da hora em que a suite roda. O fuso e fixado em '-03:00'
# pela STARTBIG_TZ e o `criado_em` da venda e escrito a mao num instante
# escolhido -- 01:30 UTC, que e 22:30 do dia anterior em Sao Paulo. A venda da
# "noite" existe independentemente do relogio da maquina.
# ---------------------------------------------------------------------------

from datetime import date, datetime

import pytest

from app.core.tempo import fim_do_dia_utc, hoje_local, inicio_do_dia_utc, intervalo_utc
from app.db.models.contador_venda import ContadorVenda
from app.db.models.venda import Venda

TEST_USER_EMAIL = "fuso.relatorio@example.com"
TEST_USER_PASSWORD = "senhaSegura456"

# 01:30 UTC de 10/03 == 22:30 de 09/03 em Sao Paulo (UTC-3).
INSTANTE_UTC_DA_VENDA = datetime(2026, 3, 10, 1, 30, 0)
DIA_LOCAL_DA_VENDA = "2026-03-09"
DIA_LOCAL_SEGUINTE = "2026-03-10"


@pytest.fixture(autouse=True)
def _fuso_sao_paulo(monkeypatch):
    """Fixa o fuso da loja em UTC-3 para toda a classe de testes.

    Deslocamento fixo em vez de 'America/Sao_Paulo' de proposito: o Windows nao
    traz o banco de fusos IANA, entao o nome levantaria ZoneInfoNotFoundError na
    maquina de loja e o teste passaria por engano, caindo no fuso do sistema.
    """
    monkeypatch.setenv("STARTBIG_TZ", "-03:00")


def _auth(client):
    client.post("/api/v1/usuarios/", json={
        "nome": "Admin Fuso", "email": TEST_USER_EMAIL, "senha": TEST_USER_PASSWORD,
    })
    login = client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": "test-terminal-hwid",
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post("/api/v1/empresas/", json={
        "razao_social": "Empresa Fuso LTDA", "nome_fantasia": "Fuso", "is_cnpj": True,
        "documento": "12345678000199", "regime_tributario": "Simples Nacional",
        "celular": "11999998888", "segmento": "assistencia_tecnica",
        "endereco": [{"logradouro": "Av. Paulista", "numero": "1000", "bairro": "Bela Vista",
                      "cidade": "São Paulo", "estado": "SP", "cep": "01310-100"}],
    }, headers=header)
    return header


def _funcionario(client, header):
    r = client.post("/api/v1/funcionarios/", json={
        "nome": "Vendedor Fuso", "cpf": "11122233344", "contato": "11999999999",
        "usuario": {"nome": "vendfuso", "email": "vendfuso@empresa.com", "senha": "SenhaForte123!"},
        "endereco": [{"logradouro": "Rua X", "numero": "1", "cep": "12345-678",
                      "bairro": "Centro", "cidade": "Lab City", "estado": "SP"}],
    }, headers=header)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _forma_pagamento(client, header):
    r = client.post("/api/v1/formas-pagamento/", json={"nome": "Dinheiro", "ativo": True}, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _produto(client, header):
    r = client.post("/api/v1/produtos/", json={
        "nome": "Cerveja 600ml", "codigo_produto": "FUSO-001", "unidade_medida": "UN",
        "estoque": {"valor_varejo": 1200, "quantidade": 100},
    }, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _venda_da_noite(client, header, db_session, funcionario_id, produto_id, fp_id):
    """Cria e finaliza uma venda, depois reescreve `criado_em` para o instante
    UTC que corresponde a 22:30 do dia local anterior."""
    if not db_session.query(ContadorVenda).first():
        db_session.add(ContadorVenda(id=1, proximo_numero=1))
        db_session.commit()

    cv = client.post("/api/v1/vendas/", json={"funcionario_id": funcionario_id}, headers=header)
    assert cv.status_code == 201, cv.text
    venda_id = cv.json()["id"]

    add = client.post(f"/api/v1/vendas/{venda_id}/itens", json={
        "tipo_produto": "CADASTRADO", "produto_id": produto_id, "quantidade": 2,
    }, headers=header)
    assert add.status_code == 201, add.text
    total = add.json()["financeiro_atualizado"]["total"]

    fin = client.post(f"/api/v1/vendas/{venda_id}/finalizar", json={
        "pagamentos": [{"forma_pagamento_id": fp_id, "valor": total,
                        "parcelado": False, "qtd_parcelas": None}],
    }, headers=header)
    assert fin.status_code == 200, fin.text

    venda = db_session.query(Venda).filter(Venda.id == venda_id).first()
    venda.criado_em = INSTANTE_UTC_DA_VENDA
    db_session.commit()
    return total


def _faturamento(client, header, dia):
    r = client.get("/api/v1/relatorios/faturamento",
                   params={"inicio": dia, "fim": dia}, headers=header)
    assert r.status_code == 200, r.text
    return r.json()["faturamento_total"]


# ===========================================================================
# O bug de producao
# ===========================================================================

def test_venda_das_22h_conta_no_dia_local_em_que_foi_feita(client, db_session):
    """Venda das 22:30 de 09/03 aparece no faturamento de 09/03.

    Antes da correcao este teste falhava: o filtro comparava a data local crua
    contra um `criado_em` que ja estava em 10/03 UTC, e o faturamento do dia
    vinha zero.
    """
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma_pagamento(client, header)
    produto_id = _produto(client, header)

    total = _venda_da_noite(client, header, db_session, funcionario_id, produto_id, fp_id)

    assert _faturamento(client, header, DIA_LOCAL_DA_VENDA) == total


def test_venda_das_22h_nao_vaza_para_o_dia_seguinte(client, db_session):
    """O espelho do teste acima: a mesma venda NAO pode contar em 10/03.

    Sem a conversao, era exatamente ai que ela reaparecia -- o lojista via o
    faturamento da noite anterior somado ao dia seguinte.
    """
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma_pagamento(client, header)
    produto_id = _produto(client, header)

    _venda_da_noite(client, header, db_session, funcionario_id, produto_id, fp_id)

    assert _faturamento(client, header, DIA_LOCAL_SEGUINTE) == 0


# ===========================================================================
# O helper de conversao, isolado
# ===========================================================================

def test_intervalo_utc_desloca_as_bordas_do_dia():
    inicio, fim = intervalo_utc(date(2026, 3, 9), date(2026, 3, 9))
    # Meia-noite em Sao Paulo e 03:00 UTC.
    assert inicio == datetime(2026, 3, 9, 3, 0, 0)
    assert fim == datetime(2026, 3, 10, 2, 59, 59, 999999)


def test_intervalo_de_varios_dias_cobre_da_primeira_a_ultima_borda():
    inicio, fim = intervalo_utc(date(2026, 3, 1), date(2026, 3, 31))
    assert inicio == datetime(2026, 3, 1, 3, 0, 0)
    assert fim == datetime(2026, 4, 1, 2, 59, 59, 999999)


def test_bordas_do_dia_sao_coerentes_entre_si():
    dia = date(2026, 3, 9)
    assert inicio_do_dia_utc(dia) < fim_do_dia_utc(dia)
    assert inicio_do_dia_utc(dia) == intervalo_utc(dia, dia)[0]


def test_fuso_invalido_nao_derruba_o_relatorio(monkeypatch):
    """Fuso mal configurado cai no fuso do sistema em vez de levantar excecao.

    Relatorio quebrado por variavel de ambiente errada seria pior que relatorio
    com fuso do sistema.
    """
    monkeypatch.setenv("STARTBIG_TZ", "isso-nao-e-um-fuso")
    assert isinstance(hoje_local(), date)
    inicio, fim = intervalo_utc(date(2026, 3, 9), date(2026, 3, 9))
    assert inicio < fim
