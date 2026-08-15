# ---------------------------------------------------------------------------
# Testes do segmento PDV (fase 5): a loja que nao tem Ordem de Servico.
#
# A PROVA E NOS DOIS SENTIDOS, e o segundo importa mais que o primeiro:
#   1. loja de PDV nao recebe OS;
#   2. as tres lojas EM PRODUCAO continuam recebendo, exatamente como antes.
#
# O frontend inteiro decide pelo campo `usa_ordem_servico` que vem no
# /usuarios/me. Se ele vier errado, some o modulo de Servicos de uma oficina que
# estava trabalhando -- por isso o contrato e testado aqui, e nao so a regra.
# ---------------------------------------------------------------------------

import pytest

from app.core.segmentos import segmento_usa_ordem_servico

SENHA = "senhaSegura456"


def _cadastrar(client, segmento, sufixo):
    """Cria usuario + empresa de um segmento e devolve o header autenticado."""
    email = f"pdv.{sufixo}@example.com"
    client.post("/api/v1/usuarios/", json={
        "nome": f"Dono {sufixo}", "email": email, "senha": SENHA,
    })
    login = client.post("/api/v1/auth/login", data={
        "username": email, "password": SENHA, "hwid": "test-terminal-hwid",
    })
    assert login.status_code == 200, login.text
    header = {"Authorization": f"Bearer {login.json()['access_token']}"}

    r = client.post("/api/v1/empresas/", json={
        "razao_social": f"Empresa {sufixo} LTDA", "nome_fantasia": sufixo, "is_cnpj": True,
        "documento": "12345678000199", "regime_tributario": "Simples Nacional",
        "celular": "11999998888", "segmento": segmento,
        "endereco": [{"logradouro": "Av. Paulista", "numero": "1000", "bairro": "Bela Vista",
                      "cidade": "São Paulo", "estado": "SP", "cep": "01310-100"}],
    }, headers=header)
    assert r.status_code == 201, r.text
    return header


def _usa_os(client, header):
    r = client.get("/api/v1/usuarios/me", headers=header)
    assert r.status_code == 200, r.text
    return r.json()["empresa"]["usa_ordem_servico"]


# ===========================================================================
# 1. A loja de PDV
# ===========================================================================

def test_pdv_e_aceito_no_cadastro(client, db_session):
    """O segmento tem que existir nos DOIS espelhos.

    Foi assim que a serigrafia falhou quando entrou: a lista do frontend ganhou
    o valor, o `Literal` do backend nao, e o cadastro morria com
    "Invalid enum value ... received 'serigrafia'".
    """
    header = _cadastrar(client, "pdv", "adega")
    assert header is not None


def test_me_diz_que_a_loja_de_pdv_nao_usa_ordem_de_servico(client, db_session):
    header = _cadastrar(client, "pdv", "adega")
    assert _usa_os(client, header) is False


# ===========================================================================
# 2. As tres lojas que JA RODAM -- a prova que mais importa
# ===========================================================================

@pytest.mark.parametrize("segmento", ["assistencia_tecnica", "oficina_mecanica", "serigrafia"])
def test_lojas_em_producao_continuam_com_ordem_de_servico(client, db_session, segmento):
    header = _cadastrar(client, segmento, segmento)
    assert _usa_os(client, header) is True


def test_segmentos_sem_definicao_continuam_com_ordem_de_servico(client, db_session):
    """Marcenaria e eletricista nao tem arquivo de definicao -- e tem OS.

    Se o padrao fosse "so tem OS quem declarar", estes segmentos perderiam o
    modulo sem ninguem pedir.
    """
    header = _cadastrar(client, "marcenaria", "marcenaria")
    assert _usa_os(client, header) is True


def test_empresa_sem_segmento_continua_com_ordem_de_servico(client, db_session):
    """Instalacao antiga, cadastrada antes de existir segmento."""
    assert segmento_usa_ordem_servico(None) is True


# ===========================================================================
# 3. O contrato do registry
# ===========================================================================

def test_pdv_nao_declara_capacidades_nem_campos_de_os():
    """Sem OS nao ha objeto de servico: declarar campo aqui seria metadado orfao."""
    from app.core.segmentos import get_definicao_segmento

    definicao = get_definicao_segmento("pdv")
    assert definicao is not None
    assert definicao["capacidades"] == []
    assert definicao["checkin"] == []
    assert definicao["vistoria"] == []
    assert definicao["identificador"] is None


def test_mercado_deixou_de_ser_segmento_valido():
    """O valor foi rebatizado; a migration b3c4d5e6f7a8 converte quem ja existia."""
    from app.schemas.auth import SEGMENTOS_VALIDOS
    from typing import get_args

    validos = get_args(SEGMENTOS_VALIDOS)
    assert "pdv" in validos
    assert "mercado" not in validos
