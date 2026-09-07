# ---------------------------------------------------------------------------
# Testes do cadastro duravel de terminais (fase 3 do PDV profissional).
#
# O teste que importa mais aqui e o do INVARIANTE: terminal que ninguem
# configurou NUNCA perde a trava de caixa. Papel ausente e papel 'PDV' sao a
# mesma coisa, e RETAGUARDA e excecao explicita -- nunca fallback.
#
# Errar para "cobra turno demais" custa um clique de configuracao. Errar para
# "nao cobra" custa o controle da gaveta, e falha em SILENCIO: nada quebra na
# hora, o dinheiro so nao bate no fim do dia.
#
# O segundo em importancia e o da DURABILIDADE: nome e papel tem que sobreviver
# ao logout. Era exatamente isso que nao acontecia quando eles moravam em
# `terminais_conectados`, que e esvaziada no boot, no shutdown e no logout -- o
# dono marcava a maquina dele como retaguarda e amanha ela era um caixa de novo.
# ---------------------------------------------------------------------------

from starlette import status

from app.db.models.terminal import Terminal
from app.db.models.terminal_conectado import TerminalConectado

HWID = "test-terminal-hwid"

TEST_USER_EMAIL = "terminais.dono@example.com"
TEST_USER_PASSWORD = "senhaSegura456"


# ===========================================================================
# HELPERS
# ===========================================================================

def _auth(client, hwid=HWID):
    client.post("/api/v1/usuarios/", json={
        "nome": "Dono da Adega", "email": TEST_USER_EMAIL, "senha": TEST_USER_PASSWORD,
    })
    login = client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": hwid,
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post("/api/v1/empresas/", json={
        "razao_social": "Adega Teste LTDA", "nome_fantasia": "Adega", "is_cnpj": True,
        "documento": "12345678000195", "regime_tributario": "Simples Nacional",
        "celular": "11999998888", "segmento": "pdv",
        "endereco": [{"logradouro": "Av. Paulista", "numero": "1000", "bairro": "Bela Vista",
                      "cidade": "São Paulo", "estado": "SP", "cep": "01310-100"}],
    }, headers=header)
    # A empresa nasce DEPOIS do login (onboarding), entao no primeiro login nao
    # ha onde pendurar a maquina. Quem fecha essa lacuna e a tela de Terminais,
    # que cadastra a maquina de quem a abriu -- e e o que o dono faz para
    # configurar o terminal em que esta.
    client.get("/api/v1/terminais/", headers={**header, "X-Terminal-HWID": hwid})
    return header


def _terminal_do_banco(db_session, hwid=HWID):
    return db_session.query(Terminal).filter(Terminal.hwid == hwid).first()


# ===========================================================================
# CADASTRO NO LOGIN
# ===========================================================================

def test_login_cadastra_o_terminal_uma_unica_vez(client, db_session):
    """A maquina se cadastra sozinha, e o login seguinte NAO a reescreve.

    Se o login reescrevesse o cadastro, a configuracao do dono duraria ate o
    proximo cafe: ele batiza a maquina, sai para almocar, volta e ela e
    "Terminal sem nome" de novo.
    """
    header = _auth(client)

    terminal = _terminal_do_banco(db_session)
    assert terminal is not None
    assert terminal.hwid == HWID
    assert terminal.nome is None      # ainda nao batizado
    assert terminal.papel is None     # e NULL significa PDV

    # Batiza e faz login de novo.
    r = client.patch(
        f"/api/v1/terminais/{terminal.id}",
        json={"nome": "Caixa 01", "papel": "PDV"},
        headers=header,
    )
    assert r.status_code == 200, r.text

    client.post("/api/v1/auth/login", data={
        "username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "hwid": HWID,
    })

    db_session.expire_all()
    assert _terminal_do_banco(db_session).nome == "Caixa 01"


def test_cadastro_sobrevive_ao_sumico_da_tabela_de_presenca(client, db_session):
    """O ponto inteiro desta fase.

    `terminais_conectados` e esvaziada no boot, no shutdown e perde a linha no
    logout. Enquanto nome e papel moravam la, evaporavam junto. Aqui a presenca
    e apagada e o cadastro tem que continuar de pe.
    """
    header = _auth(client)
    terminal = _terminal_do_banco(db_session)
    client.patch(
        f"/api/v1/terminais/{terminal.id}",
        json={"nome": "Escritorio", "papel": "RETAGUARDA"},
        headers=header,
    )

    # O logout/boot faz exatamente isto com a tabela de presenca.
    db_session.query(TerminalConectado).delete()
    db_session.flush()
    db_session.expire_all()

    sobrevivente = _terminal_do_banco(db_session)
    assert sobrevivente is not None
    assert sobrevivente.nome == "Escritorio"
    assert sobrevivente.papel == "RETAGUARDA"


# ===========================================================================
# O INVARIANTE DO PAPEL
# ===========================================================================

def test_terminal_nao_configurado_e_tratado_como_caixa(client, db_session):
    """NULL nao e RETAGUARDA. Maquina sem configuracao continua cobrando turno."""
    header = _auth(client)

    r = client.get("/api/v1/terminais/este", headers={**header, "X-Terminal-HWID": HWID})
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["papel"] is None
    assert corpo["e_retaguarda"] is False   # <- o invariante


def test_papel_pdv_explicito_tambem_cobra_turno(client, db_session):
    """'PDV' e NULL sao a mesma coisa: so RETAGUARDA dispensa."""
    header = _auth(client)
    terminal = _terminal_do_banco(db_session)
    client.patch(f"/api/v1/terminais/{terminal.id}", json={"papel": "PDV"}, headers=header)

    r = client.get("/api/v1/terminais/este", headers={**header, "X-Terminal-HWID": HWID})
    assert r.json()["e_retaguarda"] is False


def test_retaguarda_e_a_unica_excecao(client, db_session):
    header = _auth(client)
    terminal = _terminal_do_banco(db_session)
    client.patch(
        f"/api/v1/terminais/{terminal.id}", json={"papel": "RETAGUARDA"}, headers=header
    )

    r = client.get("/api/v1/terminais/este", headers={**header, "X-Terminal-HWID": HWID})
    assert r.json()["e_retaguarda"] is True


def test_papel_invalido_e_recusado(client, db_session):
    """Nao existe papel 'CAIXA', 'ADMIN' nem string livre.

    Um papel desconhecido cairia no `!= RETAGUARDA` e viraria PDV por acidente
    -- funcionaria, mas por engano, e o proximo papel que alguem inventar
    poderia cair do outro lado.
    """
    header = _auth(client)
    terminal = _terminal_do_banco(db_session)
    r = client.patch(
        f"/api/v1/terminais/{terminal.id}", json={"papel": "GERENTE"}, headers=header
    )
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===========================================================================
# EDICAO
# ===========================================================================

def test_salvar_so_o_nome_nao_apaga_o_papel(client, db_session):
    """`exclude_unset`: campo ausente e "nao mexer", nao "limpar".

    Sem isso, renomear a maquina do dono devolveria ela para a regra de caixa
    sem ninguem ter pedido -- e o sintoma seria "do nada o meu PC comecou a
    pedir abertura de turno".
    """
    header = _auth(client)
    terminal = _terminal_do_banco(db_session)
    client.patch(
        f"/api/v1/terminais/{terminal.id}",
        json={"nome": "Escritorio", "papel": "RETAGUARDA"},
        headers=header,
    )

    r = client.patch(
        f"/api/v1/terminais/{terminal.id}", json={"nome": "Sala do dono"}, headers=header
    )
    assert r.status_code == 200, r.text
    assert r.json()["nome"] == "Sala do dono"
    assert r.json()["papel"] == "RETAGUARDA"   # intacto


def test_nome_em_branco_volta_a_ser_nulo(client, db_session):
    """Espaco em branco parece preenchido e nao e.

    Gravado cru, a coluna Terminal do relatorio mostraria um espaco -- o dono
    leria "esta configurado" e nao estaria.
    """
    header = _auth(client)
    terminal = _terminal_do_banco(db_session)
    r = client.patch(
        f"/api/v1/terminais/{terminal.id}", json={"nome": "   "}, headers=header
    )
    assert r.status_code == 200, r.text
    assert r.json()["nome"] is None


def test_este_devolve_null_sem_hwid(client, db_session):
    """"Nao sei quem e esta maquina" e resposta normal, nao erro.

    Acontece no intervalo entre a atualizacao e o primeiro login. A tela trata
    como "sou um caixa", que e o lado seguro.
    """
    header = _auth(client)
    r = client.get("/api/v1/terminais/este", headers=header)
    assert r.status_code == 200
    assert r.json() is None


def test_hwid_desconhecido_nao_vaza_terminal_de_outra_empresa(client, db_session):
    header = _auth(client)
    r = client.get(
        "/api/v1/terminais/este",
        headers={**header, "X-Terminal-HWID": "maquina-que-nao-existe"},
    )
    assert r.status_code == 200
    assert r.json() is None


# ===========================================================================
# QUEM PODE
# ===========================================================================

def test_listar_exige_visao_gerencial(client, db_session):
    """Quais maquinas a loja tem, e qual e retaguarda, e informacao de dono.

    Mesma regua do historico de caixas, pela mesma razao: sem ela, um operador
    enxergaria a estrutura da loja inteira.
    """
    header = _auth(client)
    r = client.get("/api/v1/terminais/", headers=header)
    # O dono (cargo Master) passa; a lista existe e traz a propria maquina.
    assert r.status_code == 200, r.text
    assert any(t["hwid"] == HWID for t in r.json())


def test_terminal_de_outra_empresa_nao_e_editavel(client, db_session):
    """O id vem da URL: sem o filtro por empresa, bastaria adivinhar o numero.

    A empresa e forjada direto no banco porque o cadastro pela API cria a
    empresa DO usuario logado -- e o que precisa ser provado aqui e justamente o
    caso em que a linha pertence a outra.
    """
    from app.db.models.empresa import Empresa

    header = _auth(client)

    outra = db_session.query(Empresa).filter(Empresa.documento == "99999999000199").first()
    if outra is None:
        outra = Empresa(
            razao_social="Outra Loja LTDA", nome_fantasia="Outra", is_cnpj=True,
            documento="99999999000199", regime_tributario="Simples Nacional",
            celular="11888887777", segmento="pdv",
        )
        db_session.add(outra)
        db_session.flush()

    intruso = Terminal(empresa_id=outra.id, hwid="hwid-de-outra-loja")
    db_session.add(intruso)
    db_session.flush()

    r = client.patch(
        f"/api/v1/terminais/{intruso.id}", json={"nome": "invadido"}, headers=header
    )
    assert r.status_code == status.HTTP_404_NOT_FOUND
