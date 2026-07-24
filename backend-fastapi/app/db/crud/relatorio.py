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
from app.db.models.venda_produto import ProdutoVenda
from app.db.models.produto import Produto
from app.db.models.estoque import Estoque
from app.db.models.ordem_servico import OrdemServico as OSModel
from app.db.models.funcionario import Funcionario
from app.db.models.cargo import Cargo
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


def get_ranking_faturamento(
    db: Session, data_inicio: datetime, data_fim: datetime, empresa_id: int, limit: int = 50
) -> Sequence:
    """Faturamento por funcionario (vendas + OS finalizadas) no periodo, ordenado desc.

    Base do futuro relatorio de comissao. Os subselects somam por funcionario e o
    join com Funcionario restringe a empresa e traz o nome.
    """
    vendas_sub = (
        select(
            Venda.funcionario_id.label("fid"),
            func.coalesce(func.sum(Venda.total), 0).label("vendas_valor"),
            func.count(Venda.id).label("vendas_qtd"),
        )
        .where(
            and_(
                Venda.status == VendaStatus.FINALIZADA,
                Venda.criado_em >= data_inicio,
                Venda.criado_em <= data_fim,
            )
        )
        .group_by(Venda.funcionario_id)
        .subquery()
    )
    os_sub = (
        select(
            OSModel.funcionario_id.label("fid"),
            func.coalesce(func.sum(OSModel.valor_total), 0).label("os_valor"),
            func.count(OSModel.id).label("os_qtd"),
        )
        .where(
            and_(
                OSModel.status == OrdemServicoStatus.FINALIZADA,
                OSModel.data_criacao >= data_inicio,
                OSModel.data_criacao <= data_fim,
            )
        )
        .group_by(OSModel.funcionario_id)
        .subquery()
    )

    vendas_valor = func.coalesce(vendas_sub.c.vendas_valor, 0)
    os_valor = func.coalesce(os_sub.c.os_valor, 0)

    stmt = (
        select(
            Funcionario.id,
            Funcionario.nome,
            vendas_valor.label("vendas_valor"),
            func.coalesce(vendas_sub.c.vendas_qtd, 0).label("vendas_qtd"),
            os_valor.label("os_valor"),
            func.coalesce(os_sub.c.os_qtd, 0).label("os_qtd"),
        )
        .outerjoin(vendas_sub, vendas_sub.c.fid == Funcionario.id)
        .outerjoin(os_sub, os_sub.c.fid == Funcionario.id)
        .where(and_(Funcionario.empresa_id == empresa_id, Funcionario.ativo == True))
        .order_by((vendas_valor + os_valor).desc())
        .limit(limit)
    )
    return db.execute(stmt).all()


def get_comissao_base(
    db: Session, data_inicio: datetime, data_fim: datetime, empresa_id: int, limit: int = 200
) -> Sequence:
    """Base da comissao por funcionario: faturamento (vendas/OS finalizadas) +
    a TAXA resolvida pela cascata funcionario -> cargo (COALESCE) e a meta.

    Percentuais em basis points (500 = 5,00%). Meta em centavos. O calculo em si
    (aplicar a taxa) fica no service.
    """
    vendas_sub = (
        select(
            Venda.funcionario_id.label("fid"),
            func.coalesce(func.sum(Venda.total), 0).label("vendas_valor"),
        )
        .where(
            and_(
                Venda.status == VendaStatus.FINALIZADA,
                Venda.criado_em >= data_inicio,
                Venda.criado_em <= data_fim,
            )
        )
        .group_by(Venda.funcionario_id)
        .subquery()
    )
    os_sub = (
        select(
            OSModel.funcionario_id.label("fid"),
            func.coalesce(func.sum(OSModel.valor_total), 0).label("os_valor"),
        )
        .where(
            and_(
                OSModel.status == OrdemServicoStatus.FINALIZADA,
                OSModel.data_criacao >= data_inicio,
                OSModel.data_criacao <= data_fim,
            )
        )
        .group_by(OSModel.funcionario_id)
        .subquery()
    )

    vendas_valor = func.coalesce(vendas_sub.c.vendas_valor, 0)
    os_valor = func.coalesce(os_sub.c.os_valor, 0)

    stmt = (
        select(
            Funcionario.id,
            Funcionario.nome,
            vendas_valor.label("vendas_valor"),
            os_valor.label("os_valor"),
            # Cascata: taxa/meta do funcionario; se nula, herda do cargo.
            func.coalesce(
                Funcionario.comissao_venda_percentual, Cargo.comissao_venda_percentual
            ).label("rate_venda"),
            func.coalesce(
                Funcionario.comissao_servico_percentual, Cargo.comissao_servico_percentual
            ).label("rate_servico"),
            func.coalesce(Funcionario.meta_mensal, Cargo.meta_mensal).label("meta"),
            # Modo pela mesma cascata; NULL vira 'direto' no service.
            func.coalesce(Funcionario.comissao_modo, Cargo.comissao_modo).label("modo"),
        )
        .outerjoin(vendas_sub, vendas_sub.c.fid == Funcionario.id)
        .outerjoin(os_sub, os_sub.c.fid == Funcionario.id)
        .outerjoin(Cargo, Cargo.id == Funcionario.cargo_id)
        .where(and_(Funcionario.empresa_id == empresa_id, Funcionario.ativo == True))
        .order_by((vendas_valor + os_valor).desc())
        .limit(limit)
    )
    return db.execute(stmt).all()


# ===========================================================================
# ESTOQUE / CURVA ABC (Fase 4a)
# ===========================================================================

def get_vendas_por_produto(
    db: Session, data_inicio: datetime, data_fim: datetime, empresa_id: int
) -> Sequence:
    """Faturamento e quantidade por produto CADASTRADO nas vendas finalizadas do período.

    Base da Curva ABC. Faturamento = Σ(subtotal - desconto) do item (nível-item, já
    pós-desconto do item). Itens avulsos (produto_id NULL) ficam de fora — não têm
    produto de estoque para classificar. Escopo por empresa via funcionário da venda.
    """
    faturamento = func.coalesce(func.sum(ProdutoVenda.subtotal - ProdutoVenda.desconto), 0)
    stmt = (
        select(
            Produto.id.label("produto_id"),
            Produto.nome,
            Produto.codigo_produto.label("sku"),
            Produto.categoria,
            faturamento.label("faturamento"),
            func.coalesce(func.sum(ProdutoVenda.quantidade), 0).label("quantidade"),
        )
        .join(Venda, Venda.id == ProdutoVenda.venda_id)
        .join(Funcionario, Funcionario.id == Venda.funcionario_id)
        .join(Produto, Produto.id == ProdutoVenda.produto_id)
        .where(
            and_(
                Venda.status == VendaStatus.FINALIZADA,
                Venda.criado_em >= data_inicio,
                Venda.criado_em <= data_fim,
                Funcionario.empresa_id == empresa_id,
                ProdutoVenda.produto_id.isnot(None),
            )
        )
        .group_by(Produto.id, Produto.nome, Produto.codigo_produto, Produto.categoria)
        .order_by(faturamento.desc())
    )
    return db.execute(stmt).all()


def get_produtos_estoque(db: Session) -> Sequence:
    """Posição de estoque de todos os produtos ATIVOS (nome, sku, custo, mínimos).

    Produto não tem empresa_id (banco é single-store por loja) — retorna global,
    igual ao get_estoque_baixo do dashboard. Base dos KPIs de valor imobilizado,
    da lista "abaixo do mínimo" e do cruzamento com vendas para achar os "parados".
    """
    stmt = (
        select(
            Produto.id.label("produto_id"),
            Produto.nome,
            Produto.codigo_produto.label("sku"),
            Produto.categoria,
            Estoque.quantidade,
            Estoque.valor_entrada,
            Estoque.valor_varejo,
            Estoque.quantidade_minima,
            Estoque.quantidade_ideal,
        )
        .join(Estoque, Estoque.id == Produto.id)
        .where(Produto.ativo == True)
        .order_by(Produto.nome.asc())
    )
    return db.execute(stmt).all()


# ===========================================================================
# OS-PERFORMANCE (Fase 4b)
# ===========================================================================

def get_os_finalizadas_periodo(
    db: Session, data_inicio: datetime, data_fim: datetime, empresa_id: int
) -> Sequence:
    """OS FINALIZADAS no período (âncora = data_finalizacao) com o que a análise precisa:
    técnico, valor, desfecho e as duas datas para o tempo de conclusão.

    O cálculo (média de tempo, contagem de reparo, agregado por técnico) fica no service
    — o volume de OS de uma loja por período é modesto e evita SQL de data por dialeto.
    Escopo por empresa via funcionário (OS sem funcionário também entram, como no dashboard).
    """
    stmt = (
        select(
            OSModel.id,
            OSModel.funcionario_id,
            Funcionario.nome.label("funcionario_nome"),
            OSModel.valor_total,
            OSModel.situacao_equipamento,
            OSModel.data_criacao,
            OSModel.data_finalizacao,
        )
        .outerjoin(Funcionario, Funcionario.id == OSModel.funcionario_id)
        .where(
            and_(
                OSModel.status == OrdemServicoStatus.FINALIZADA,
                OSModel.data_finalizacao.isnot(None),
                OSModel.data_finalizacao >= data_inicio,
                OSModel.data_finalizacao <= data_fim,
                or_(
                    Funcionario.empresa_id == empresa_id,
                    OSModel.funcionario_id.is_(None),
                ),
            )
        )
    )
    return db.execute(stmt).all()


def get_os_abertas_count_periodo(
    db: Session, data_inicio: datetime, data_fim: datetime, empresa_id: int
) -> int:
    """Quantas OS foram CRIADAS (abertas) no período — throughput de entrada."""
    stmt = (
        select(func.count(OSModel.id))
        .outerjoin(Funcionario, Funcionario.id == OSModel.funcionario_id)
        .where(
            and_(
                OSModel.data_criacao >= data_inicio,
                OSModel.data_criacao <= data_fim,
                or_(
                    Funcionario.empresa_id == empresa_id,
                    OSModel.funcionario_id.is_(None),
                ),
            )
        )
    )
    return db.execute(stmt).scalar() or 0


def get_os_por_status(db: Session, empresa_id: int) -> Sequence:
    """Snapshot do backlog: contagem de OS ATIVAS por status atual (não é do período)."""
    stmt = (
        select(
            OSModel.status,
            func.count(OSModel.id).label("quantidade"),
        )
        .outerjoin(Funcionario, Funcionario.id == OSModel.funcionario_id)
        .where(
            and_(
                OSModel.ativo == True,
                or_(
                    Funcionario.empresa_id == empresa_id,
                    OSModel.funcionario_id.is_(None),
                ),
            )
        )
        .group_by(OSModel.status)
    )
    return db.execute(stmt).all()
