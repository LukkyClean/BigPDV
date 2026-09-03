# ---------------------------------------------------------------------------
# ARQUIVO: test/api/v1/test_relatorio_fuso.py
# DESCRIÇÃO: Regressão do defeito de fuso na apuração por período.
#
# Aqui a venda é gravada com carimbo dentro da janela crítica (21h-24h local,
# que o banco grava no dia UTC seguinte) e o relatório é consultado pelo dia
# LOCAL. Antes da correção o resultado vinha zerado.
# ---------------------------------------------------------------------------

from datetime import date, datetime, timedelta

import pytest

from app.core.tempo import intervalo_utc
from app.db.models.venda import Venda
from test.api.v1.test_custo_estoque import (
    _auth, _forma_pagamento, _funcionario, _produto,
    _seed_contador_venda, _venda_finalizada,
)


def _faturamento(client, header, dia):
    r = client.get("/api/v1/relatorios/faturamento",
                   params={"inicio": dia.isoformat(), "fim": dia.isoformat()},
                   headers=header)
    assert r.status_code == 200, r.text
    return r.json()


def test_venda_da_noite_aparece_no_relatorio_do_dia(client, db_session):
    """
    Simula o cenário real: venda feita às 21h30 no horário da loja, cujo
    carimbo no banco cai no dia seguinte em UTC.
    """
    _seed_contador_venda(db_session)
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma_pagamento(client, header)
    produto_id = _produto(client, header, "P-NOITE", varejo=15000,
                          entrada=4000, quantidade=10)

    venda_id, _ = _venda_finalizada(client, header, funcionario_id, produto_id, 2, fp_id)

    # Reposiciona o carimbo para o último instante do dia local — o mesmo lugar
    # onde o banco grava uma venda das 21h30 em UTC-3.
    hoje = date.today()
    _, fim_utc = intervalo_utc(hoje, hoje)
    venda = db_session.query(Venda).filter(Venda.id == venda_id).first()
    venda.criado_em = fim_utc - timedelta(minutes=1)
    db_session.commit()

    relatorio = _faturamento(client, header, hoje)

    assert relatorio["cmv"] == 8000, "a venda da noite precisa entrar na apuração do dia"
    assert relatorio["faturamento_total"] > 0


def test_venda_do_dia_seguinte_nao_entra_no_relatorio_de_hoje(client, db_session):
    """A conversão não pode alargar o intervalo e capturar o dia seguinte."""
    _seed_contador_venda(db_session)
    header = _auth(client)
    funcionario_id = _funcionario(client, header)
    fp_id = _forma_pagamento(client, header)
    produto_id = _produto(client, header, "P-AMANHA", varejo=15000,
                          entrada=4000, quantidade=10)

    venda_id, _ = _venda_finalizada(client, header, funcionario_id, produto_id, 2, fp_id)

    hoje = date.today()
    _, fim_utc = intervalo_utc(hoje, hoje)
    venda = db_session.query(Venda).filter(Venda.id == venda_id).first()
    venda.criado_em = fim_utc + timedelta(minutes=1)   # já é amanhã, no local
    db_session.commit()

    relatorio = _faturamento(client, header, hoje)

    assert relatorio["faturamento_total"] == 0
