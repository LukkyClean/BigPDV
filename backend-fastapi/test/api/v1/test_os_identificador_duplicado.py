# ---------------------------------------------------------------------------
# ARQUIVO: test_os_identificador_duplicado.py
# DESCRICAO: Cobre o aviso de identificador (placa / n de serie) ja cadastrado.
#
#            Tres comportamentos, nesta ordem de importancia:
#              1. identificador generico ("S/N", "nao sei") NAO serve de chave --
#                 nem para avisar, nem para reaproveitar objeto;
#              2. identificador real de OUTRO cliente gera aviso (nunca bloqueio);
#              3. o aviso some assim que o proprio cliente passa a ter o objeto,
#                 que e o que faz ele aparecer so na primeira OS apos a venda.
#
#            Inclui teste GUARDIAO: o reaproveitamento de objeto por serial de
#            verdade (comportamento antigo, em producao) segue intacto.
# ---------------------------------------------------------------------------

from starlette import status

from app.core.segmentos import (
    identificador_pesquisavel,
    SEGMENTO_OFICINA,
    SEGMENTO_ASSISTENCIA,
)

TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"

ROTA_CHECK = "/api/v1/ordens-servico/objeto/verificar-identificador"


# =========================
# Helpers de setup
# =========================

def _autenticar_e_criar_empresa(client, segmento: str) -> dict:
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


def _criar_cliente(client, header: dict, nome: str, cpf: str) -> int:
    r = client.post("/api/v1/clientes/cliente_pf", json={
        "nome": nome,
        "cpf": cpf,
        "tipo": "PF",
        "celular": "11987654321",
        "endereco": [{
            "logradouro": "Rua das Flores", "numero": "100", "bairro": "Centro",
            "cidade": "Campinas", "estado": "SP", "cep": "13010-000",
        }],
    }, headers=header)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _criar_os(client, header: dict, cliente_id: int, numero_serie: str,
              marca: str = "Dell", modelo: str = "Inspiron") -> dict:
    r = client.post("/api/v1/ordens-servico/", json={
        "cliente_id": cliente_id,
        "prioridade": "NORMAL",
        "defeito_relatado": "Nao liga",
        "dados_adicionais": {},
        "objeto": {
            "marca": marca,
            "modelo": modelo,
            "numero_serie": numero_serie,
            "dados_adicionais": {},
        },
        "itens": [],
    }, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    return r.json()


def _check(client, header: dict, identificador: str, cliente_id: int | None = None) -> dict:
    params = {"identificador": identificador}
    if cliente_id is not None:
        params["cliente_id"] = cliente_id
    r = client.get(ROTA_CHECK, params=params, headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    return r.json()


# =========================
# A REGRA (unitario, sem banco)
# =========================

def test_identificador_generico_nao_e_pesquisavel():
    """O que o atendente digita quando nao tem o dado nao identifica bem nenhum."""
    for valor in ["S/N", "s / n", "SN", "sn", "  s/n  ", "sem numero", "sem número",
                  "nao sei", "não sei", "NAO TEM", "nenhum", "desconhecido", "teste"]:
        assert identificador_pesquisavel(valor) is False, valor


def test_identificador_vazio_curto_ou_repetido_nao_e_pesquisavel():
    for valor in [None, "", "   ", "AB", "123", "----", "0000", "XXXX", "....."]:
        assert identificador_pesquisavel(valor) is False, valor


def test_serial_real_e_pesquisavel_em_segmento_sem_regex():
    """Informatica aceita qualquer formato: o filtro e so contra placeholder."""
    for valor in ["C02X1234JGH5", "SN123456789", "ABC-1234-XY", "5CD9284QK7"]:
        assert identificador_pesquisavel(valor, SEGMENTO_ASSISTENCIA) is True, valor


def test_oficina_so_considera_pesquisavel_o_que_e_placa():
    """Na oficina o identificador e a placa: serial de notebook nao e placa."""
    assert identificador_pesquisavel("ABC1D23", SEGMENTO_OFICINA) is True
    assert identificador_pesquisavel("abc-1d23", SEGMENTO_OFICINA) is True
    assert identificador_pesquisavel("ABC1234", SEGMENTO_OFICINA) is True
    assert identificador_pesquisavel("C02X1234JGH5", SEGMENTO_OFICINA) is False
    assert identificador_pesquisavel("S/N", SEGMENTO_OFICINA) is False


# =========================
# O AVISO (integracao)
# =========================

def test_identificador_generico_nao_gera_conflito(client, db_session):
    """Dois clientes com 'S/N' nao podem virar aviso de duplicidade."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    ana = _criar_cliente(client, header, "Ana Souza", "98765432100")
    bruno = _criar_cliente(client, header, "Bruno Lima", "11122233396")

    _criar_os(client, header, ana, "S/N")

    body = _check(client, header, "S/N", cliente_id=bruno)
    assert body["pesquisavel"] is False
    assert body["conflitos"] == []


def test_serial_de_outro_cliente_gera_aviso_com_dono_e_ultima_os(client, db_session):
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    ana = _criar_cliente(client, header, "Ana Souza", "98765432100")
    bruno = _criar_cliente(client, header, "Bruno Lima", "11122233396")

    os_ana = _criar_os(client, header, ana, "C02X1234JGH5", marca="Apple", modelo="MacBook")

    body = _check(client, header, "C02X1234JGH5", cliente_id=bruno)
    assert body["pesquisavel"] is True
    assert len(body["conflitos"]) == 1

    conflito = body["conflitos"][0]
    assert conflito["cliente_id"] == ana
    assert conflito["cliente_nome"] == "Ana Souza"
    assert conflito["marca"] == "Apple"
    assert conflito["modelo"] == "MacBook"
    assert conflito["ultima_os_numero"] == os_ana["numero_os"]
    assert conflito["ultima_os_data"] is not None


def test_aviso_ignora_diferenca_de_formatacao(client, db_session):
    """Placa gravada como o usuario digitou: 'abc-1d23' tem que achar 'ABC1D23'."""
    header = _autenticar_e_criar_empresa(client, "oficina_mecanica")
    ana = _criar_cliente(client, header, "Ana Souza", "98765432100")
    bruno = _criar_cliente(client, header, "Bruno Lima", "11122233396")

    _criar_os(client, header, ana, "ABC1D23", marca="Fiat", modelo="Uno")

    body = _check(client, header, "abc-1d23", cliente_id=bruno)
    assert body["pesquisavel"] is True
    assert len(body["conflitos"]) == 1
    assert body["conflitos"][0]["cliente_id"] == ana


def test_identificador_inedito_nao_gera_aviso(client, db_session):
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    ana = _criar_cliente(client, header, "Ana Souza", "98765432100")

    body = _check(client, header, "SERIALNOVO123", cliente_id=ana)
    assert body["pesquisavel"] is True
    assert body["conflitos"] == []


def test_dono_atual_nao_recebe_aviso_do_proprio_objeto(client, db_session):
    """Cliente voltando com o mesmo bem e reuso normal, nao duplicidade."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    ana = _criar_cliente(client, header, "Ana Souza", "98765432100")

    _criar_os(client, header, ana, "C02X1234JGH5")

    body = _check(client, header, "C02X1234JGH5", cliente_id=ana)
    assert body["conflitos"] == []


def test_aviso_some_depois_que_o_novo_dono_tem_o_objeto(client, db_session):
    """
    O comportamento que o usuario pediu: avisa na primeira vez, nao em toda OS.

    Nao ha flag de "ja avisei" -- o aviso some sozinho porque, apos seguir com a
    OS, o novo dono passa a ter um objeto proprio com aquele identificador.
    """
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    ana = _criar_cliente(client, header, "Ana Souza", "98765432100")
    bruno = _criar_cliente(client, header, "Bruno Lima", "11122233396")

    _criar_os(client, header, ana, "C02X1234JGH5")

    # 1a OS do Bruno com a maquina comprada da Ana: avisa.
    assert len(_check(client, header, "C02X1234JGH5", cliente_id=bruno)["conflitos"]) == 1

    # Ele segue assim mesmo -- vira registro proprio, sem tocar no da Ana.
    _criar_os(client, header, bruno, "C02X1234JGH5")

    # 2a OS do Bruno: silencio.
    assert _check(client, header, "C02X1234JGH5", cliente_id=bruno)["conflitos"] == []

    # E a Ana continua dona do objeto dela, com o historico intacto.
    assert _check(client, header, "C02X1234JGH5", cliente_id=ana)["conflitos"] == []


def test_sem_cliente_selecionado_lista_todos_os_donos(client, db_session):
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    ana = _criar_cliente(client, header, "Ana Souza", "98765432100")

    _criar_os(client, header, ana, "C02X1234JGH5")

    body = _check(client, header, "C02X1234JGH5")
    assert len(body["conflitos"]) == 1
    assert body["conflitos"][0]["cliente_id"] == ana


# =========================
# DEDUP DO OBJETO
# =========================

def test_dois_bens_com_sn_do_mesmo_cliente_nao_colapsam(client, db_session):
    """
    Regressao: 'S/N' == 'S/N' fazia o segundo aparelho reusar o objeto do
    primeiro e sobrescrever marca/modelo. Cada um tem que virar seu proprio
    registro, senao o cliente perde o cadastro do primeiro aparelho.
    """
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    ana = _criar_cliente(client, header, "Ana Souza", "98765432100")

    os1 = _criar_os(client, header, ana, "S/N", marca="Dell", modelo="Inspiron")
    os2 = _criar_os(client, header, ana, "S/N", marca="Acer", modelo="Aspire")

    assert os1["objeto"]["id"] != os2["objeto"]["id"]

    # O primeiro objeto continua sendo o Dell.
    r = client.get(f"/api/v1/ordens-servico/{os1['numero_os']}", headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    assert r.json()["objeto"]["marca"] == "Dell"
    assert r.json()["objeto"]["modelo"] == "Inspiron"


def test_serial_real_do_mesmo_cliente_continua_reusando_o_objeto(client, db_session):
    """
    GUARDIAO: o reaproveitamento por identificador de verdade e o comportamento
    que ja roda em producao (um bem fisico = um registro que acumula historico).
    A correcao do 'S/N' nao pode ter desligado isso.
    """
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    ana = _criar_cliente(client, header, "Ana Souza", "98765432100")

    os1 = _criar_os(client, header, ana, "C02X1234JGH5", marca="Apple", modelo="MacBook")
    os2 = _criar_os(client, header, ana, "C02X1234JGH5", marca="Apple", modelo="MacBook")

    assert os1["objeto"]["id"] == os2["objeto"]["id"]
