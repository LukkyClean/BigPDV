# ---------------------------------------------------------------------------
# ARQUIVO: endpoints/relatorios.py
# DESCRICAO: Endpoints read-only do modulo de Relatorios.
#
# SEPARACAO DE ACESSO (regra do dono) — a MESMA do endpoints/dashboard.py:
#   - VISAO GERAL da loja (ranking, comissoes, estoque, os-performance) e
#     EXCLUSIVA do Master -> Depends(get_current_master_user), 403 se nao for.
#     Ranking e comissao expoem o desempenho e o pagamento dos COLEGAS; estoque
#     e curva ABC expoem custo e imobilizado; desempenho de OS compara tecnicos.
#     Nada disso e do funcionario — e do dono.
#   - /faturamento continua aberto a quem tem a permissao do modulo, mas RECORTADO:
#     master recebe a loja inteira, funcionario recebe so o que ele mesmo fez
#     (get_faturamento_pessoal), sem juros, custo, lucro nem formas de pagamento.
#
# O gate e o `is_master`, nao o nome do cargo. Mesma decisao do HomeView e do
# dashboard: cargo por nome ("gerente"/"administrador") e fragil e ja divergiu
# do servidor uma vez.
# ---------------------------------------------------------------------------

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.depends import check_permission, get_current_master_user, get_db
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
    """Master ve a loja; funcionario ve o que ele mesmo fez."""
    if user_token.get("is_master") is True:
        return relatorio_service.get_faturamento(db, inicio, fim, user_token["empresa_id"])

    funcionario_id = user_token.get("funcionario_id")
    if not funcionario_id:
        # Usuario sem ficha de funcionario nao tem "o que ele fez" para somar. O
        # relatorio vazio e a resposta certa — cair no relatorio da loja seria
        # justamente o vazamento que este recorte existe para fechar.
        return RelatorioFaturamento(
            inicio=inicio,
            fim=fim,
            faturamento_total=0,
            faturamento_vendas=0,
            faturamento_os=0,
            ticket_medio=0,
            qtd_vendas=0,
            qtd_os=0,
        )

    return relatorio_service.get_faturamento_pessoal(db, inicio, fim, funcionario_id)


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
    user_token: dict = Depends(get_current_master_user),
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
    user_token: dict = Depends(get_current_master_user),
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
    user_token: dict = Depends(get_current_master_user),
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
    user_token: dict = Depends(get_current_master_user),
    *,
    db: Session = Depends(get_db),
    inicio: date = Query(..., description="Data inicial do periodo (YYYY-MM-DD)"),
    fim: date = Query(..., description="Data final do periodo (YYYY-MM-DD)"),
):
    return relatorio_service.get_os_performance(db, inicio, fim, user_token["empresa_id"])
