# ---------------------------------------------------------------------------
# ARQUIVO: test_licenca_renovacao.py
# DESCRICAO: Cobre a renovacao de assinatura (PIX / cartao) do lado da loja.
#
#            O que estes testes protegem, em ordem de consequencia:
#
#              1. a tela nao pode quebrar enquanto a API de cobranca nao subiu
#                 -- indisponivel e um estado NORMAL, nao um erro;
#              2. as rotas nao sao publicas (as de status sao, estas nao);
#              3. a traducao camelCase -> snake_case, que e o unico ponto onde
#                 um rename da nuvem pode nos atingir;
#              4. a comparacao de vencimento com fusos diferentes, que
#                 derrubaria a consulta bem no momento em que o cliente pagou.
# ---------------------------------------------------------------------------

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette import status

from app.services import licenca_renovacao as renovacao


# =========================
# Traducao de vocabulario
# =========================

def test_traduz_periodo_em_camelcase():
    periodo = renovacao._para_periodo({
        "codigo": "MENSAL",
        "nome": "Mensal",
        "valorCentavos": 8990,
        "dias": 30,
        "metodos": ["pix", "CARTAO"],
    })

    assert periodo.codigo == "MENSAL"
    assert periodo.valor_centavos == 8990
    assert periodo.dias == 30
    # Metodo sempre em caixa alta: a tela compara com "PIX"/"CARTAO".
    assert periodo.metodos == ["PIX", "CARTAO"]


def test_traduz_cobranca_pix():
    cobranca = renovacao._para_cobranca({
        "cobrancaId": "cob_123",
        "metodo": "PIX",
        "valorCentavos": 8990,
        "pixCopiaECola": "00020126...",
        "qrCodeBase64": None,
        "expiraEm": "2026-08-22T14:30:00Z",
    })

    assert cobranca.cobranca_id == "cob_123"
    assert cobranca.pix_copia_e_cola == "00020126..."
    assert cobranca.url_checkout is None


def test_traduz_cobranca_cartao():
    cobranca = renovacao._para_cobranca({
        "cobrancaId": "cob_456",
        "metodo": "CARTAO",
        "valorCentavos": 8990,
        "url": "https://checkout.stripe.com/abc",
    })

    assert cobranca.metodo == "CARTAO"
    assert cobranca.url_checkout == "https://checkout.stripe.com/abc"
    assert cobranca.pix_copia_e_cola is None


def test_aceita_sinonimos_de_campo():
    """A API descreve os mesmos dados com palavras diferentes em dois pontos.

    Aceitar os dois nomes evita que a tela morra por causa de um sinonimo. O dia
    que a nuvem se decidir, o alias sai -- e este teste avisa se sair errado.
    """
    assert renovacao._para_cobranca({"id": "x", "metodo": "PIX"}).cobranca_id == "x"
    assert renovacao._para_cobranca({"payload": "000201"}).pix_copia_e_cola == "000201"
    assert renovacao._para_cobranca({"encodedImage": "iVBOR"}).qr_code_base64 == "iVBOR"


# =========================
# Comparacao de vencimento
# =========================

def test_vencimento_compara_datas_com_fusos_diferentes():
    """O banco guarda data ingenua; o servidor manda com fuso. Comparar cru
    levanta TypeError e derrubaria a consulta logo apos o pagamento."""
    antes_ingenuo = datetime(2026, 8, 22, 12, 0, 0)
    depois_com_fuso = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)

    assert renovacao._mudou_o_vencimento(antes_ingenuo, depois_com_fuso) is True
    assert renovacao._mudou_o_vencimento(depois_com_fuso, antes_ingenuo) is False


def test_vencimento_igual_nao_conta_como_renovacao():
    data = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)
    assert renovacao._mudou_o_vencimento(data, data) is False


# =========================
# Indisponibilidade e uma tela calma
# =========================

def test_api_ainda_sem_a_rota_devolve_indisponivel_sem_erro(monkeypatch):
    """Enquanto a VPS nao subiu, a resposta e 404 -- e isso NAO e falha.

    Se virasse exception, o master abriria a tela de renovacao e veria um erro
    vermelho onde deveria ler "ainda nao disponivel".
    """
    monkeypatch.setattr(renovacao, "_credenciais", lambda db: ("chave", "hwid"))

    def _quatro_zero_quatro(*args, **kwargs):
        raise renovacao._erro(renovacao.INDISPONIVEL, "ainda nao disponivel")

    monkeypatch.setattr(renovacao, "_chamar", _quatro_zero_quatro)

    resultado = renovacao.listar_periodos(db=None)

    assert resultado.disponivel is False
    assert resultado.periodos == []
    assert resultado.motivo == "ainda nao disponivel"


def test_loja_offline_tambem_devolve_tela_calma(monkeypatch):
    monkeypatch.setattr(renovacao, "_credenciais", lambda db: ("chave", "hwid"))

    def _sem_rede(*args, **kwargs):
        raise renovacao._erro("SEM_CONEXAO", "Sem conexao com a internet.")

    monkeypatch.setattr(renovacao, "_chamar", _sem_rede)

    resultado = renovacao.listar_periodos(db=None)
    assert resultado.disponivel is False


def test_licenca_bloqueada_sobe_como_erro(monkeypatch):
    """Bloqueio administrativo NAO pode virar 'indisponivel': pagar nao resolve,
    e esconder isso deixaria o dono tentando pagar para sempre."""
    monkeypatch.setattr(renovacao, "_credenciais", lambda db: ("chave", "hwid"))

    def _bloqueada(*args, **kwargs):
        raise renovacao._erro("LICENCA_BLOQUEADA", "Licenca bloqueada.", status.HTTP_400_BAD_REQUEST)

    monkeypatch.setattr(renovacao, "_chamar", _bloqueada)

    with pytest.raises(HTTPException) as erro:
        renovacao.listar_periodos(db=None)

    assert erro.value.detail["codigo"] == "LICENCA_BLOQUEADA"


def test_periodos_traduzidos_de_ponta_a_ponta(monkeypatch):
    """Formato REAL da API, capturado dela em 22/08/2026.

    Duas armadilhas ficam registradas aqui:
      - a lista de PERIODOS chega num campo chamado "planos";
      - o plano de verdade vem em "plano", no singular, e e outra coisa: ele
        diz quantos computadores a loja pode usar, nao por quanto tempo paga.
    """
    monkeypatch.setattr(renovacao, "_credenciais", lambda db: ("chave", "hwid"))
    monkeypatch.setattr(
        renovacao.licenca_crud, "get_licenca",
        lambda db: SimpleNamespace(limite=3),
    )
    monkeypatch.setattr(renovacao, "_chamar", lambda *a, **k: {
        "plano": "Plano Start",
        "status": "ATIVA",
        "planos": [
            {"codigo": "MENSAL", "nome": "Mensal", "valorCentavos": 8990,
             "meses": 1, "desconto": 0, "metodos": ["CARTAO", "PIX"]},
            {"codigo": "ANUAL", "nome": "Anual", "valorCentavos": 101990,
             "meses": 12, "desconto": 0.0546, "metodos": ["CARTAO", "PIX"]},
        ],
    })

    resultado = renovacao.listar_periodos(db=None)

    assert resultado.disponivel is True
    assert resultado.plano == "Plano Start"
    # O limite de PCs vem da licenca LOCAL, nao da API.
    assert resultado.limite_terminais == 3

    mensal, anual = resultado.periodos
    assert mensal.valor_centavos == 8990
    # `meses` e o que a API manda; `dias` nunca vem. Ler so `dias` fazia a tela
    # mostrar preco sem dizer o que se compra.
    assert mensal.meses == 1
    assert anual.meses == 12
    assert round(anual.desconto, 3) == 0.055


# =========================
# Metodo de pagamento
# =========================

def test_metodo_invalido_e_recusado_antes_de_sair_da_maquina(monkeypatch):
    def _nao_deveria_chamar(*args, **kwargs):
        raise AssertionError("nao pode chamar a API com metodo invalido")

    monkeypatch.setattr(renovacao, "_chamar", _nao_deveria_chamar)

    with pytest.raises(HTTPException) as erro:
        renovacao.criar_cobranca(db=None, metodo="BOLETO", periodo="MENSAL")

    assert erro.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# =========================
# Pagamento confirmado -> revalidacao
# =========================

def test_cobranca_paga_revalida_a_licenca_antes_de_responder(monkeypatch):
    """`licenca_renovada` so pode ser True depois de o vencimento novo estar
    gravado aqui. A tela usa esse campo para cantar vitoria."""
    chamou = {"revalidou": False}

    monkeypatch.setattr(renovacao, "_credenciais", lambda db: ("chave", "hwid"))
    monkeypatch.setattr(renovacao, "_chamar", lambda *a, **k: {
        "cobrancaId": "cob_1", "status": "PAGA", "pagoEm": "2026-08-22T14:00:00Z",
    })

    def _revalidar(db):
        chamou["revalidou"] = True
        return True

    monkeypatch.setattr(renovacao, "revalidar_agora", _revalidar)

    resultado = renovacao.consultar_cobranca(db=None, cobranca_id="cob_1")

    assert resultado.status == "PAGA"
    assert chamou["revalidou"] is True
    assert resultado.licenca_renovada is True


def test_cobranca_pendente_nao_revalida(monkeypatch):
    """Polling de 5 em 5 segundos nao pode martelar o servidor de licenca."""
    monkeypatch.setattr(renovacao, "_credenciais", lambda db: ("chave", "hwid"))
    monkeypatch.setattr(renovacao, "_chamar", lambda *a, **k: {"cobrancaId": "c", "status": "PENDENTE"})

    def _nao_deveria(db):
        raise AssertionError("revalidou sem pagamento confirmado")

    monkeypatch.setattr(renovacao, "revalidar_agora", _nao_deveria)

    resultado = renovacao.consultar_cobranca(db=None, cobranca_id="c")
    assert resultado.licenca_renovada is False


# =========================
# Modo simulado
# =========================

def test_modo_simulado_desligado_por_padrao(monkeypatch):
    monkeypatch.delenv("STARTBIG_RENOVACAO_SIMULADA", raising=False)
    assert renovacao._modo_simulado() is False


def test_modo_simulado_entrega_pix_desenhavel(monkeypatch):
    monkeypatch.setenv("STARTBIG_RENOVACAO_SIMULADA", "1")

    cobranca = renovacao.criar_cobranca(db=None, metodo="PIX", periodo="MENSAL")

    assert cobranca.pix_copia_e_cola
    assert cobranca.pix_copia_e_cola.startswith("00020126")


def test_simulado_nunca_finge_que_a_licenca_renovou(monkeypatch):
    """O simulado existe para ver a TELA, nao para forjar licenca.

    Estender a licenca localmente e o que a invariante I4 proibe -- nem no modo
    de desenvolvimento o codigo pode aprender esse caminho.
    """
    monkeypatch.setenv("STARTBIG_RENOVACAO_SIMULADA", "1")

    cobranca = renovacao.criar_cobranca(db=None, metodo="PIX", periodo="MENSAL")
    registro = renovacao._COBRANCAS_SIMULADAS[cobranca.cobranca_id]
    registro["criada_em"] = datetime.now(timezone.utc) - timedelta(minutes=5)

    status_cobranca = renovacao.consultar_cobranca(db=None, cobranca_id=cobranca.cobranca_id)

    assert status_cobranca.status == "PAGA"
    assert status_cobranca.licenca_renovada is False


# =========================
# Simulacoes de desenvolvimento nao vazam para producao
# =========================

def test_simulacao_de_licenca_vencida_desligada_por_padrao(client, db_session, monkeypatch):
    """A flag que finge licenca vencida NAO pode estar ligada sem alguem pedir.

    Ligada por engano, ela tranca a loja inteira numa tela de cobranca. Este
    teste e a unica coisa entre um `.env` distraido e um cliente sem sistema.
    """
    monkeypatch.delenv("STARTBIG_LICENCA_EXPIRADA_SIMULADA", raising=False)

    resposta = client.get("/api/v1/licenca/status")
    corpo = resposta.json()

    # Sem licenca cadastrada no banco de teste a resposta e "nao encontrada" --
    # o que importa e que NAO e a simulacao de vencida.
    if resposta.status_code == 403:
        assert corpo["detail"]["codigo"] != "LICENCA_EXPIRADA"


# =========================
# As rotas nao sao publicas
# =========================

@pytest.mark.parametrize("metodo,rota", [
    ("get", "/api/v1/licenca/renovacao/periodos"),
    ("post", "/api/v1/licenca/renovacao/cobranca"),
    ("get", "/api/v1/licenca/renovacao/cobranca/qualquer"),
    ("post", "/api/v1/licenca/renovacao/revalidar"),
])
def test_rota_de_renovacao_exige_autenticacao(client, db_session, metodo, rota):
    """`/licenca/status` e publica porque roda antes do login. Estas NAO sao:
    mexem em dinheiro e sao exclusivas do master."""
    resposta = (
        client.get(rota) if metodo == "get" else client.post(rota, json={})
    )
    assert resposta.status_code in (
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ), resposta.text
