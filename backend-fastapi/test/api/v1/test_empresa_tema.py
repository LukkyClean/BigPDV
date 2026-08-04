# ---------------------------------------------------------------------------
# ARQUIVO: test_empresa_tema.py
# DESCRICAO: Cobre a cor do tema da empresa.
#
#            Duas garantias, opostas de proposito:
#              - LER e publico. A tela de login precisa da cor antes de existir
#                token, e o terminal precisa dela no boot. A exposicao e minima:
#                so o hex, nada mais da empresa.
#              - GRAVAR exige master. Foi a regra pedida ("quem decide e o dono,
#                ponto final"), e ela vem do PUT /empresas/ que ja era protegido.
# ---------------------------------------------------------------------------

from starlette import status

MASTER_EMAIL = "master.tema@example.com"
MASTER_SENHA = "senhaSegura456"
COMUM_EMAIL = "comum.tema@example.com"
COMUM_SENHA = "outraSenha789"

ROTA_TEMA = "/api/v1/empresas/tema"
ROTA_EMPRESA = "/api/v1/empresas/"


def _criar_master_e_empresa(client) -> dict:
    """Primeiro usuario criado vira master; cria a empresa e devolve o header."""
    client.post("/api/v1/usuarios/", json={
        "nome": "Dono da Loja",
        "email": MASTER_EMAIL,
        "senha": MASTER_SENHA,
    })
    login = client.post("/api/v1/auth/login", data={
        "username": MASTER_EMAIL,
        "password": MASTER_SENHA,
        "hwid": "test-terminal-hwid",
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}

    r = client.post("/api/v1/empresas/", json={
        "razao_social": "Empresa Tema LTDA",
        "nome_fantasia": "Tema",
        "is_cnpj": True,
        "documento": "12345678000199",
        "regime_tributario": "Simples Nacional",
        "celular": "11999998888",
        "segmento": "assistencia_tecnica",
        "endereco": [{
            "logradouro": "Av. Paulista", "numero": "1000", "bairro": "Bela Vista",
            "cidade": "São Paulo", "estado": "SP", "cep": "01310-100",
        }],
    }, headers=header)
    assert r.status_code == 201, r.text
    return header


# =========================
# LEITURA — publica
# =========================

def test_tema_e_publico_e_comeca_nulo(client, db_session):
    """Sem empresa e sem token: responde 200 com null, nao 401 nem 500.

    A tela de login abre antes de tudo isso existir e nao pode quebrar por causa
    de cor."""
    r = client.get(ROTA_TEMA)
    assert r.status_code == status.HTTP_200_OK, r.text
    assert r.json() == {"cor_tema": None}


def test_tema_publico_devolve_a_cor_gravada(client, db_session):
    header = _criar_master_e_empresa(client)

    assert client.put(ROTA_EMPRESA, json={"cor_tema": "#7b1fa2"}, headers=header).status_code == 200

    # Sem header nenhum — e o caso da tela de login.
    r = client.get(ROTA_TEMA)
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["cor_tema"] == "#7b1fa2"


def test_tema_publico_nao_vaza_dados_da_empresa(client, db_session):
    """A resposta tem exatamente uma chave. Endpoint sem autenticacao nao pode
    virar porta dos fundos para razao social, documento ou endereco."""
    _criar_master_e_empresa(client)

    corpo = client.get(ROTA_TEMA).json()
    assert set(corpo.keys()) == {"cor_tema"}


# =========================
# ESCRITA — so master
# =========================

def test_master_grava_a_cor(client, db_session):
    header = _criar_master_e_empresa(client)

    r = client.put(ROTA_EMPRESA, json={"cor_tema": "#00c853"}, headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    assert r.json()["cor_tema"] == "#00c853"


def test_gravacao_do_tema_exige_master():
    """
    GUARDIAO da regra de produto: so o dono decide a identidade visual.

    Verifica a AMARRACAO, nao o efeito: que a rota de gravacao pende de
    `get_current_master_user`. Trocar essa dependencia por `get_current_user`
    liberaria a cor para qualquer balconista sem quebrar nenhum outro teste --
    e este falha na hora.

    Nao da para exercitar o 403 de ponta a ponta aqui: `POST /usuarios/` e o
    endpoint de setup e cria sempre com is_master=True, entao um usuario comum
    exigiria montar cargo + funcionario + login. A amarracao cobre o essencial.
    """
    from app.api.v1.endpoints import empresa as endpoint_empresa
    from app.core.depends import get_current_master_user

    rota_put = next(
        r for r in endpoint_empresa.router.routes
        if getattr(r, "path", None) == "/" and "PUT" in getattr(r, "methods", set())
    )
    dependencias = [d.call for d in rota_put.dependant.dependencies]
    assert get_current_master_user in dependencias


def test_leitura_do_tema_nao_exige_autenticacao():
    """O espelho do teste acima: a rota publica NAO pode ganhar trava, senao a
    tela de login volta a abrir sem a cor da empresa."""
    from app.api.v1.endpoints import empresa as endpoint_empresa
    from app.core.depends import get_current_master_user, get_current_user

    rota_tema = next(
        r for r in endpoint_empresa.router.routes
        if getattr(r, "path", None) == "/tema"
    )
    dependencias = [d.call for d in rota_tema.dependant.dependencies]
    assert get_current_user not in dependencias
    assert get_current_master_user not in dependencias


def test_cor_invalida_e_recusada(client, db_session):
    """O hex e validado no schema: texto solto nao entra no banco para o
    frontend descobrir na hora de pintar a tela."""
    header = _criar_master_e_empresa(client)

    for invalida in ["vermelho", "#12345", "045ca1", "#zzzzzz", "#0000000"]:
        r = client.put(ROTA_EMPRESA, json={"cor_tema": invalida}, headers=header)
        assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, f"{invalida}: {r.text}"


def test_cor_nula_volta_ao_padrao(client, db_session):
    """NULL e o 'restaurar padrao' — a instalacao volta a paleta de fabrica."""
    header = _criar_master_e_empresa(client)

    client.put(ROTA_EMPRESA, json={"cor_tema": "#7b1fa2"}, headers=header)
    assert client.get(ROTA_TEMA).json()["cor_tema"] == "#7b1fa2"

    r = client.put(ROTA_EMPRESA, json={"cor_tema": None}, headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    assert client.get(ROTA_TEMA).json()["cor_tema"] is None


# =========================
# CHAVE PIX
# =========================

def test_master_grava_chave_pix(client, db_session):
    header = _criar_master_e_empresa(client)

    r = client.put(ROTA_EMPRESA, json={
        "chave_pix": "loja@exemplo.com.br",
        "pix_ativo": True,
    }, headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    assert r.json()["chave_pix"] == "loja@exemplo.com.br"
    assert r.json()["pix_ativo"] is True


def test_pix_comeca_desligado(client, db_session):
    """Instalacao existente nao passa a exibir QR sozinha ao atualizar."""
    header = _criar_master_e_empresa(client)

    r = client.get(ROTA_EMPRESA, headers=header)
    assert r.status_code == status.HTTP_200_OK, r.text
    assert r.json()["chave_pix"] is None
    assert r.json()["pix_ativo"] is False


def test_chave_pix_aceita_as_cinco_formas(client, db_session):
    """CPF, CNPJ, telefone, e-mail e aleatoria: o QR embute a chave literalmente,
    entao o backend nao impoe formato."""
    header = _criar_master_e_empresa(client)

    for chave in [
        "12345678901",
        "12345678000199",
        "+5511987654321",
        "loja@exemplo.com.br",
        "123e4567-e89b-12d3-a456-426614174000",
    ]:
        r = client.put(ROTA_EMPRESA, json={"chave_pix": chave}, headers=header)
        assert r.status_code == status.HTTP_200_OK, f"{chave}: {r.text}"
        assert r.json()["chave_pix"] == chave


def test_chave_pix_longa_demais_e_recusada(client, db_session):
    """77 e o teto do BR Code. Recusar aqui evita gerar um QR invalido depois."""
    header = _criar_master_e_empresa(client)

    r = client.put(ROTA_EMPRESA, json={"chave_pix": "a" * 78}, headers=header)
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, r.text


def test_chave_pix_e_publica_apenas_pelo_endpoint_autenticado(client, db_session):
    """GUARDIAO: a rota publica /tema devolve SO a cor. A chave PIX nao pode vazar
    por ela -- e dado de recebimento, ainda que apareca no QR para quem compra."""
    header = _criar_master_e_empresa(client)
    client.put(ROTA_EMPRESA, json={"chave_pix": "loja@exemplo.com.br"}, headers=header)

    corpo = client.get(ROTA_TEMA).json()
    assert set(corpo.keys()) == {"cor_tema"}
