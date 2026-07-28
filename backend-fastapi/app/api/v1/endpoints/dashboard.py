# ---------------------------------------------------------------------------
# ARQUIVO: endpoints/dashboard.py
# DESCRICAO: Endpoints read-only para o Dashboard.
#
# SEPARACAO DE ACESSO (regra do dono):
#   - VISAO GERAL da loja (stats, ranking, os-por-status, formas-pagamento,
#     os-atrasadas-empresa, estoque-baixo, os-vencendo, ultimas-vendas) e
#     EXCLUSIVA do Master -> Depends(get_current_master_user) (403 se nao for).
#   - Endpoints PESSOAIS (meu-resumo, minha-fila, minhas-*, os-aguardando-retirada,
#     minha-atividade-hoje) ficam com get_current_active_user e filtram pelo
#     funcionario_id do proprio token. Periodo limitado a hoje|semana|mes (teto 1 mes).
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.depends import get_current_active_user, get_current_master_user, get_db
from app.schemas.dashboard import (
    DashboardStats,
    TendenciaResponse,
    OSVencendoResponse,
    EstoqueBaixoResponse,
    UltimasVendasResponse,
    MeuResumoStats,
    MinhaFilaResponse,
    OSAtrasadaResponse,
    OSAguardandoRetiradaResponse,
    AtividadeHojeResponse,
    RankingFuncionariosResponse,
    OSPorStatusResponse,
    FormasPagamentoResponse,
    OSAtrasadaEmpresaResponse,
)
from app.services import dashboard as dashboard_service

router = APIRouter()


@router.get(
    "/stats",
    response_model=DashboardStats,
    summary="Metricas do Dashboard",
    description="Retorna vendas totais, OS criadas, novos clientes e ticket medio com variacao percentual.",
)
def obter_stats(
    user_token: dict = Depends(get_current_master_user),
    *,
    db: Session = Depends(get_db),
    periodo: str = Query("hoje", pattern="^(hoje|semana|mes)$", description="Periodo de filtragem"),
):
    return dashboard_service.get_dashboard_stats(db, periodo, user_token["empresa_id"])


@router.get(
    "/tendencia",
    response_model=TendenciaResponse,
    summary="Tendencia de faturamento da loja (serie diaria)",
    description="Faturamento (vendas + OS finalizadas) por dia no periodo. Visao geral — Master.",
)
def obter_tendencia(
    user_token: dict = Depends(get_current_master_user),
    *,
    db: Session = Depends(get_db),
    periodo: str = Query("hoje", pattern="^(hoje|semana|mes)$", description="Periodo de filtragem"),
):
    return dashboard_service.get_tendencia(db, periodo, user_token["empresa_id"])


@router.get(
    "/os-vencendo",
    response_model=OSVencendoResponse,
    summary="OS Proximas do Prazo",
    description="Retorna ordens de servico ativas ordenadas por urgencia de prazo.",
)
def obter_os_vencendo(
    user_token: dict = Depends(get_current_master_user),
    *,
    db: Session = Depends(get_db),
):
    return dashboard_service.get_os_vencendo(db, user_token["empresa_id"])


@router.get(
    "/estoque-baixo",
    response_model=EstoqueBaixoResponse,
    summary="Produtos com Estoque Critico",
    description="Retorna produtos com estoque zerado ou abaixo da quantidade minima.",
)
def obter_estoque_baixo(
    user_token: dict = Depends(get_current_master_user),
    *,
    db: Session = Depends(get_db),
):
    return dashboard_service.get_estoque_baixo(db)


@router.get(
    "/meu-resumo",
    response_model=MeuResumoStats,
    summary="Resumo pessoal do funcionario",
    description="Retorna as metricas do periodo filtradas pelo funcionario logado.",
)
def obter_meu_resumo(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
    periodo: str = Query("hoje", pattern="^(hoje|semana|mes)$"),
):
    funcionario_id = user_token.get("funcionario_id")
    if not funcionario_id:
        return MeuResumoStats()
    return dashboard_service.get_meu_resumo(db, periodo, funcionario_id)


@router.get(
    "/minha-tendencia",
    response_model=TendenciaResponse,
    summary="Minha tendencia de faturamento (serie diaria pessoal)",
    description="Faturamento (minhas vendas + minhas OS finalizadas) por dia no periodo.",
)
def obter_minha_tendencia(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
    periodo: str = Query("hoje", pattern="^(hoje|semana|mes)$"),
):
    funcionario_id = user_token.get("funcionario_id")
    if not funcionario_id:
        return TendenciaResponse()
    return dashboard_service.get_minha_tendencia(db, periodo, funcionario_id)


@router.get(
    "/minhas-os-vencendo",
    response_model=OSVencendoResponse,
    summary="OS do funcionario proximas do prazo",
)
def obter_minhas_os_vencendo(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
):
    funcionario_id = user_token.get("funcionario_id")
    if not funcionario_id:
        return OSVencendoResponse(items=[])
    return dashboard_service.get_minhas_os_vencendo(db, funcionario_id)


@router.get(
    "/minhas-ultimas-vendas",
    response_model=UltimasVendasResponse,
    summary="Ultimas vendas do funcionario logado",
)
def obter_minhas_ultimas_vendas(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
):
    funcionario_id = user_token.get("funcionario_id")
    if not funcionario_id:
        return UltimasVendasResponse(items=[])
    return dashboard_service.get_minhas_ultimas_vendas(db, funcionario_id)


@router.get("/minha-fila", response_model=MinhaFilaResponse, summary="Fila de trabalho do funcionario")
def obter_minha_fila(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
):
    funcionario_id = user_token.get("funcionario_id")
    if not funcionario_id:
        return MinhaFilaResponse()
    return dashboard_service.get_minha_fila(db, funcionario_id)


@router.get("/minhas-os-atrasadas", response_model=OSAtrasadaResponse, summary="OS com prazo vencido do funcionario")
def obter_minhas_os_atrasadas(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
):
    funcionario_id = user_token.get("funcionario_id")
    if not funcionario_id:
        return OSAtrasadaResponse()
    return dashboard_service.get_minhas_os_atrasadas(db, funcionario_id)


@router.get("/os-aguardando-retirada", response_model=OSAguardandoRetiradaResponse, summary="OS prontas para retirada")
def obter_os_aguardando_retirada(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
):
    funcionario_id = user_token.get("funcionario_id")
    if not funcionario_id:
        return OSAguardandoRetiradaResponse()
    return dashboard_service.get_os_aguardando_retirada(db, funcionario_id)


@router.get("/minha-atividade-hoje", response_model=AtividadeHojeResponse, summary="Timeline de atividades do funcionario hoje")
def obter_minha_atividade_hoje(
    user_token: dict = Depends(get_current_active_user),
    *,
    db: Session = Depends(get_db),
):
    funcionario_id = user_token.get("funcionario_id")
    if not funcionario_id:
        return AtividadeHojeResponse()
    return dashboard_service.get_minha_atividade_hoje(db, funcionario_id)


@router.get(
    "/ranking-funcionarios",
    response_model=RankingFuncionariosResponse,
    summary="Ranking de funcionarios por desempenho",
)
def obter_ranking_funcionarios(
    user_token: dict = Depends(get_current_master_user),
    *,
    db: Session = Depends(get_db),
    periodo: str = Query("mes", pattern="^(hoje|semana|mes)$"),
):
    return dashboard_service.get_ranking_funcionarios(db, periodo, user_token["empresa_id"])


@router.get(
    "/os-por-status",
    response_model=OSPorStatusResponse,
    summary="Contagem de OS agrupadas por status",
)
def obter_os_por_status(
    user_token: dict = Depends(get_current_master_user),
    *,
    db: Session = Depends(get_db),
):
    return dashboard_service.get_os_por_status(db, user_token["empresa_id"])


@router.get(
    "/formas-pagamento",
    response_model=FormasPagamentoResponse,
    summary="Total por forma de pagamento no periodo",
)
def obter_formas_pagamento(
    user_token: dict = Depends(get_current_master_user),
    *,
    db: Session = Depends(get_db),
    periodo: str = Query("mes", pattern="^(hoje|semana|mes)$"),
):
    return dashboard_service.get_formas_pagamento(db, periodo, user_token["empresa_id"])


@router.get(
    "/os-atrasadas-empresa",
    response_model=OSAtrasadaEmpresaResponse,
    summary="OS com prazo vencido em toda a empresa",
)
def obter_os_atrasadas_empresa(
    user_token: dict = Depends(get_current_master_user),
    *,
    db: Session = Depends(get_db),
):
    return dashboard_service.get_os_atrasadas_empresa(db, user_token["empresa_id"])


@router.get(
    "/ultimas-vendas",
    response_model=UltimasVendasResponse,
    summary="Vendas Recentes",
    description="Retorna as ultimas vendas e orcamentos realizados.",
)
def obter_ultimas_vendas(
    user_token: dict = Depends(get_current_master_user),
    *,
    db: Session = Depends(get_db),
):
    return dashboard_service.get_ultimas_vendas(db, user_token["empresa_id"])
