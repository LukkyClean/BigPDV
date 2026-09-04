# ---------------------------------------------------------------------------
# ARQUIVO: test/api/v1/test_os_identificador_gerado.py
# DESCRICAO: Identificador GERADO pelo sistema (serigrafia) x identificador
#            PEDIDO ao usuario (informatica, oficina).
#
# POR QUE ESTE ARQUIVO EXISTE. Para a serigrafia poder gerar "ART-0042", o
# campo `numero_serie` deixou de ser obrigatorio no SCHEMA e a exigencia mudou
# de lugar -- foi para o servico, que sabe qual e o segmento.
#
# Isso mexeu em codigo que informatica e oficina usam TODO DIA, e as duas estao
# em producao. O risco concreto: sem a guarda no servico, informatica passaria
# a aceitar OS sem numero de serie nenhum, em silencio. Os testes abaixo sao a
# prova de que nao passa.
# ---------------------------------------------------------------------------

from starlette import status

from app.core.segmentos import gerar_identificador, identificador_e_gerado

TEST_USER_EMAIL = "teste.funcionario@example.com"
TEST_USER_PASSWORD = "senhaSegura456"


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


def _criar_cliente(client, header: dict, nome: str = "Claudinha", cpf: str = "52998224725") -> int:
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


def _post_os(client, header: dict, cliente_id: int, objeto: dict):
    return client.post("/api/v1/ordens-servico/", json={
        "cliente_id": cliente_id,
        "prioridade": "NORMAL",
        "defeito_relatado": "Estampa frente 2 cores",
        "dados_adicionais": {},
        "objeto": objeto,
        "itens": [],
    }, headers=header)


# =========================
# Registry (sem banco)
# =========================

def test_so_serigrafia_gera_identificador():
    """Placa e numero de serie existem no mundo -- nao se geram."""
    assert identificador_e_gerado("serigrafia") is True
    assert identificador_e_gerado("oficina_mecanica") is False
    assert identificador_e_gerado("assistencia_tecnica") is False


def test_codigo_nasce_do_numero_da_os():
    """Herda a unicidade do numero da OS: sem contador novo, sem corrida."""
    assert gerar_identificador("serigrafia", "0042") == "ART-0042"
    assert gerar_identificador("oficina_mecanica", "0042") is None


def test_codigo_nao_empilha_dois_prefixos():
    """O numero real da OS e "OS-2026-000001". Concatenar direto dava
    "ART-OS-2026-000001" -- dois prefixos, feio de ler e pior de escrever no
    quadro da tela, que e para o que este codigo existe."""
    assert gerar_identificador("serigrafia", "OS-2026-000001") == "ART-2026-000001"


# =========================
# Serigrafia: o sistema preenche o que o usuario nao sabe
# =========================

def test_serigrafia_abre_os_sem_o_usuario_informar_codigo(client, db_session):
    header = _autenticar_e_criar_empresa(client, "serigrafia")
    cliente_id = _criar_cliente(client, header)

    # O formulario da serigrafia manda so o que o atendente sabe: o nome da arte.
    r = _post_os(client, header, cliente_id, {
        "modelo": "Logo Claudinha frente",
        "dados_adicionais": {"tipo_trabalho": "camisa", "cores_quantidade": 2},
    })

    assert r.status_code == status.HTTP_201_CREATED, r.text
    corpo = r.json()
    objeto = corpo.get("objeto") or corpo.get("equipamento")

    codigo = objeto["numero_serie"]
    numero_os = corpo["numero_os"]
    # Carrega o numero da OS, com UM prefixo so: "OS-2026-000001" vira
    # "ART-2026-000001", e nao "ART-OS-2026-000001".
    assert codigo == f"ART-{numero_os.removeprefix('OS-')}"
    assert "ART-OS-" not in codigo


def test_serigrafia_preenche_a_marca_com_o_cliente_quando_vazia(client, db_session):
    """`marca` e coluna NOT NULL herdada do desenho de veiculo/equipamento.
    Numa serigrafia, a marca da arte no caso comum e o proprio cliente -- pedir
    que ele redigite isso seria atrito sem informacao nova."""
    header = _autenticar_e_criar_empresa(client, "serigrafia")
    cliente_id = _criar_cliente(client, header, nome="Claudinha")

    r = _post_os(client, header, cliente_id, {
        "modelo": "Logo Claudinha frente",
        "dados_adicionais": {"tipo_trabalho": "camisa"},
    })

    assert r.status_code == status.HTTP_201_CREATED, r.text
    objeto = r.json().get("objeto") or r.json().get("equipamento")
    assert objeto["marca"] == "Claudinha"


def test_serigrafia_respeita_o_codigo_quando_informado(client, db_session):
    """Gerar e o padrao, nao uma imposicao: loja que ja tem codigo proprio de
    arte continua podendo usa-lo."""
    header = _autenticar_e_criar_empresa(client, "serigrafia")
    cliente_id = _criar_cliente(client, header)

    r = _post_os(client, header, cliente_id, {
        "marca": "JotaArtes",
        "modelo": "Logo Claudinha",
        "numero_serie": "CLAU-2026-01",
        "dados_adicionais": {"tipo_trabalho": "camisa"},
    })

    assert r.status_code == status.HTTP_201_CREATED, r.text
    objeto = r.json().get("objeto") or r.json().get("equipamento")
    assert objeto["numero_serie"] == "CLAU-2026-01"


# =========================
# A PROTECAO DOS SEGMENTOS EM PRODUCAO
# =========================

def test_informatica_continua_exigindo_numero_de_serie(client, db_session):
    """O teste que justifica este arquivo.

    `numero_serie` virou opcional no schema por causa da serigrafia. Se a
    guarda do servico falhar, informatica -- em producao -- passa a aceitar OS
    sem identificador em silencio, e o objeto do cliente vira inencontravel.
    """
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header)

    r = _post_os(client, header, cliente_id, {
        "marca": "Dell",
        "modelo": "Inspiron",
        "dados_adicionais": {},
    })

    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, r.text


def test_oficina_continua_exigindo_placa(client, db_session):
    """Oficina tambem esta em producao, e a placa e validada por regex propria."""
    header = _autenticar_e_criar_empresa(client, "oficina_mecanica")
    cliente_id = _criar_cliente(client, header)

    sem_placa = _post_os(client, header, cliente_id, {
        "marca": "Fiat",
        "modelo": "Uno",
        "dados_adicionais": {},
    })
    assert sem_placa.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, sem_placa.text

    placa_invalida = _post_os(client, header, cliente_id, {
        "marca": "Fiat",
        "modelo": "Uno",
        "numero_serie": "NAO-E-PLACA",
        "dados_adicionais": {},
    })
    assert placa_invalida.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, placa_invalida.text


def test_informatica_nao_ganha_marca_automatica(client, db_session):
    """O preenchimento automatico de marca e SO do segmento que gera
    identificador. Informatica manda a marca de verdade e ela e preservada."""
    header = _autenticar_e_criar_empresa(client, "assistencia_tecnica")
    cliente_id = _criar_cliente(client, header, nome="Fulano")

    r = _post_os(client, header, cliente_id, {
        "marca": "Dell",
        "modelo": "Inspiron",
        "numero_serie": "C02X1234JGH5",
        "dados_adicionais": {},
    })

    assert r.status_code == status.HTTP_201_CREATED, r.text
    objeto = r.json().get("objeto") or r.json().get("equipamento")
    assert objeto["marca"] == "Dell"
