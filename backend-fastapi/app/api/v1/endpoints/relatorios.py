# ---------------------------------------------------------------------------
# ARQUIVO: endpoints/relatorios.py
# DESCRICAO: Endpoints read-only do modulo de Relatorios. Dados sensiveis
#            (faturamento) — protegidos por permissao no backend.
# ---------------------------------------------------------------------------

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.depends import check_permission, get_db
from app.schemas.relatorio import (
    RelatorioFaturamento,
    RelatorioRanking,
    RelatorioComissao,
    RelatorioEstoque,
    RelatorioOSPerformance,
)
from app.services import relatorio as relatorio_service

router = APIRouter()

# Master e cargos com "all" ja furam a checagem; os demais precisam desta permissao.
module_permission = ["relatorio", "view_reports", "manage_reports"]


@router.get(
    "/faturamento",
    response_model=RelatorioFaturamento,
    summary="Relatorio de faturamento por periodo",
    description=(
        "Faturamento (vendas + OS finalizadas) por dia, KPIs (total, ticket medio, "
        "quantidades) e distribuicao por forma de pagamento no intervalo informado."
    ),
)
def obter_faturamento(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    db: Session = Depends(get_db),
    inicio: date = Query(..., description="Data inicial do periodo (YYYY-MM-DD)"),
    fim: date = Query(..., description="Data final do periodo (YYYY-MM-DD)"),
):
    return relatorio_service.get_faturamento(db, inicio, fim, user_token["empresa_id"])


@router.get(
    "/ranking-funcionarios",
    response_model=RelatorioRanking,
    summary="Ranking de funcionarios por faturamento",
    description=(
        "Faturamento (vendas + OS finalizadas) por funcionario no periodo, ordenado "
        "do maior para o menor. Base do futuro relatorio de comissao."
    ),
)
def obter_ranking_funcionarios(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    db: Session = Depends(get_db),
    inicio: date = Query(..., description="Data inicial do periodo (YYYY-MM-DD)"),
    fim: date = Query(..., description="Data final do periodo (YYYY-MM-DD)"),
):
    return relatorio_service.get_ranking(db, inicio, fim, user_token["empresa_id"])


@router.get(
    "/comissoes",
    response_model=RelatorioComissao,
    summary="Relatorio de comissao por funcionario",
    description=(
        "Comissao apurada por funcionario no periodo: base liquida (vendas + OS "
        "finalizadas), taxa resolvida pela cascata funcionario -> cargo, e total a pagar."
    ),
)
def obter_comissoes(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    db: Session = Depends(get_db),
    inicio: date = Query(..., description="Data inicial do periodo (YYYY-MM-DD)"),
    fim: date = Query(..., description="Data final do periodo (YYYY-MM-DD)"),
):
    return relatorio_service.get_comissao(db, inicio, fim, user_token["empresa_id"])


@router.get(
    "/estoque",
    response_model=RelatorioEstoque,
    summary="Relatorio de estoque e Curva ABC",
    description=(
        "Curva ABC dos produtos por faturamento no periodo (A<=80%, B<=95%, C o resto), "
        "KPIs de valor imobilizado (posicao atual), lista de reposicao (abaixo do minimo) "
        "e produtos parados (ativos sem venda no periodo)."
    ),
)
def obter_estoque(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    db: Session = Depends(get_db),
    inicio: date = Query(..., description="Data inicial do periodo (YYYY-MM-DD)"),
    fim: date = Query(..., description="Data final do periodo (YYYY-MM-DD)"),
):
    return relatorio_service.get_estoque(db, inicio, fim, user_token["empresa_id"])


@router.get(
    "/os-performance",
    response_model=RelatorioOSPerformance,
    summary="Relatorio de desempenho de OS",
    description=(
        "Desempenho de ordens de servico no periodo: throughput (abertas x finalizadas), "
        "tempo medio de conclusao, taxa de reparo (desfecho) e desempenho por tecnico, "
        "alem do snapshot do backlog por status atual."
    ),
)
def obter_os_performance(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    db: Session = Depends(get_db),
    inicio: date = Query(..., description="Data inicial do periodo (YYYY-MM-DD)"),
    fim: date = Query(..., description="Data final do periodo (YYYY-MM-DD)"),
):
    return relatorio_service.get_os_performance(db, inicio, fim, user_token["empresa_id"])
