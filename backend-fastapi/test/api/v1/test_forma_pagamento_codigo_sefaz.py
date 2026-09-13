# ---------------------------------------------------------------------------
# ARQUIVO: test_forma_pagamento_codigo_sefaz.py
# DESCRIÇÃO: Toda forma de pagamento padrão nasce com o código da NF-e.
#
# O gate recusa a emissão enquanto houver forma ATIVA sem `codigo_sefaz`
# (`pendencias_globais.pagamentos_sem_sefaz`). As seis formas padrão nasciam
# com o campo NULL e nenhuma tela permitia preencher: toda instalação ficava
# impedida de emitir por um campo sem caminho. Achado numa loja real em
# 12/09/2026.
# ---------------------------------------------------------------------------

import pytest

from app.core import tarefas as tarefas_mod
from app.core.tarefas import _CODIGO_SEFAZ_PADRAO, _FORMAS_PAGAMENTO_PADRAO, _seed_formas_pagamento
from app.db.models.forma_pagamento import FormaPagamento

from test.conftest import TestingSessionLocal


@pytest.fixture
def seed_no_banco_de_teste(monkeypatch):
    """
    `_seed_formas_pagamento` abre a PRÓPRIA sessão (`SessionLocal`), porque roda
    no boot, sem request. Sem este patch ela escreveria no banco de
    desenvolvimento e o teste passaria por engano, consultando um banco onde
    nada aconteceu.
    """
    monkeypatch.setattr(tarefas_mod, "SessionLocal", TestingSessionLocal)


def test_toda_forma_padrao_tem_codigo_mapeado():
    """
    Nenhuma das seis formas padrão pode ficar de fora do mapa — é o que
    garante que a instalação nova nasce apta a emitir.
    """
    for nome in _FORMAS_PAGAMENTO_PADRAO:
        assert nome.strip().lower() in _CODIGO_SEFAZ_PADRAO, f"'{nome}' sem código SEFAZ"


def test_codigos_sao_dois_digitos():
    """`tPag` tem dois dígitos, e a coluna é String(2)."""
    for codigo in _CODIGO_SEFAZ_PADRAO.values():
        assert len(codigo) == 2 and codigo.isdigit(), codigo


def test_codigos_batem_com_a_tabela_da_nfe():
    """Os que o varejo usa todo dia, conferidos um a um contra o layout."""
    assert _CODIGO_SEFAZ_PADRAO["dinheiro"] == "01"
    assert _CODIGO_SEFAZ_PADRAO["cheque"] == "02"
    assert _CODIGO_SEFAZ_PADRAO["cartão de crédito"] == "03"
    assert _CODIGO_SEFAZ_PADRAO["cartão de débito"] == "04"
    assert _CODIGO_SEFAZ_PADRAO["fiado"] == "05"        # 05 = Crédito Loja
    assert _CODIGO_SEFAZ_PADRAO["boleto"] == "15"
    assert _CODIGO_SEFAZ_PADRAO["pix"] == "17"
    assert _CODIGO_SEFAZ_PADRAO["transferência bancária"] == "18"


def test_seed_completa_o_codigo_de_quem_ja_existia(db_session, seed_no_banco_de_teste):
    """
    Backfill: a loja que já roda tem as formas criadas antes de o campo
    existir. O seed roda no boot e completa.
    """
    db_session.add(FormaPagamento(nome="Dinheiro", ativo=True, codigo_sefaz=None))
    db_session.commit()

    _seed_formas_pagamento()

    forma = db_session.query(FormaPagamento).filter(FormaPagamento.nome == "Dinheiro").first()
    db_session.refresh(forma)
    assert forma.codigo_sefaz == "01"


def test_seed_nao_sobrescreve_escolha_da_loja(db_session, seed_no_banco_de_teste):
    """
    A loja pode ter trocado de propósito — o 20 do PIX estático, por exemplo.
    Sobrescrever a cada reinício desfaria a decisão do contador.
    """
    db_session.add(FormaPagamento(nome="PIX", ativo=True, codigo_sefaz="20"))
    db_session.commit()

    _seed_formas_pagamento()

    forma = db_session.query(FormaPagamento).filter(FormaPagamento.nome == "PIX").first()
    db_session.refresh(forma)
    assert forma.codigo_sefaz == "20"


def test_instalacao_nova_nasce_sem_pendencia_de_pagamento(db_session, seed_no_banco_de_teste):
    """O caminho que importa: seed do zero e nenhuma forma ativa sem código."""
    _seed_formas_pagamento()

    sem_codigo = (
        db_session.query(FormaPagamento)
        .filter(
            FormaPagamento.ativo == True,  # noqa: E712
            (FormaPagamento.codigo_sefaz == None) | (FormaPagamento.codigo_sefaz == ""),  # noqa: E711
        )
        .all()
    )
    assert sem_codigo == [], [f.nome for f in sem_codigo]
