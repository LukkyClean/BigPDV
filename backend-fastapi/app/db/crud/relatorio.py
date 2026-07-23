# ---------------------------------------------------------------------------
# ARQUIVO: crud/relatorio.py
# DESCRICAO: Queries agregadas do modulo de Relatorios. Apenas leitura.
#            As metricas consolidadas (totais, ticket, formas de pagamento)
#            reusam crud/dashboard.py; aqui ficam as series temporais (por dia).
#
# Convencao de data: timestamps sao gravados em UTC (func.now()); os filtros
# de periodo usam limites UTC, iguais aos do dashboard, para bater com ele.
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import Sequence

from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_

from app.db.models.venda import Venda
from app.db.models.ordem_servico import OrdemServico as OSModel
from app.db.models.funcionario import Funcionario
from app.core.enum import VendaStatus, OrdemServicoStatus


def get_faturamento_vendas_por_dia(
    db: Session, data_inicio: datetime, data_fim: datetime, empresa_id: int
) -> Sequence:
    """Soma das vendas finalizadas agrupada por dia (func.date), da empresa."""
    stmt = (
        select(
            func.date(Venda.criado_em).label("dia"),
            func.coalesce(func.sum(Venda.total), 0).label("total"),
        )
        .join(Funcionario, Funcionario.id == Venda.funcionario_id)
        .where(
            and_(
                Venda.status == VendaStatus.FINALIZADA,
                Venda.criado_em >= data_inicio,
                Venda.criado_em <= data_fim,
                Funcionario.empresa_id == empresa_id,
            )
        )
        .group_by(func.date(Venda.criado_em))
    )
    return db.execute(stmt).all()


def get_faturamento_os_por_dia(
    db: Session, data_inicio: datetime, data_fim: datetime, empresa_id: int
) -> Sequence:
    """Soma das OS finalizadas agrupada por dia (func.date), da empresa.

    Usa data_criacao para bater com o get_stats_agregados do dashboard (que soma
    valor_total das OS finalizadas cujo data_criacao cai no periodo).
    """
    stmt = (
        select(
            func.date(OSModel.data_criacao).label("dia"),
            func.coalesce(func.sum(OSModel.valor_total), 0).label("total"),
        )
        .outerjoin(Funcionario, Funcionario.id == OSModel.funcionario_id)
        .where(
            and_(
                OSModel.status == OrdemServicoStatus.FINALIZADA,
                OSModel.data_criacao >= data_inicio,
                OSModel.data_criacao <= data_fim,
                or_(
                    Funcionario.empresa_id == empresa_id,
                    OSModel.funcionario_id.is_(None),
                ),
            )
        )
        .group_by(func.date(OSModel.data_criacao))
    )
    return db.execute(stmt).all()
