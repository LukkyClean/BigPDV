# ---------------------------------------------------------------------------
# ARQUIVO: crud/dashboard.py
# DESCRICAO: Queries SQL via SQLAlchemy para o Dashboard.
#            Apenas leitura — sem efeito colateral no banco.
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import Sequence, NamedTuple

from sqlalchemy.orm import Session, aliased
from sqlalchemy import select, func, or_, and_, case, literal

from app.db.models.venda import Venda
from app.db.models.ordem_servico import OrdemServico as OSModel
from app.db.models.objeto_servico import ObjetoServico as OSEquipamentoModel
from app.db.models.cliente import Cliente, ClientePF, ClientePJ
from app.db.models.produto import Produto
from app.db.models.estoque import Estoque
from app.db.models.funcionario import Funcionario
from app.db.models.venda_pagamento import PagamentoVenda
from app.db.models.ordem_servico_pagamento import OrdemServicoPagamento
from app.db.models.forma_pagamento import FormaPagamento

from app.core.enum import VendaStatus, OrdemServicoStatus, OrdemServicoPrioridade


# ===========================================================================
# STATS — Metricas agregadas por periodo (query consolidada)
# ===========================================================================

class StatsAgregados(NamedTuple):
    vendas_total: int
    vendas_count: int
    os_count: int
    clientes_count: int
    os_soma: int
    os_finalizadas_count: int


def get_stats_agregados(
    db: Session,
    data_inicio: datetime,
    data_fim: datetime,
    empresa_id: int,
) -> StatsAgregados:
    """
    Retorna todas as metricas do dashboard em 3 queries (vendas, OS, clientes)
    em vez de 8 separadas. Filtra por empresa_id via Funcionario.
    """
    # Vendas: soma total + contagem (para ticket medio)
    vendas_stmt = select(
        func.coalesce(func.sum(Venda.total), 0).label("vendas_total"),
        func.count(Venda.id).label("vendas_count"),
    ).join(
        Funcionario, Funcionario.id == Venda.funcionario_id
    ).where(
        and_(
            Venda.status == VendaStatus.FINALIZADA,
            Venda.criado_em >= data_inicio,
            Venda.criado_em <= data_fim,
            Funcionario.empresa_id == empresa_id,
        )
    )
    vendas_result = db.execute(vendas_stmt).first()

    # OS: contagem total + soma/contagem finalizadas (para ticket medio)
    os_stmt = select(
        func.count(OSModel.id).label("os_count"),
        func.coalesce(
            func.sum(
                case((OSModel.status == OrdemServicoStatus.FINALIZADA, OSModel.valor_total), else_=0)
            ), 0
        ).label("os_soma"),
        func.sum(
            case((OSModel.status == OrdemServicoStatus.FINALIZADA, 1), else_=0)
        ).label("os_finalizadas_count"),
    ).outerjoin(
        Funcionario, Funcionario.id == OSModel.funcionario_id
    ).where(
        and_(
            OSModel.data_criacao >= data_inicio,
            OSModel.data_criacao <= data_fim,
            or_(
                Funcionario.empresa_id == empresa_id,
                OSModel.funcionario_id.is_(None),
            ),
        )
    )
    os_result = db.execute(os_stmt).first()

    # Clientes: sem empresa_id no modelo, contagem global
    clientes_stmt = select(func.count(Cliente.id)).where(
        and_(
            Cliente.data_criacao >= data_inicio,
            Cliente.data_criacao <= data_fim,
        )
    )
    clientes_count = db.scalar(clientes_stmt) or 0

    return StatsAgregados(
        vendas_total=vendas_result.vendas_total or 0,
        vendas_count=vendas_result.vendas_count or 0,
        os_count=os_result.os_count or 0,
        clientes_count=clientes_count,
        os_soma=os_result.os_soma or 0,
        os_finalizadas_count=os_result.os_finalizadas_count or 0,
    )


# ===========================================================================
# OS VENCENDO — Ordens proximas/passadas do prazo
# ===========================================================================

def get_os_vencendo(db: Session, empresa_id: int, limit: int = 10) -> Sequence:
    """
    OS ativas com data_previsao definida, ordenadas por urgencia (mais urgente primeiro).
    Filtra por empresa_id via Funcionario.
    """
    client_pf = aliased(ClientePF)
    client_pj = aliased(ClientePJ)

    stmt = (
        select(
            OSModel.numero_os,
            func.coalesce(client_pf.nome, client_pj.razao_social, literal("Sem cliente")).label("cliente_nome"),
            OSModel.defeito_relatado,
            OSModel.data_previsao,
        )
        .join(OSModel.objeto)
        .join(OSEquipamentoModel.cliente)
        .outerjoin(client_pf, Cliente.id == client_pf.id)
        .outerjoin(client_pj, Cliente.id == client_pj.id)
        .outerjoin(Funcionario, Funcionario.id == OSModel.funcionario_id)
        .where(
            and_(
                OSModel.data_previsao.isnot(None),
                OSModel.status.notin_([OrdemServicoStatus.FINALIZADA, OrdemServicoStatus.CANCELADA]),
                or_(
                    Funcionario.empresa_id == empresa_id,
                    OSModel.funcionario_id.is_(None),
                ),
            )
        )
        .order_by(OSModel.data_previsao.asc())
        .limit(limit)
    )

    return db.execute(stmt).all()


# ===========================================================================
# ESTOQUE BAIXO — Produtos que precisam de reposicao
# ===========================================================================

def get_estoque_baixo(db: Session, limit: int = 8) -> Sequence:
    """
    Produtos ativos com estoque zerado ou abaixo da quantidade minima.
    Zerados aparecem primeiro, depois ordenados pela diferenca (mais criticos primeiro).
    Nota: Produto nao possui empresa_id — retorna dados globais.
    """
    stmt = (
        select(
            Produto.id.label("produto_id"),
            Produto.nome,
            Estoque.quantidade,
            Estoque.quantidade_minima,
        )
        .join(Estoque, Estoque.id == Produto.id)
        .where(
            and_(
                Produto.ativo == True,
                or_(
                    Estoque.quantidade == 0,
                    and_(
                        Estoque.quantidade_minima.isnot(None),
                        Estoque.quantidade <= Estoque.quantidade_minima,
                    ),
                ),
            )
        )
        .order_by(
            Estoque.quantidade.asc(),
        )
        .limit(limit)
    )

    return db.execute(stmt).all()


# ===========================================================================
# MEU RESUMO — Stats pessoais do funcionario logado
# ===========================================================================

class MeuResumoAgregado(NamedTuple):
    minhas_vendas_valor: int
    minhas_vendas_count: int
    minhas_os_valor: int
    minhas_os_abertas: int
    minhas_os_concluidas: int


def get_meu_resumo_stats(
    db: Session,
    data_inicio: datetime,
    data_fim: datetime,
    funcionario_id: int,
) -> MeuResumoAgregado:
    """Stats pessoais do funcionario: vendas e OS filtradas pelo seu ID."""
    vendas_stmt = select(
        func.coalesce(func.sum(Venda.total), 0).label("vendas_valor"),
        func.count(Venda.id).label("vendas_count"),
    ).where(
        and_(
            Venda.status == VendaStatus.FINALIZADA,
            Venda.criado_em >= data_inicio,
            Venda.criado_em <= data_fim,
            Venda.funcionario_id == funcionario_id,
        )
    )
    vendas_result = db.execute(vendas_stmt).first()

    os_stmt = select(
        func.sum(case((OSModel.status.notin_([OrdemServicoStatus.FINALIZADA, OrdemServicoStatus.CANCELADA]), 1), else_=0)).label("os_abertas"),
        func.sum(case((OSModel.status == OrdemServicoStatus.FINALIZADA, 1), else_=0)).label("os_concluidas"),
        func.coalesce(
            func.sum(case((OSModel.status == OrdemServicoStatus.FINALIZADA, OSModel.valor_total), else_=0)), 0
        ).label("os_valor"),
    ).where(
        and_(
            OSModel.data_criacao >= data_inicio,
            OSModel.data_criacao <= data_fim,
            OSModel.funcionario_id == funcionario_id,
            OSModel.ativo == True,
        )
    )
    os_result = db.execute(os_stmt).first()

    return MeuResumoAgregado(
        minhas_vendas_valor=vendas_result.vendas_valor or 0,
        minhas_vendas_count=vendas_result.vendas_count or 0,
        minhas_os_valor=os_result.os_valor or 0,
        minhas_os_abertas=os_result.os_abertas or 0,
        minhas_os_concluidas=os_result.os_concluidas or 0,
    )


def get_minhas_vendas_por_dia(
    db: Session, data_inicio: datetime, data_fim: datetime, funcionario_id: int
) -> Sequence:
    """Soma das vendas finalizadas do funcionario, agrupada por dia (serie de tendencia pessoal)."""
    stmt = (
        select(
            func.date(Venda.criado_em).label("dia"),
            func.coalesce(func.sum(Venda.total), 0).label("total"),
        )
        .where(
            and_(
                Venda.status == VendaStatus.FINALIZADA,
                Venda.criado_em >= data_inicio,
                Venda.criado_em <= data_fim,
                Venda.funcionario_id == funcionario_id,
            )
        )
        .group_by(func.date(Venda.criado_em))
    )
    return db.execute(stmt).all()


def get_minhas_os_por_dia(
    db: Session, data_inicio: datetime, data_fim: datetime, funcionario_id: int
) -> Sequence:
    """Soma das OS finalizadas do funcionario, agrupada por dia (serie de tendencia pessoal)."""
    stmt = (
        select(
            func.date(OSModel.data_criacao).label("dia"),
            func.coalesce(func.sum(OSModel.valor_total), 0).label("total"),
        )
        .where(
            and_(
                OSModel.status == OrdemServicoStatus.FINALIZADA,
                OSModel.data_criacao >= data_inicio,
                OSModel.data_criacao <= data_fim,
                OSModel.funcionario_id == funcionario_id,
            )
        )
        .group_by(func.date(OSModel.data_criacao))
    )
    return db.execute(stmt).all()


def get_minhas_os_vencendo(db: Session, funcionario_id: int, limit: int = 10):
    """OS do funcionario proximas/passadas do prazo."""
    client_pf = aliased(ClientePF)
    client_pj = aliased(ClientePJ)

    stmt = (
        select(
            OSModel.numero_os,
            func.coalesce(client_pf.nome, client_pj.razao_social, literal("Sem cliente")).label("cliente_nome"),
            OSModel.defeito_relatado,
            OSModel.data_previsao,
        )
        .join(OSModel.objeto)
        .join(OSEquipamentoModel.cliente)
        .outerjoin(client_pf, Cliente.id == client_pf.id)
        .outerjoin(client_pj, Cliente.id == client_pj.id)
        .where(
            and_(
                OSModel.data_previsao.isnot(None),
                OSModel.status.notin_([OrdemServicoStatus.FINALIZADA, OrdemServicoStatus.CANCELADA]),
                OSModel.funcionario_id == funcionario_id,
            )
        )
        .order_by(OSModel.data_previsao.asc())
        .limit(limit)
    )
    return db.execute(stmt).all()


def get_minha_fila(db: Session, funcionario_id: int, limit: int = 20):
    """OS abertas do funcionario ordenadas por prioridade (URGENTE→BAIXA) e prazo."""
    client_pf = aliased(ClientePF)
    client_pj = aliased(ClientePJ)

    prioridade_order = case(
        (OSModel.prioridade == OrdemServicoPrioridade.URGENTE, 1),
        (OSModel.prioridade == OrdemServicoPrioridade.ALTA, 2),
        (OSModel.prioridade == OrdemServicoPrioridade.NORMAL, 3),
        (OSModel.prioridade == OrdemServicoPrioridade.BAIXA, 4),
        else_=5,
    )

    stmt = (
        select(
            OSModel.numero_os,
            func.coalesce(client_pf.nome, client_pj.razao_social, literal("Sem cliente")).label("cliente_nome"),
            OSModel.defeito_relatado,
            OSModel.prioridade,
            OSModel.status,
            OSModel.data_previsao,
        )
        .join(OSModel.objeto)
        .join(OSEquipamentoModel.cliente)
        .outerjoin(client_pf, Cliente.id == client_pf.id)
        .outerjoin(client_pj, Cliente.id == client_pj.id)
        .where(
            and_(
                OSModel.funcionario_id == funcionario_id,
                OSModel.status.notin_([
                    OrdemServicoStatus.FINALIZADA,
                    OrdemServicoStatus.CANCELADA,
                    OrdemServicoStatus.AGUARDANDO_RETIRADA,
                ]),
                OSModel.ativo == True,
            )
        )
        .order_by(prioridade_order.asc(), OSModel.data_previsao.asc())
        .limit(limit)
    )
    return db.execute(stmt).all()


def get_minhas_os_atrasadas(db: Session, funcionario_id: int, limit: int = 10):
    """OS com data_previsao anterior a hoje (atrasadas)."""
    client_pf = aliased(ClientePF)
    client_pj = aliased(ClientePJ)
    hoje_inicio = datetime.combine(datetime.utcnow().date(), datetime.min.time())

    stmt = (
        select(
            OSModel.numero_os,
            func.coalesce(client_pf.nome, client_pj.razao_social, literal("Sem cliente")).label("cliente_nome"),
            OSModel.defeito_relatado,
            OSModel.data_previsao,
        )
        .join(OSModel.objeto)
        .join(OSEquipamentoModel.cliente)
        .outerjoin(client_pf, Cliente.id == client_pf.id)
        .outerjoin(client_pj, Cliente.id == client_pj.id)
        .where(
            and_(
                OSModel.funcionario_id == funcionario_id,
                OSModel.data_previsao < hoje_inicio,
                OSModel.status.notin_([OrdemServicoStatus.FINALIZADA, OrdemServicoStatus.CANCELADA]),
                OSModel.ativo == True,
            )
        )
        .order_by(OSModel.data_previsao.asc())
        .limit(limit)
    )
    return db.execute(stmt).all()


def get_os_aguardando_retirada(db: Session, funcionario_id: int, limit: int = 10):
    """OS com status AGUARDANDO_RETIRADA do funcionario."""
    client_pf = aliased(ClientePF)
    client_pj = aliased(ClientePJ)

    stmt = (
        select(
            OSModel,
            func.coalesce(client_pf.nome, client_pj.razao_social, literal("Sem cliente")).label("cliente_nome"),
        )
        .join(OSModel.objeto)
        .join(OSEquipamentoModel.cliente)
        .outerjoin(client_pf, Cliente.id == client_pf.id)
        .outerjoin(client_pj, Cliente.id == client_pj.id)
        .where(
            and_(
                OSModel.funcionario_id == funcionario_id,
                OSModel.status == OrdemServicoStatus.AGUARDANDO_RETIRADA,
                OSModel.ativo == True,
            )
        )
        .order_by(OSModel.data_finalizacao.asc())
        .limit(limit)
    )
    return db.execute(stmt).all()


def get_minhas_vendas_hoje(db: Session, funcionario_id: int):
    """Vendas do funcionario criadas hoje."""
    client_pf = aliased(ClientePF)
    client_pj = aliased(ClientePJ)
    hoje_inicio = datetime.combine(datetime.utcnow().date(), datetime.min.time())

    stmt = (
        select(
            Venda.id,
            func.coalesce(client_pf.nome, client_pj.razao_social).label("cliente_nome"),
            Venda.total,
            Venda.status,
            Venda.criado_em,
        )
        .outerjoin(Venda.cliente)
        .outerjoin(client_pf, Cliente.id == client_pf.id)
        .outerjoin(client_pj, Cliente.id == client_pj.id)
        .where(
            and_(
                Venda.funcionario_id == funcionario_id,
                Venda.criado_em >= hoje_inicio,
                Venda.status.in_([VendaStatus.ATIVA, VendaStatus.FINALIZADA]),
            )
        )
        .order_by(Venda.criado_em.desc())
    )
    return db.execute(stmt).all()


def get_minhas_os_hoje(db: Session, funcionario_id: int):
    """OS do funcionario criadas hoje."""
    client_pf = aliased(ClientePF)
    client_pj = aliased(ClientePJ)
    hoje_inicio = datetime.combine(datetime.utcnow().date(), datetime.min.time())

    stmt = (
        select(
            OSModel.numero_os,
            func.coalesce(client_pf.nome, client_pj.razao_social, literal("Sem cliente")).label("cliente_nome"),
            OSModel.valor_total,
            OSModel.status,
            OSModel.data_criacao,
        )
        .join(OSModel.objeto)
        .join(OSEquipamentoModel.cliente)
        .outerjoin(client_pf, Cliente.id == client_pf.id)
        .outerjoin(client_pj, Cliente.id == client_pj.id)
        .where(
            and_(
                OSModel.funcionario_id == funcionario_id,
                OSModel.data_criacao >= hoje_inicio,
                OSModel.ativo == True,
            )
        )
        .order_by(OSModel.data_criacao.desc())
    )
    return db.execute(stmt).all()


def get_minhas_ultimas_vendas(db: Session, funcionario_id: int, limit: int = 5):
    """Ultimas vendas do funcionario logado."""
    client_pf = aliased(ClientePF)
    client_pj = aliased(ClientePJ)

    stmt = (
        select(
            Venda.id,
            func.coalesce(client_pf.nome, client_pj.razao_social).label("cliente_nome"),
            Venda.total,
            Venda.status,
            Venda.criado_em,
        )
        .outerjoin(Venda.cliente)
        .outerjoin(client_pf, Cliente.id == client_pf.id)
        .outerjoin(client_pj, Cliente.id == client_pj.id)
        .where(
            and_(
                Venda.status.in_([VendaStatus.FINALIZADA, VendaStatus.ATIVA]),
                Venda.funcionario_id == funcionario_id,
            )
        )
        .order_by(Venda.criado_em.desc())
        .limit(limit)
    )
    return db.execute(stmt).all()


# ===========================================================================
# MASTER — Ranking de funcionarios
# ===========================================================================

def get_ranking_funcionarios(
    db: Session,
    data_inicio: datetime,
    data_fim: datetime,
    empresa_id: int,
    limit: int = 10,
) -> Sequence:
    """Ranking de funcionarios por valor de vendas finalizadas no periodo."""
    vendas_sub = (
        select(
            Venda.funcionario_id,
            func.coalesce(func.sum(Venda.total), 0).label("total_vendas"),
            func.count(Venda.id).label("qtd_vendas"),
        )
        .where(and_(
            Venda.status == VendaStatus.FINALIZADA,
            Venda.criado_em >= data_inicio,
            Venda.criado_em <= data_fim,
        ))
        .group_by(Venda.funcionario_id)
        .subquery()
    )

    os_sub = (
        select(
            OSModel.funcionario_id,
            func.count(OSModel.id).label("qtd_os"),
            func.coalesce(func.sum(OSModel.valor_total), 0).label("os_valor"),
        )
        .where(and_(
            OSModel.status == OrdemServicoStatus.FINALIZADA,
            OSModel.data_criacao >= data_inicio,
            OSModel.data_criacao <= data_fim,
        ))
        .group_by(OSModel.funcionario_id)
        .subquery()
    )

    total_vendas = func.coalesce(vendas_sub.c.total_vendas, 0)
    total_os = func.coalesce(os_sub.c.os_valor, 0)

    stmt = (
        select(
            Funcionario.id,
            Funcionario.nome,
            total_vendas.label("total_vendas_valor"),
            func.coalesce(vendas_sub.c.qtd_vendas, 0).label("qtd_vendas"),
            total_os.label("total_os_valor"),
            func.coalesce(os_sub.c.qtd_os, 0).label("qtd_os_fechadas"),
        )
        .outerjoin(vendas_sub, vendas_sub.c.funcionario_id == Funcionario.id)
        .outerjoin(os_sub, os_sub.c.funcionario_id == Funcionario.id)
        .where(and_(
            Funcionario.empresa_id == empresa_id,
            Funcionario.ativo == True,
        ))
        # Ranking JUSTO: ordena por faturamento total (vendas + OS), nao so vendas.
        .order_by((total_vendas + total_os).desc())
        .limit(limit)
    )
    return db.execute(stmt).all()


# ===========================================================================
# MASTER — OS por status
# ===========================================================================

def get_os_por_status(db: Session, empresa_id: int) -> Sequence:
    """Contagem de OS ativas agrupadas por status para a empresa."""
    stmt = (
        select(
            OSModel.status,
            func.count(OSModel.id).label("count"),
        )
        .outerjoin(Funcionario, Funcionario.id == OSModel.funcionario_id)
        .where(and_(
            OSModel.ativo == True,
            OSModel.status.notin_([OrdemServicoStatus.CANCELADA, OrdemServicoStatus.FINALIZADA]),
            or_(
                Funcionario.empresa_id == empresa_id,
                OSModel.funcionario_id.is_(None),
            ),
        ))
        .group_by(OSModel.status)
    )
    return db.execute(stmt).all()


# ===========================================================================
# MASTER — Formas de pagamento
# ===========================================================================

def get_formas_pagamento_vendas(
    db: Session, data_inicio: datetime, data_fim: datetime, empresa_id: int
) -> Sequence:
    """Pagamentos de vendas agrupados por forma no periodo."""
    stmt = (
        select(
            FormaPagamento.nome,
            func.sum(PagamentoVenda.valor).label("total"),
        )
        .select_from(PagamentoVenda)
        .join(FormaPagamento, FormaPagamento.id == PagamentoVenda.forma_pagamento_id)
        .join(Venda, Venda.id == PagamentoVenda.venda_id)
        .join(Funcionario, Funcionario.id == Venda.funcionario_id)
        .where(and_(
            Venda.status == VendaStatus.FINALIZADA,
            Venda.criado_em >= data_inicio,
            Venda.criado_em <= data_fim,
            Funcionario.empresa_id == empresa_id,
        ))
        .group_by(FormaPagamento.nome)
    )
    return db.execute(stmt).all()


def get_formas_pagamento_os(
    db: Session, data_inicio: datetime, data_fim: datetime, empresa_id: int
) -> Sequence:
    """Pagamentos de OS agrupados por forma no periodo."""
    stmt = (
        select(
            FormaPagamento.nome,
            func.sum(OrdemServicoPagamento.valor).label("total"),
        )
        .select_from(OrdemServicoPagamento)
        .join(FormaPagamento, FormaPagamento.id == OrdemServicoPagamento.forma_pagamento_id)
        .join(OSModel, OSModel.id == OrdemServicoPagamento.ordem_servico_id)
        .outerjoin(Funcionario, Funcionario.id == OSModel.funcionario_id)
        .where(and_(
            OSModel.status == OrdemServicoStatus.FINALIZADA,
            OSModel.data_criacao >= data_inicio,
            OSModel.data_criacao <= data_fim,
            or_(
                Funcionario.empresa_id == empresa_id,
                OSModel.funcionario_id.is_(None),
            ),
        ))
        .group_by(FormaPagamento.nome)
    )
    return db.execute(stmt).all()


# ===========================================================================
# MASTER — OS atrasadas da empresa toda
# ===========================================================================

def get_os_atrasadas_empresa(db: Session, empresa_id: int, limit: int = 15) -> Sequence:
    """OS com prazo vencido de toda a empresa, com nome do responsavel."""
    client_pf = aliased(ClientePF)
    client_pj = aliased(ClientePJ)
    hoje_inicio = datetime.combine(datetime.utcnow().date(), datetime.min.time())

    stmt = (
        select(
            OSModel.numero_os,
            func.coalesce(client_pf.nome, client_pj.razao_social, literal("Sem cliente")).label("cliente_nome"),
            Funcionario.nome.label("funcionario_nome"),
            OSModel.defeito_relatado,
            OSModel.data_previsao,
        )
        .join(OSModel.objeto)
        .join(OSEquipamentoModel.cliente)
        .outerjoin(client_pf, Cliente.id == client_pf.id)
        .outerjoin(client_pj, Cliente.id == client_pj.id)
        .outerjoin(Funcionario, Funcionario.id == OSModel.funcionario_id)
        .where(and_(
            OSModel.data_previsao < hoje_inicio,
            OSModel.status.notin_([OrdemServicoStatus.FINALIZADA, OrdemServicoStatus.CANCELADA]),
            OSModel.ativo == True,
            or_(
                Funcionario.empresa_id == empresa_id,
                OSModel.funcionario_id.is_(None),
            ),
        ))
        .order_by(OSModel.data_previsao.asc())
        .limit(limit)
    )
    return db.execute(stmt).all()


# ===========================================================================
# ULTIMAS VENDAS — Vendas recentes (finalizadas + orcamentos)
# ===========================================================================

def get_ultimas_vendas(db: Session, empresa_id: int, limit: int = 5) -> Sequence:
    """
    Ultimas vendas (finalizadas e orcamentos), com nome do cliente resolvido.
    Filtra por empresa_id via Funcionario.
    """
    client_pf = aliased(ClientePF)
    client_pj = aliased(ClientePJ)

    stmt = (
        select(
            Venda.id,
            func.coalesce(client_pf.nome, client_pj.razao_social).label("cliente_nome"),
            Venda.total,
            Venda.status,
            Venda.criado_em,
        )
        .join(Funcionario, Funcionario.id == Venda.funcionario_id)
        .outerjoin(Venda.cliente)
        .outerjoin(client_pf, Cliente.id == client_pf.id)
        .outerjoin(client_pj, Cliente.id == client_pj.id)
        .where(
            and_(
                Venda.status.in_([VendaStatus.FINALIZADA, VendaStatus.ATIVA]),
                Funcionario.empresa_id == empresa_id,
            )
        )
        .order_by(Venda.criado_em.desc())
        .limit(limit)
    )

    return db.execute(stmt).all()
