"""
A NF-e é o único módulo que NEGA quando a licença não responde.

Existe porque a regra geral é o contrário -- sem resposta, LIBERA (ver
app/core/modulos.py). Essa regra protege quem já usava o recurso de perdê-lo
por token velho ou rede fora. A NF-e não tem o que proteger: é recurso novo,
ninguém em campo tem. E errar para "tem" deixaria uma loja emitir documento
fiscal em nome dela na SEFAZ.

Estes testes existem para que, se alguém "simplificar" a exceção mais adiante,
a suíte reclame antes de o instalador chegar na loja.
"""

import pytest
from fastapi import HTTPException

from app.core.modulos import MODULOS_NEGADOS_SEM_RESPOSTA, requer_modulo


def _rodar(monkeypatch, identificador: str, modulos):
    """Executa a dependência de módulo com a lista que a licença devolveria."""
    from app.core import modulos as modulos_mod

    monkeypatch.setattr(
        modulos_mod.licenca_service,
        "modulos_da_licenca",
        lambda _db: modulos,
    )
    return requer_modulo(identificador)(db=None)


# --- NFE: "não sei" significa NÃO -------------------------------------------

@pytest.mark.parametrize("sem_resposta", [None, []])
def test_nfe_negada_quando_licenca_nao_responde(monkeypatch, sem_resposta):
    """Token sem a claim (None) e lista vazia -- os dois barram a NF-e.

    Lista vazia é o caso REAL de hoje: nenhuma licença em campo carrega
    módulos. Sem esta exceção, o Centro Fiscal abriria em toda loja.
    """
    with pytest.raises(HTTPException) as exc:
        _rodar(monkeypatch, "NFE", sem_resposta)

    assert exc.value.status_code == 403
    assert exc.value.detail["codigo"] == "MODULO_NAO_CONTRATADO"
    assert exc.value.detail["modulo"] == "NFE"


def test_nfe_liberada_quando_a_plataforma_concede(monkeypatch):
    """Concedida por plano ou por cliente, a lista chega com NFE dentro."""
    assert _rodar(monkeypatch, "NFE", ["FINANCEIRO", "NFE"]) is None


def test_nfe_negada_quando_a_lista_vem_sem_ela(monkeypatch):
    """Plataforma falou e não incluiu NFE: barra, como qualquer outro módulo."""
    with pytest.raises(HTTPException) as exc:
        _rodar(monkeypatch, "NFE", ["FINANCEIRO"])

    assert exc.value.status_code == 403


# --- Os demais módulos seguem a regra de sempre ------------------------------

@pytest.mark.parametrize("sem_resposta", [None, []])
def test_financeiro_continua_liberando_sem_resposta(monkeypatch, sem_resposta):
    """A exceção da NF-e NÃO pode ter mudado o comportamento dos outros.

    Se este teste quebrar, a trava passou a negar por padrão para todo mundo --
    e o efeito seria tirar a Gestão Financeira de quem já a usa.
    """
    assert _rodar(monkeypatch, "FINANCEIRO", sem_resposta) is None


def test_apenas_nfe_esta_na_lista_de_excecao():
    """A exceção é estreita de propósito.

    Cada módulo aqui dentro é um recurso que some quando a rede falha. Só entra
    o que ainda não está em uso por ninguém.
    """
    assert MODULOS_NEGADOS_SEM_RESPOSTA == frozenset({"NFE"})
