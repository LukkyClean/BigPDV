# ---------------------------------------------------------------------------
# ARQUIVO: test_os_busca_por_identificador.py
# DESCRICAO: Cobre a busca de objeto pela placa / n de serie / codigo da arte
#            usada no seletor de cliente da OS.
#
#            O comportamento que mais importa aqui e o PEDACO: quem esta no
#            balcao lembra o final da placa, nao a placa inteira. Se um dia
#            alguem "arrumar" esta rota fazendo-a cobrar
#            `identificador_pesquisavel`, o teste do pedaco quebra -- e e para
#            quebrar mesmo: aquela funcao exige a placa inteira (regex ancorado)
#            porque decide dedup, nao busca.
# ---------------------------------------------------------------------------

from starlette import status

from app.db.models.cliente import Cliente as ClienteModel

TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"

ROTA_BUSCA = "/api/v1/ordens-servico/objeto/buscar"


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
        "documento": "12345678000199",
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
              marca: str = "Dell", modelo: str = "Inspiron",
              cor: str | None = None, dados_adicionais: dict | None = None) -> dict:
    objeto = {
        "marca": marca,
        "modelo": modelo,
        "numero_serie": numero_serie,
        "dados_adicionais": dados_adicionais or {},
    }
    if cor is not None:
        objeto["cor"] = cor

    r = client.post("/api/v1/ordens-servico/", json={
        "cliente_id": cliente_id,
        "prioridade": "NORMAL",
        "defeito_relatado": "Nao liga",
        "dados_adicionais": {},
        "objeto": objeto,
        "itens": [],
    }, headers=header)
    assert r.status_code == status.HTTP_201_CREATED, r.text
    return r.json()


def _buscar(client, header: dict, termo: str) -> list[dict]:
    r = client.get(ROTA_BUSCA, params={"termo": termo}, headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    return r.json()


# =========================
# O QUE TEM QUE ACHAR
# =========================

def test_acha_pela_placa_inteira(client, db_session):
    header = _autenticar_e_criar_empresa(client, "oficina_mecanica")
    ana = _criar_cliente(client, header, "Ana Souza", "98765432101")
    _criar_os(client, header, ana, "ABC1D23", marca="Fiat", modelo="Uno")

    achados = _buscar(client, header, "ABC1D23")
    assert len(achados) == 1
    assert achados[0]["cliente_id"] == ana
    assert achados[0]["cliente_nome"] == "Ana Souza"
    assert achados[0]["numero_serie"] == "ABC1D23"


def test_acha_por_pedaco_da_placa(client, db_session):
    """O caso do balcao: o atendente lembra o final da placa.

    Cobrar `identificador_pesquisavel` aqui recusaria '1D23', porque o regex da
    oficina e ancorado -- e a busca morreria justo no segmento que mais precisa.
    """
    header = _autenticar_e_criar_empresa(client, "oficina_mecanica")
    ana = _criar_cliente(client, header, "Ana Souza", "98765432101")
    _criar_os(client, header, ana, "ABC1D23", marca="Fiat", modelo="Uno")

    achados = _buscar(client, header, "1D23")
    assert len(achados) == 1
    assert achados[0]["cliente_id"] == ana


def test_acha_pelas_tres_primeiras_letras_da_placa(client, db_session):
    """E assim que se comeca a digitar uma placa.

    O piso da BUSCA e 3, nao os 4 do registry: la o numero decide se o texto
    identifica um bem (dedup), aqui decide se vale consultar o banco.
    """
    header = _autenticar_e_criar_empresa(client, "oficina_mecanica")
    ana = _criar_cliente(client, header, "Ana Souza", "98765432101")
    _criar_os(client, header, ana, "ABC2152", marca="Fiat", modelo="Toro")

    achados = _buscar(client, header, "ABC")
    assert len(achados) == 1
    assert achados[0]["numero_serie"] == "ABC2152"


def test_acha_ignorando_hifen_e_caixa(client, db_session):
    header = _autenticar_e_criar_empresa(client, "oficina_mecanica")
    ana = _criar_cliente(client, header, "Ana Souza", "98765432101")
    _criar_os(client, header, ana, "ABC1D23", marca="Fiat", modelo="Uno")

    assert len(_buscar(client, header, "abc-1d23")) == 1
    assert len(_buscar(client, header, "abc 1d23")) == 1


def test_acha_por_pedaco_do_numero_de_serie(client, db_session):
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    ana = _criar_cliente(client, header, "Ana Souza", "98765432101")
    _criar_os(client, header, ana, "C02X1234JGH5", marca="Apple", modelo="MacBook")

    achados = _buscar(client, header, "1234JGH5")
    assert len(achados) == 1
    assert achados[0]["marca"] == "Apple"


def test_devolve_o_objeto_inteiro_para_a_os_abrir_preenchida(client, db_session):
    """Quem clica na linha ja disse qual e o bem: o form nao pode ter que
    perguntar de novo."""
    header = _autenticar_e_criar_empresa(client, "oficina_mecanica")
    ana = _criar_cliente(client, header, "Ana Souza", "98765432101")
    _criar_os(client, header, ana, "ABC1D23", marca="Fiat", modelo="Uno",
              cor="Prata", dados_adicionais={"ano": "2015"})

    achado = _buscar(client, header, "ABC1D23")[0]
    assert achado["marca"] == "Fiat"
    assert achado["modelo"] == "Uno"
    assert achado["cor"] == "Prata"
    assert achado["dados_adicionais"].get("ano") == "2015"
    assert achado["tipo_equipamento"]
    assert achado["objeto_id"] > 0


def test_bem_vendido_devolve_os_dois_donos(client, db_session):
    """Mesma placa em dois clientes: a lista mostra os dois, com nome, para o
    atendente escolher. Esconder um seria pior que mostrar."""
    header = _autenticar_e_criar_empresa(client, "oficina_mecanica")
    ana = _criar_cliente(client, header, "Ana Souza", "98765432101")
    bruno = _criar_cliente(client, header, "Bruno Lima", "11122233396")

    _criar_os(client, header, ana, "ABC1D23", marca="Fiat", modelo="Uno")
    _criar_os(client, header, bruno, "ABC1D23", marca="Fiat", modelo="Uno")

    achados = _buscar(client, header, "ABC1D23")
    assert len(achados) == 2
    assert {a["cliente_id"] for a in achados} == {ana, bruno}
    assert {a["cliente_nome"] for a in achados} == {"Ana Souza", "Bruno Lima"}


# =========================
# O QUE NAO PODE ACHAR
# =========================

def test_termo_generico_nao_devolve_nada(client, db_session):
    """'S/N' e 'nao sei' sao o que se digita SEM ter o dado -- se casassem,
    a busca devolveria meia loja."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    ana = _criar_cliente(client, header, "Ana Souza", "98765432101")
    bruno = _criar_cliente(client, header, "Bruno Lima", "11122233396")
    _criar_os(client, header, ana, "S/N")
    _criar_os(client, header, bruno, "nao sei")

    assert _buscar(client, header, "S/N") == []
    assert _buscar(client, header, "s / n") == []
    assert _buscar(client, header, "nao sei") == []
    assert _buscar(client, header, "desconhecido") == []


def test_termo_curto_nao_varre_a_loja(client, db_session):
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    ana = _criar_cliente(client, header, "Ana Souza", "98765432101")
    _criar_os(client, header, ana, "AB123456")

    assert _buscar(client, header, "AB") == []
    assert _buscar(client, header, "1") == []


def test_cliente_inativo_fica_de_fora(client, db_session):
    """Nao adianta oferecer no seletor um dono que nao da mais para selecionar."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    ana = _criar_cliente(client, header, "Ana Souza", "98765432101")
    _criar_os(client, header, ana, "C02X1234JGH5")

    assert len(_buscar(client, header, "C02X1234JGH5")) == 1

    cliente = db_session.get(ClienteModel, ana)
    cliente.ativo = False
    db_session.commit()

    assert _buscar(client, header, "C02X1234JGH5") == []


def test_identificador_inexistente_devolve_lista_vazia(client, db_session):
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    _criar_cliente(client, header, "Ana Souza", "98765432101")

    assert _buscar(client, header, "SERIALQUENAOEXISTE") == []
