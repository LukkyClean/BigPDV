# ---------------------------------------------------------------------------
# ARQUIVO: services/relatorio.py
# DESCRICAO: Regras do modulo de Relatorios. Monta o relatorio de faturamento
#            reusando as agregacoes do dashboard e a serie por dia do crud proprio.
# ---------------------------------------------------------------------------

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.db.crud import dashboard as dashboard_crud
from app.db.crud import relatorio as relatorio_crud
from app.schemas.relatorio import (
    RelatorioFaturamento,
    FaturamentoDiaItem,
    FormaPagamentoResumo,
    RelatorioRanking,
    RankingFuncionarioItem,
)


def get_faturamento(db: Session, inicio: date, fim: date, empresa_id: int) -> RelatorioFaturamento:
    """
    Faturamento (vendas + OS finalizadas) no intervalo [inicio, fim]:
    KPIs, serie por dia e formas de pagamento.

    Os KPIs reusam get_stats_agregados (mesma base do dashboard), entao a soma da
    serie por dia bate com o faturamento_total.
    """
    dt_inicio = datetime.combine(inicio, datetime.min.time())
    dt_fim = datetime.combine(fim, datetime.max.time())

    stats = dashboard_crud.get_stats_agregados(db, dt_inicio, dt_fim, empresa_id)
    faturamento_vendas = stats.vendas_total
    faturamento_os = stats.os_soma
    faturamento_total = faturamento_vendas + faturamento_os
    qtd_transacoes = stats.vendas_count + stats.os_finalizadas_count
    ticket_medio = int(faturamento_total / qtd_transacoes) if qtd_transacoes else 0

    # Serie por dia — preenche dias sem movimento com zero para o grafico ficar continuo.
    vendas_dia = {
        str(r.dia): (r.total or 0)
        for r in relatorio_crud.get_faturamento_vendas_por_dia(db, dt_inicio, dt_fim, empresa_id)
    }
    os_dia = {
        str(r.dia): (r.total or 0)
        for r in relatorio_crud.get_faturamento_os_por_dia(db, dt_inicio, dt_fim, empresa_id)
    }

    por_dia: list[FaturamentoDiaItem] = []
    dia = inicio
    while dia <= fim:
        chave = dia.isoformat()
        tv = vendas_dia.get(chave, 0)
        to = os_dia.get(chave, 0)
        por_dia.append(
            FaturamentoDiaItem(dia=dia, total_vendas=tv, total_os=to, total_geral=tv + to)
        )
        dia += timedelta(days=1)

    # Formas de pagamento — reusa o crud do dashboard e mescla vendas + OS.
    totais: dict[str, int] = {}
    for r in dashboard_crud.get_formas_pagamento_vendas(db, dt_inicio, dt_fim, empresa_id):
        totais[r.nome] = totais.get(r.nome, 0) + (r.total or 0)
    for r in dashboard_crud.get_formas_pagamento_os(db, dt_inicio, dt_fim, empresa_id):
        totais[r.nome] = totais.get(r.nome, 0) + (r.total or 0)
    formas = [
        FormaPagamentoResumo(nome=nome, valor_total=valor)
        for nome, valor in sorted(totais.items(), key=lambda x: x[1], reverse=True)
    ]

    return RelatorioFaturamento(
        inicio=inicio,
        fim=fim,
        faturamento_total=faturamento_total,
        faturamento_vendas=faturamento_vendas,
        faturamento_os=faturamento_os,
        ticket_medio=ticket_medio,
        qtd_vendas=stats.vendas_count,
        qtd_os=stats.os_finalizadas_count,
        por_dia=por_dia,
        formas_pagamento=formas,
    )


def get_ranking(db: Session, inicio: date, fim: date, empresa_id: int) -> RelatorioRanking:
    """Ranking de funcionarios por faturamento (vendas + OS finalizadas) no periodo.

    Só entram funcionarios que faturaram algo (total > 0), ja ordenados desc pelo crud.
    """
    dt_inicio = datetime.combine(inicio, datetime.min.time())
    dt_fim = datetime.combine(fim, datetime.max.time())

    rows = relatorio_crud.get_ranking_faturamento(db, dt_inicio, dt_fim, empresa_id)
    itens: list[RankingFuncionarioItem] = []
    for r in rows:
        vendas = r.vendas_valor or 0
        os = r.os_valor or 0
        total = vendas + os
        if total <= 0:
            continue
        itens.append(
            RankingFuncionarioItem(
                funcionario_id=r.id,
                nome=r.nome,
                faturamento_vendas=vendas,
                faturamento_os=os,
                faturamento_total=total,
                qtd_vendas=r.vendas_qtd or 0,
                qtd_os=r.os_qtd or 0,
            )
        )

    return RelatorioRanking(inicio=inicio, fim=fim, itens=itens)
