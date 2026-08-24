# ---------------------------------------------------------------------------
# ARQUIVO: test_licenca_validacao_offline.py
# DESCRICAO: Rede de seguranca do `_validar_offline` -- a funcao que decide se
#            a loja abre quando o servidor de licenca nao responde.
#
#            ESTES TESTES NASCERAM ANTES DA MUDANCA DA CARENCIA, de proposito:
#            a funcao nao tinha teste nenhum e e ela que mantem tres lojas em
#            producao funcionando. Os quatro primeiros descrevem o
#            comportamento que JA existia; se algum deles quebrar num commit
#            futuro, quebrou o que ja rodava.
#
#            Os limites sao TRES e independentes -- vencimento do plano,
#            validade offline (grace_period) e proxima validacao obrigatoria.
#            Cada um barra por um motivo diferente, e a carencia so afrouxa o
#            PRIMEIRO.
# ---------------------------------------------------------------------------

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services import licenca as licenca_service


AGORA = datetime.now(timezone.utc)


def _licenca(
    *,
    vencimento_em_dias: int = 30,
    dias_desde_sinc: int = 0,
    grace_period: int = 7,
    proxima_validacao_em_dias: int = 5,
    em_carencia: bool | None = None,
    carencia_ate_em_dias: int | None = None,
):
    """Licenca de mentira com os quatro prazos sob controle do teste."""
    return SimpleNamespace(
        token="token-falso",
        data_vencimento=AGORA + timedelta(days=vencimento_em_dias),
        ultima_sinc=AGORA - timedelta(days=dias_desde_sinc),
        grace_period=grace_period,
        proxima_validacao=AGORA + timedelta(days=proxima_validacao_em_dias),
        em_carencia=em_carencia,
        data_limite_carencia=(
            AGORA + timedelta(days=carencia_ate_em_dias)
            if carencia_ate_em_dias is not None
            else None
        ),
    )


@pytest.fixture(autouse=True)
def _jwt_sempre_valido(monkeypatch):
    """O JWT e assinado pelo servidor; aqui interessa a regra de datas.

    Sem isto todo teste morreria na assinatura, e o que se quer provar (qual
    prazo barra primeiro) nunca seria exercitado.
    """
    monkeypatch.setattr(licenca_service.jwt, "decode", lambda *a, **k: {"sub": "x"})


# =========================
# O QUE JA EXISTIA (guardioes)
# =========================

def test_licenca_em_dia_passa():
    resultado = licenca_service._validar_offline(_licenca(), public_key="pem")

    assert resultado["status"] == "offline_valid"
    assert resultado["dias_restantes"] >= 0


def test_vencimento_no_passado_expira():
    with pytest.raises(HTTPException) as erro:
        licenca_service._validar_offline(_licenca(vencimento_em_dias=-1), public_key="pem")

    assert erro.value.detail["codigo"] == "LICENCA_EXPIRADA"


def test_tempo_demais_sem_sincronizar_exige_internet():
    """Limite de validade OFFLINE. Nada a ver com pagamento: e quanto tempo a
    loja pode rodar sem falar com o servidor."""
    with pytest.raises(HTTPException) as erro:
        licenca_service._validar_offline(
            _licenca(dias_desde_sinc=10, grace_period=7), public_key="pem"
        )

    assert erro.value.detail["codigo"] == "REQUISITA_CONEXAO_INTERNET"


def test_data_de_validacao_obrigatoria_atingida_exige_internet():
    with pytest.raises(HTTPException) as erro:
        licenca_service._validar_offline(
            _licenca(proxima_validacao_em_dias=-1), public_key="pem"
        )

    assert erro.value.detail["codigo"] == "REQUISITA_CONEXAO_INTERNET"


def test_dias_restantes_e_o_menor_dos_tres_limites():
    """A tela mostra o prazo que vence primeiro, nao o mais generoso."""
    resultado = licenca_service._validar_offline(
        _licenca(vencimento_em_dias=30, dias_desde_sinc=5, grace_period=7,
                 proxima_validacao_em_dias=20),
        public_key="pem",
    )

    # grace: 7 - 5 = 2, o mais apertado dos tres
    assert resultado["dias_restantes"] == 2


# =========================
# CARENCIA (novo)
# =========================

def test_carencia_ativa_segura_a_loja_aberta_apos_o_vencimento():
    """Cartao em re-tentativa no Stripe: a data ja passou, mas o cliente nao e
    inadimplente por escolha -- pode ser limite, banco recusando, cartao
    trocado. Trava-lo no primeiro dia seria punir quem contratou justamente
    para nao precisar lembrar de pagar."""
    resultado = licenca_service._validar_offline(
        _licenca(vencimento_em_dias=-2, em_carencia=True, carencia_ate_em_dias=5),
        public_key="pem",
    )

    assert resultado["status"] == "offline_valid"


def test_carencia_vencida_expira_normalmente():
    with pytest.raises(HTTPException) as erro:
        licenca_service._validar_offline(
            _licenca(vencimento_em_dias=-10, em_carencia=True, carencia_ate_em_dias=-1),
            public_key="pem",
        )

    assert erro.value.detail["codigo"] == "LICENCA_EXPIRADA"


def test_carencia_sem_data_limite_nao_vale():
    """Flag ligada e limite ausente nao pode virar carencia infinita.

    Sem esta regra, um servidor que mandasse `emCarencia` e esquecesse a data
    daria uso ilimitado de graca -- e ninguem perceberia, porque o sintoma e
    o sistema funcionar."""
    with pytest.raises(HTTPException) as erro:
        licenca_service._validar_offline(
            _licenca(vencimento_em_dias=-2, em_carencia=True, carencia_ate_em_dias=None),
            public_key="pem",
        )

    assert erro.value.detail["codigo"] == "LICENCA_EXPIRADA"


def test_carencia_nao_afrouxa_a_validade_offline():
    """A carencia perdoa o PAGAMENTO, nao a falta de sincronizacao.

    Sao coisas diferentes: uma licenca em carencia que passou dez dias offline
    continua tendo que se conectar -- senao a carencia viraria uma porta para
    rodar desconectado o tempo que quisesse."""
    with pytest.raises(HTTPException) as erro:
        licenca_service._validar_offline(
            _licenca(vencimento_em_dias=-1, em_carencia=True, carencia_ate_em_dias=5,
                     dias_desde_sinc=10, grace_period=7),
            public_key="pem",
        )

    assert erro.value.detail["codigo"] == "REQUISITA_CONEXAO_INTERNET"


def test_licenca_antiga_sem_os_campos_de_carencia_continua_funcionando():
    """Instalacao que ainda nao sincronizou depois da atualizacao tem as duas
    colunas NULAS. Tem que se comportar exatamente como antes."""
    licenca = _licenca(vencimento_em_dias=10)
    assert licenca.em_carencia is None

    resultado = licenca_service._validar_offline(licenca, public_key="pem")
    assert resultado["status"] == "offline_valid"
