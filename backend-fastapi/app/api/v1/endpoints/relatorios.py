# ---------------------------------------------------------------------------
# ARQUIVO: endpoints/relatorios.py
# DESCRICAO: Endpoints read-only do modulo de Relatorios. Dados sensiveis
#            (faturamento) — protegidos por permissao no backend.
# ---------------------------------------------------------------------------

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.depends import check_permission, get_db
from app.schemas.relatorio import RelatorioFaturamento
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
