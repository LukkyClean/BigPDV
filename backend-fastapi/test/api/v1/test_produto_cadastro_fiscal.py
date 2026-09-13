# ---------------------------------------------------------------------------
# ARQUIVO: test_produto_cadastro_fiscal.py
# DESCRIÇÃO: O produto nasce com os dados fiscais, numa transação só.
#
# Antes deste comportamento o lojista cadastrava o produto, fechava, procurava
# na lista, reabria em edição e só então preenchia NCM/CFOP/CST — e entre os
# dois passos o produto entrava na lista de pendências do Centro Fiscal.
# Ver `docs/cadastro-produto-plano.md`, §2.A1.
# ---------------------------------------------------------------------------

import pytest
from fastapi.testclient import TestClient
from starlette import status

from app.db.models.empresa import Empresa
from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings

TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"
TEST_HWID = "test-terminal-hwid"


# =========================
# Fixtures
# =========================

@pytest.fixture(scope="function")
def header_with_token(client: TestClient, db_session, create_test_empresa) -> dict:
    """Autentica o usuário de teste e devolve o header Authorization."""
    login_data = {
        "username": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
        "hwid": TEST_HWID,
    }
    response = client.post("/api/v1/auth/login", data=login_data)
    if response.status_code != 200:
        pytest.skip("Falha na autenticação do usuário de teste.")
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def licenca_com_nfe(monkeypatch):
    """
    Concede o módulo NFE na licença.

    Sem isto o gate nega — e nega certo: NFE está em
    `MODULOS_NEGADOS_SEM_RESPOSTA`, onde "não sei" significa NÃO, porque
    liberar por engano deixaria uma loja emitir documento fiscal em nome dela
    na SEFAZ. A concessão real vem no JWT assinado pela plataforma.
    """
    from app.core import modulos as modulos_mod

    monkeypatch.setattr(
        modulos_mod.licenca_service, "modulos_da_licenca", lambda db: ["NFE"]
    )


@pytest.fixture
def modulo_fiscal_configurado(db_session, header_with_token, licenca_com_nfe):
    """
    Liga o módulo fiscal desta empresa.

    É a segunda pergunta do `requer_modulo_fiscal`: a licença responde pela
    primeira (fixture acima), e a existência de `EmpresaFiscalSettings`
    responde por esta.
    """
    empresa = db_session.query(Empresa).first()
    db_session.add(EmpresaFiscalSettings(
        empresa_id=empresa.id,
        serie_nfe=1,
        ultimo_numero_nfe=0,
        ambiente_emissao=2,
    ))
    db_session.commit()
    return empresa


def _payload(codigo: str, fiscal: dict | None = None) -> dict:
    """Produto mínimo válido, com ou sem o bloco fiscal."""
    corpo = {
        "nome": "Caneta Esferográfica Azul",
        "codigo_produto": codigo,
        "unidade_medida": "UN",
        "estoque": {"valor_varejo": 100, "quantidade": 10, "valor_entrada": 50},
    }
    if fiscal is not None:
        corpo["fiscal"] = fiscal
    return corpo


FISCAL_OK = {
    "ncm": "96081000",
    "cfop_padrao": "5102",
    "origem_mercadoria": 0,
    "csosn": "102",
    "unidade_tributavel": "UN",
}


# =========================
# O caminho novo
# =========================

def test_cadastro_ja_grava_os_dados_fiscais(
    client: TestClient, header_with_token, modulo_fiscal_configurado
):
    """Um POST só: o produto nasce pronto para emitir nota."""
    resposta = client.post(
        "/api/v1/produtos/", json=_payload("CAN-FISC-01", FISCAL_OK), headers=header_with_token
    )
    assert resposta.status_code == status.HTTP_201_CREATED, resposta.text
    produto_id = resposta.json()["id"]

    fiscal = client.get(f"/api/v1/produtos/{produto_id}/fiscal", headers=header_with_token)
    assert fiscal.status_code == status.HTTP_200_OK, fiscal.text
    corpo = fiscal.json()
    assert corpo["ncm"] == "96081000"
    assert corpo["cfop_padrao"] == "5102"
    assert corpo["csosn"] == "102"
    assert corpo["origem_mercadoria"] == 0


def test_fiscal_invalido_nao_deixa_o_produto_nascer(
    client: TestClient, header_with_token, modulo_fiscal_configurado
):
    """
    A transação é uma só — é o motivo de o bloco fiscal viajar junto do POST.

    Com duas chamadas (criar produto, depois salvar fiscal) o NCM torto deixava
    para trás um produto criado e sem dados fiscais, que é exatamente o estado
    que este cadastro veio consertar.
    """
    resposta = client.post(
        "/api/v1/produtos/",
        json=_payload("CAN-FISC-02", {**FISCAL_OK, "ncm": "123"}),
        headers=header_with_token,
    )
    assert resposta.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, resposta.text

    # E o produto não ficou no banco.
    busca = client.get(
        "/api/v1/produtos/", params={"buscar": "CAN-FISC-02"}, headers=header_with_token
    )
    assert busca.status_code == status.HTTP_200_OK
    assert [p for p in busca.json() if p["codigo_produto"] == "CAN-FISC-02"] == []


# =========================
# Não regredir quem não emite nota
# =========================

def test_cadastro_sem_bloco_fiscal_continua_igual(client: TestClient, header_with_token):
    """
    Três segmentos rodam em loja real e nenhum emite nota: o cadastro sem
    `fiscal` não pode exigir módulo, configuração, nem campo novo.
    """
    resposta = client.post(
        "/api/v1/produtos/", json=_payload("CAN-SEM-FISC"), headers=header_with_token
    )
    assert resposta.status_code == status.HTTP_201_CREATED, resposta.text
    assert resposta.json()["codigo_produto"] == "CAN-SEM-FISC"


def test_produto_sem_dados_fiscais_responde_404_e_nao_500(
    client: TestClient, header_with_token, modulo_fiscal_configurado
):
    """
    `HTTPException` era usada no endpoint sem estar importada: o 404 de "ainda
    não preenchido" virava NameError, e o cliente recebia 500. A tela engolia
    em silêncio porque o `getProdutoFiscal` fica dentro de um try/catch.
    """
    criado = client.post(
        "/api/v1/produtos/", json=_payload("CAN-FISC-03"), headers=header_with_token
    )
    assert criado.status_code == status.HTTP_201_CREATED, criado.text

    fiscal = client.get(
        f"/api/v1/produtos/{criado.json()['id']}/fiscal", headers=header_with_token
    )
    assert fiscal.status_code == status.HTTP_404_NOT_FOUND, fiscal.text


def test_bloco_fiscal_sem_modulo_configurado_e_recusado(
    client: TestClient, header_with_token, licenca_com_nfe
):
    """
    Mandar `fiscal` passa pela mesma porta do PUT /{id}/fiscal.

    Aqui a licença LIBERA a NF-e e a empresa ainda não configurou — que é o
    estado normal de quem acabou de contratar. Resposta: 403 e nenhum produto
    criado, para o cadastro não nascer pela metade.
    """
    resposta = client.post(
        "/api/v1/produtos/", json=_payload("CAN-FISC-04", FISCAL_OK), headers=header_with_token
    )
    assert resposta.status_code == status.HTTP_403_FORBIDDEN, resposta.text

    busca = client.get(
        "/api/v1/produtos/", params={"buscar": "CAN-FISC-04"}, headers=header_with_token
    )
    assert [p for p in busca.json() if p["codigo_produto"] == "CAN-FISC-04"] == []


# =========================
# O SKU que passava na tela e voltava 422
# =========================

def test_sku_de_60_caracteres_e_aceito(client: TestClient, header_with_token):
    """
    A coluna e o Zod aceitam 100; o schema de entrada parava em 50. Um SKU
    longo passava na validação da tela e voltava 422 do servidor.
    """
    codigo = "SKU-" + ("L" * 56)
    assert len(codigo) == 60

    resposta = client.post("/api/v1/produtos/", json=_payload(codigo), headers=header_with_token)
    assert resposta.status_code == status.HTTP_201_CREATED, resposta.text
    assert resposta.json()["codigo_produto"] == codigo


# =========================
# O campo que a tela mostrava e o banco jogava fora
# =========================

def test_localizacao_no_estoque_e_gravada_e_devolvida(client: TestClient, header_with_token):
    """
    Era campo fantasma: existia na tela, no Zod e nos dois payloads, com a
    coluna comentada no model. O lojista digitava a prateleira, salvava com
    sucesso e o dado sumia sem erro nenhum.
    """
    payload = _payload("CAN-LOC-01")
    payload["localizacao_estoque"] = "Corredor A, Prateleira 3"

    criado = client.post("/api/v1/produtos/", json=payload, headers=header_with_token)
    assert criado.status_code == status.HTTP_201_CREATED, criado.text
    assert criado.json()["localizacao_estoque"] == "Corredor A, Prateleira 3"

    # E sobrevive à releitura — não é só eco do payload.
    lido = client.get(f"/api/v1/produtos/{criado.json()['id']}", headers=header_with_token)
    assert lido.status_code == status.HTTP_200_OK, lido.text
    assert lido.json()["localizacao_estoque"] == "Corredor A, Prateleira 3"


def test_localizacao_pode_ser_alterada_na_edicao(client: TestClient, header_with_token):
    """O caminho do update também precisa levar o campo até o banco."""
    criado = client.post(
        "/api/v1/produtos/", json=_payload("CAN-LOC-02"), headers=header_with_token
    )
    produto_id = criado.json()["id"]

    editado = client.put(
        f"/api/v1/produtos/{produto_id}",
        json={"localizacao_estoque": "Depósito, Estante 7"},
        headers=header_with_token,
    )
    assert editado.status_code == status.HTTP_200_OK, editado.text
    assert editado.json()["localizacao_estoque"] == "Depósito, Estante 7"
