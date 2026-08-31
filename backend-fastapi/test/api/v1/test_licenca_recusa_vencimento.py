# ---------------------------------------------------------------------------
# ARQUIVO: test_licenca_recusa_vencimento.py
# DESCRICAO: A recusa da nuvem que significa "falta pagar" -- e a que nao.
#
#            O DEFEITO QUE ESTES TESTES FECHAM (visto na loja em 31/08/2026):
#            com o plano vencido e a maquina ONLINE, a nuvem respondia 4xx e o
#            sistema traduzia tudo para LICENCA_RECUSADA. O cliente parava numa
#            tela com "Tentar Novamente" e um link de suporte -- sem login, sem
#            renovacao. A tela de cobranca ja existia e era inalcancavel: ela so
#            abre com LICENCA_EXPIRADA, e esse codigo so nascia no caminho
#            OFFLINE (ou na simulacao por variavel de ambiente).
#
#            Duas invariantes, e elas puxam para lados opostos:
#              1. vencimento vira LICENCA_EXPIRADA e o login PASSA, senao a
#                 pessoa nao chega na tela que cobra;
#              2. recusa que nao e vencimento continua barrando igual antes --
#                 clonagem e bloqueio administrativo nao melhoram pagando.
# ---------------------------------------------------------------------------

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException

from app.services import licenca as licenca_service


AGORA = datetime.now(timezone.utc)


def _licenca(
    *,
    vencimento_em_dias: int = 30,
    em_carencia=None,
    carencia_ate_em_dias=None,
    bloqueada: bool = False,
):
    return SimpleNamespace(
        bloqueada=bloqueada,
        licenca_id="lic-1",
        token="token-falso",
        limite=3,
        chave_ativacao="cifrada",
        public_key=None,
        data_vencimento=AGORA + timedelta(days=vencimento_em_dias),
        ultima_sinc=AGORA,
        grace_period=7,
        proxima_validacao=AGORA + timedelta(days=5),
        em_carencia=em_carencia,
        data_limite_carencia=(
            AGORA + timedelta(days=carencia_ate_em_dias)
            if carencia_ate_em_dias is not None
            else None
        ),
    )


class _Resposta:
    """Resposta da nuvem, so com o que o codigo de licenca le."""

    def __init__(self, status_code: int, corpo=None, texto: str = ""):
        self.status_code = status_code
        self._corpo = corpo
        self.text = texto or (str(corpo) if corpo is not None else "")

    def json(self):
        if self._corpo is None:
            raise ValueError("corpo nao e JSON")
        return self._corpo


def _fingir_resposta(monkeypatch, resposta: _Resposta):
    """Faz qualquer POST httpx do modulo devolver esta resposta."""

    class _Cliente:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            return resposta

    monkeypatch.setattr(licenca_service.httpx, "Client", _Cliente)


# =========================
# O classificador
# =========================

def test_texto_da_nuvem_com_acento_conta_como_vencimento():
    """A frase que a loja recebeu de verdade, verbatim.

    A nuvem nao manda codigo nenhum hoje -- so este texto. Se este teste
    quebrar, o cliente vencido volta a cair na tela sem saida.
    """
    assert licenca_service._recusa_por_vencimento(
        403, "Licença vencida. Acesso negado.", {}, _licenca()
    )


def test_codigo_estruturado_vence_o_texto():
    assert licenca_service._recusa_por_vencimento(
        400, "qualquer coisa", {"codigo": "SUBSCRIPTION_EXPIRED"}, _licenca()
    )


def test_402_payment_required_conta_como_vencimento():
    assert licenca_service._recusa_por_vencimento(402, "", {}, _licenca())


def test_vencimento_gravado_na_maquina_serve_de_segunda_opiniao():
    """O dia em que a nuvem mudar a frase, o dado local ainda sabe.

    Essa data veio da propria nuvem na ultima sincronizacao bem-sucedida.
    """
    assert licenca_service._recusa_por_vencimento(
        403, "Acesso negado.", {}, _licenca(vencimento_em_dias=-1)
    )


def test_carencia_vigente_nao_e_vencimento():
    """Em carencia o vencimento passou, mas o gateway ainda esta tentando.

    Sem esta linha, uma recusa qualquer durante a carencia seria lida como
    "falta pagar" por causa da data local.
    """
    assert not licenca_service._recusa_por_vencimento(
        403,
        "Acesso negado.",
        {},
        _licenca(vencimento_em_dias=-1, em_carencia=True, carencia_ate_em_dias=5),
    )


def test_bloqueio_administrativo_nao_vira_vencimento():
    """Bloqueio nao se resolve pagando -- e continua barrando antes do login."""
    assert not licenca_service._recusa_por_vencimento(
        403, "Licenca bloqueada por uso indevido.", {"codigo": "LICENCA_BLOQUEADA"}, _licenca()
    )


def test_corpo_sem_json_nao_quebra_a_leitura():
    detalhe, corpo = licenca_service._detalhe_da_recusa(
        _Resposta(403, corpo=None, texto="Bad Request")
    )
    assert detalhe == "Bad Request"
    assert corpo == {}


# =========================
# /licenca/status (a tela de bloqueio)
# =========================

def test_status_traduz_recusa_por_vencimento_em_licenca_expirada(monkeypatch):
    _fingir_resposta(monkeypatch, _Resposta(403, {"msg": "Licença vencida. Acesso negado."}))

    with pytest.raises(HTTPException) as erro:
        licenca_service._tentar_conexao_remota(None, _licenca(), "chave", "hwid")

    assert erro.value.status_code == 403
    # E o codigo que abre a tela de cobranca. Qualquer outro prende o cliente
    # na tela de erro.
    assert erro.value.detail["codigo"] == "LICENCA_EXPIRADA"


def test_status_mantem_licenca_recusada_para_o_resto(monkeypatch):
    _fingir_resposta(monkeypatch, _Resposta(403, {"msg": "Licenca bloqueada."}))

    with pytest.raises(HTTPException) as erro:
        licenca_service._tentar_conexao_remota(None, _licenca(), "chave", "hwid")

    assert erro.value.detail["codigo"] == "LICENCA_RECUSADA"


def test_status_5xx_continua_caindo_no_offline(monkeypatch):
    """Servidor com problema nao e licenca invalida -- e fallback offline."""
    _fingir_resposta(monkeypatch, _Resposta(500, texto="boom"))

    with pytest.raises(httpx.ConnectError):
        licenca_service._tentar_conexao_remota(None, _licenca(), "chave", "hwid")


# =========================
# Login (conectar_terminal)
# =========================

@pytest.fixture
def _login_isolado(monkeypatch):
    """Login sem banco e sem criptografia: aqui interessa so a decisao."""
    criados: list[str] = []

    monkeypatch.setattr(licenca_service, "obter_hwid", lambda: "hwid-servidor")
    monkeypatch.setattr(licenca_service, "decriptar_valor", lambda *a, **k: "chave-limpa")
    monkeypatch.setattr(
        licenca_service.terminal_crud, "get_terminal_by_hwid", lambda db, hwid: None
    )
    monkeypatch.setattr(licenca_service.terminal_crud, "get_todos_terminais", lambda db: [])
    monkeypatch.setattr(
        licenca_service.terminal_crud,
        "create_terminal",
        lambda db, terminal: criados.append(terminal.hwid),
    )
    return criados


def test_licenca_vencida_deixa_o_terminal_logar(monkeypatch, _login_isolado):
    """A porta que faltava: sem isto o dono nao chega na tela que cobra.

    Entrar nao libera o sistema -- o /licenca/status ja respondeu
    LICENCA_EXPIRADA e o frontend prende tudo na renovacao.
    """
    monkeypatch.setattr(
        licenca_service.licenca_crud, "get_licenca", lambda db: _licenca(vencimento_em_dias=-3)
    )
    _fingir_resposta(monkeypatch, _Resposta(403, {"msg": "Licença vencida. Acesso negado."}))

    licenca_service.conectar_terminal(None, "hwid-terminal")

    assert _login_isolado == ["hwid-terminal"]


def test_limite_de_maquinas_continua_barrando(monkeypatch, _login_isolado):
    """A recusa que nao e vencimento nao ganhou passagem nenhuma."""
    monkeypatch.setattr(licenca_service.licenca_crud, "get_licenca", lambda db: _licenca())
    _fingir_resposta(
        monkeypatch, _Resposta(400, {"msg": "Limite de dispositivos atingido."})
    )

    with pytest.raises(HTTPException) as erro:
        licenca_service.conectar_terminal(None, "hwid-terminal")

    assert erro.value.detail["codigo"] == "LIMITE_TERMINAIS"
    assert _login_isolado == []


# =========================
# Bloqueio local x nuvem
# =========================
# O beco sem saida de 31/08/2026: a plataforma mostrava "Ativa, 15 dias
# restantes" e a maquina continuava em "Licenca bloqueada". So o heartbeat
# limpava a flag, e so com terminal respondendo 200 -- mas e o heartbeat que
# bloqueia, e ao bloquear ele APAGA os terminais. Sem terminal ele retorna antes
# de perguntar, e a flag nunca mais cai.

def test_validacao_online_limpa_o_bloqueio_local(monkeypatch):
    """A resposta da nuvem AGORA vale mais que a conclusao que tiramos antes."""
    licenca = _licenca(bloqueada=True)
    gravadas: list = []

    monkeypatch.setattr(
        licenca_service.licenca_crud, "update_licenca", lambda db, lic: gravadas.append(lic)
    )
    _fingir_resposta(
        monkeypatch,
        _Resposta(200, {
            "msg": "ok",
            "licencaId": "lic-1",
            "limite": 3,
            "dataVencimento": (AGORA + timedelta(days=15)).isoformat(),
            "token": "token-novo",
            "ultimaSincronizacao": AGORA.isoformat(),
            "gracePeriodDias": 7,
            "proximaValidacaoEm": (AGORA + timedelta(days=1)).isoformat(),
        }),
    )

    resultado = licenca_service._tentar_conexao_remota(
        SimpleNamespace(commit=lambda: None), licenca, "chave", "hwid"
    )

    assert resultado["status"] == "online_valid"
    assert licenca.bloqueada is False
    assert gravadas == [licenca]


def test_login_aceito_pela_nuvem_limpa_o_bloqueio(monkeypatch, _login_isolado):
    """Sem isto o dono loga e leva 403 em toda tela ate o proximo /licenca/status."""
    licenca = _licenca(bloqueada=True)
    monkeypatch.setattr(licenca_service.licenca_crud, "get_licenca", lambda db: licenca)
    monkeypatch.setattr(licenca_service.licenca_crud, "update_licenca", lambda db, lic: None)
    _fingir_resposta(monkeypatch, _Resposta(201, {"msg": "conectado"}))

    licenca_service.conectar_terminal(SimpleNamespace(commit=lambda: None), "hwid-terminal")

    assert licenca.bloqueada is False
    assert _login_isolado == ["hwid-terminal"]


def test_licenca_sadia_nao_grava_a_toa(monkeypatch):
    """Quem nunca esteve bloqueada nao gera escrita nenhuma por causa disto."""
    assert licenca_service._limpar_bloqueio(_licenca()) is False
