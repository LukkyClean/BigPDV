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

from sqlalchemy.orm import Session, aliased
from sqlalchemy import select, func, and_, or_, literal

from app.core.tempo import deslocamento_sqlite
from app.db.models.venda import Venda
from app.db.models.venda_pagamento import PagamentoVenda
from app.db.models.venda_produto import ProdutoVenda
from app.db.models.produto import Produto
from app.db.models.estoque import Estoque
from app.db.models.movimentacao_estoque import MovimentacaoEstoque
from app.db.models.ordem_servico import OrdemServico as OSModel
from app.db.models.ordem_servico_item import OrdemServicoItem
from app.db.models.ordem_servico_pagamento import OrdemServicoPagamento
from app.db.models.funcionario import Funcionario
from app.db.models.objeto_servico import ObjetoServico
from app.db.models.cliente import Cliente, ClientePF, ClientePJ
from app.db.models.cargo import Cargo
from app.core.enum import (
    VendaStatus,
    OrdemServicoStatus,
    MovimentacaoOrigem,
    MovimentacaoTipo,
    OrdemServicoItemAprovacao,
    OrdemServicoItemTipo,
)


def get_faturamento_vendas_por_dia(
    db: Session, data_inicio: datetime, data_fim: datetime, empresa_id: int
) -> Sequence:
    """Soma das vendas finalizadas agrupada por dia (func.date), da empresa."""
    stmt = (
        select(
            func.date(Venda.criado_em, deslocamento_sqlite()).label("dia"),
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
        .group_by(func.date(Venda.criado_em, deslocamento_sqlite()))
    )
    return db.execute(stmt).all()


def get_faturamento_os_por_dia(
    db: Session, data_inicio: datetime, data_fim: datetime, empresa_id: int
) -> Sequence:
    """Soma das OS finalizadas agrupada por dia (func.date), da empresa.

    Ancorado em data_finalizacao: a receita da OS pertence ao dia em que ela foi
    fechada, nao ao dia em que o equipamento entrou. Bate com o get_stats_agregados
    do dashboard, que usa a mesma ancora.
    """
    stmt = (
        select(
            func.date(OSModel.data_finalizacao, deslocamento_sqlite()).label("dia"),
            func.coalesce(func.sum(OSModel.valor_total), 0).label("total"),
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
        .group_by(func.date(OSModel.data_finalizacao, deslocamento_sqlite()))
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
                OSModel.data_finalizacao.isnot(None),
                OSModel.data_finalizacao >= data_inicio,
                OSModel.data_finalizacao <= data_fim,
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
                OSModel.data_finalizacao.isnot(None),
                OSModel.data_finalizacao >= data_inicio,
                OSModel.data_finalizacao <= data_fim,
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


# ---------------------------------------------------------------------------
# CMV — custo da mercadoria vendida
#
# Sai do livro de estoque, nao do cadastro do produto: o que interessa e quanto
# a peca custava NO DIA em que ela saiu, e esse numero esta congelado em
# `movimentacoes_estoque.custo_unitario`.
#
# Ancoragem de data: NAO usa `movimentacao.created_at`, e sim a mesma data que
# ancora a receita (Venda.criado_em e OS.data_finalizacao). Uma venda criada
# ontem e fechada hoje teria a receita num dia e o custo no outro, e a margem
# do dia sairia errada nos dois. Amarrando na data da receita, CMV e faturamento
# sempre fecham no mesmo periodo.
#
# ENTRADA aqui e ESTORNO (venda cancelada, OS reaberta) e entra como credito: a
# peca voltou para a prateleira, entao o custo dela sai do CMV. Por isso o
# agrupamento e por tipo, e nao um `sum` unico.
#
# AJUSTE fica DE FORA de proposito: contagem de inventario nao e venda. Sobra e
# falta de estoque sao ganho ou perda operacional, e jogar isso no CMV faria a
# margem despencar todo mes de inventario, justamente quando a loja foi mais
# caprichosa.
# ---------------------------------------------------------------------------

def _custo_movimentado():
    """Σ (quantidade × custo congelado) e quantas linhas ficaram sem custo."""
    return (
        func.coalesce(
            func.sum(MovimentacaoEstoque.quantidade * MovimentacaoEstoque.custo_unitario), 0
        ).label("total"),
        func.count(MovimentacaoEstoque.id)
        .filter(MovimentacaoEstoque.custo_unitario.is_(None))
        .label("sem_custo"),
    )


def get_cmv_vendas(
    db: Session, data_inicio: datetime, data_fim: datetime, empresa_id: int
) -> Sequence:
    """Custo das peças movimentadas por venda no período, agrupado por tipo."""
    total, sem_custo = _custo_movimentado()
    stmt = (
        select(MovimentacaoEstoque.tipo, total, sem_custo)
        .join(Venda, Venda.id == MovimentacaoEstoque.venda_id)
        .join(Funcionario, Funcionario.id == Venda.funcionario_id)
        .where(
            and_(
                MovimentacaoEstoque.origem == MovimentacaoOrigem.VENDA.value,
                MovimentacaoEstoque.tipo.in_(
                    [MovimentacaoTipo.ENTRADA, MovimentacaoTipo.SAIDA]
                ),
                Venda.status == VendaStatus.FINALIZADA,
                Venda.criado_em >= data_inicio,
                Venda.criado_em <= data_fim,
                Funcionario.empresa_id == empresa_id,
            )
        )
        .group_by(MovimentacaoEstoque.tipo)
    )
    return db.execute(stmt).all()


def get_cmv_os(
    db: Session, data_inicio: datetime, data_fim: datetime, empresa_id: int
) -> Sequence:
    """Custo das peças movimentadas por OS no período, agrupado por tipo."""
    total, sem_custo = _custo_movimentado()
    stmt = (
        select(MovimentacaoEstoque.tipo, total, sem_custo)
        .join(OSModel, OSModel.id == MovimentacaoEstoque.ordem_servico_id)
        .outerjoin(Funcionario, Funcionario.id == OSModel.funcionario_id)
        .where(
            and_(
                MovimentacaoEstoque.origem == MovimentacaoOrigem.ORDEM_SERVICO.value,
                MovimentacaoEstoque.tipo.in_(
                    [MovimentacaoTipo.ENTRADA, MovimentacaoTipo.SAIDA]
                ),
                OSModel.status == OrdemServicoStatus.FINALIZADA,
                OSModel.data_finalizacao >= data_inicio,
                OSModel.data_finalizacao <= data_fim,
                # OS sem técnico atribuído pertence à empresa — é o mesmo escopo
                # que o faturamento usa (dashboard.get_stats_agregados). Com
                # INNER JOIN, a receita dessas OS entrava e o custo NÃO, e o
                # lucro saía inflado exatamente nelas.
                or_(
                    Funcionario.empresa_id == empresa_id,
                    OSModel.funcionario_id.is_(None),
                ),
            )
        )
        .group_by(MovimentacaoEstoque.tipo)
    )
    return db.execute(stmt).all()


def get_custo_manual_os(
    db: Session, data_inicio: datetime, data_fim: datetime, empresa_id: int
) -> int:
    """Gasto declarado a mão nos itens de OS finalizadas no período (centavos).

    Existe porque na OS o comum é NÃO cadastrar a peça: lança-se só o serviço. O
    custo dela não passa pelo livro de estoque, então precisa de um lugar próprio
    — senão o lucro do mês sai maior do que foi.

    Duas exclusões que evitam contar errado:
      - item COM `produto_id` fica de fora: esse saiu do estoque e já tem custo
        congelado no livro; somar os dois dobraria o CMV.
      - item REPROVADO fica de fora: o cliente recusou, o serviço não foi feito
        e o gasto não aconteceu.

    Ancorado em `data_finalizacao`, igual à receita da OS, para o custo cair no
    mesmo período do faturamento que ele produziu.
    """
    stmt = (
        select(
            func.coalesce(
                func.sum(OrdemServicoItem.quantidade * OrdemServicoItem.custo_unitario), 0
            )
        )
        .join(OSModel, OSModel.id == OrdemServicoItem.ordem_servico_id)
        .outerjoin(Funcionario, Funcionario.id == OSModel.funcionario_id)
        .where(
            and_(
                OrdemServicoItem.custo_unitario.isnot(None),
                OrdemServicoItem.produto_id.is_(None),
                OrdemServicoItem.status_aprovacao != OrdemServicoItemAprovacao.REPROVADO,
                OSModel.status == OrdemServicoStatus.FINALIZADA,
                OSModel.data_finalizacao >= data_inicio,
                OSModel.data_finalizacao <= data_fim,
                # Mesmo escopo do faturamento: OS sem técnico é da empresa.
                or_(
                    Funcionario.empresa_id == empresa_id,
                    OSModel.funcionario_id.is_(None),
                ),
            )
        )
    )
    return db.scalar(stmt) or 0


def get_custo_manual_vendas(
    db: Session, data_inicio: datetime, data_fim: datetime, empresa_id: int
) -> int:
    """Gasto declarado a mão nos itens AVULSOS de vendas finalizadas (centavos).

    Item avulso não movimenta estoque (services/venda.py só baixa o CADASTRADO),
    então o custo dele não passa pelo livro. Sem isto, um avulso vendido por 80
    que custou 30 entrava como receita pura.

    Exclui item com `produto_id`: esse deu baixa e já tem custo congelado no
    livro — somar os dois dobraria o CMV.
    """
    stmt = (
        select(func.coalesce(func.sum(ProdutoVenda.quantidade * ProdutoVenda.custo_unitario), 0))
        .join(Venda, Venda.id == ProdutoVenda.venda_id)
        .join(Funcionario, Funcionario.id == Venda.funcionario_id)
        .where(
            and_(
                ProdutoVenda.custo_unitario.isnot(None),
                ProdutoVenda.produto_id.is_(None),
                Venda.status == VendaStatus.FINALIZADA,
                Venda.criado_em >= data_inicio,
                Venda.criado_em <= data_fim,
                Funcionario.empresa_id == empresa_id,
            )
        )
    )
    return db.scalar(stmt) or 0


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
            Estoque.custo_medio,
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


def get_servicos_do_funcionario(
    db: Session,
    data_inicio: datetime,
    data_fim: datetime,
    empresa_id: int,
    funcionario_id: int,
) -> Sequence:
    """Os SERVICOS executados por um funcionario nas OS finalizadas do periodo.

    Uma linha por ITEM, nao por OS: a OS com tres servicos devolve tres linhas.
    Quem conta OS distintas e o service, com um `set` -- somar linhas diria "3 OS"
    e o numero nao bateria com o ranking, que e o primeiro lugar onde alguem vai
    conferir este extrato.

    ANCORA = `data_finalizacao`, como todo o resto do modulo: o que foi concluido
    no periodo conta no periodo.

    SO OS FINALIZADA. Servico em OS aberta ainda pode mudar ou sair, e extrato
    com linha que some depois e pior que extrato incompleto.

    ITEM REPROVADO FICA DE FORA -- ele nao foi executado, e ja nao entra no total
    da OS. O criterio e `!= REPROVADO`, o mesmo que a consulta de CMV deste
    arquivo usa: PENDENTE nao precisa ser tratado porque finalizar OS com item
    pendente ja e barrado, entao numa OS finalizada ele nao existe.
    """
    client_pf = aliased(ClientePF)
    client_pj = aliased(ClientePJ)

    stmt = (
        select(
            OSModel.id.label("os_id"),
            OSModel.numero_os,
            OSModel.data_finalizacao,
            ObjetoServico.marca,
            ObjetoServico.modelo,
            ObjetoServico.numero_serie,
            func.coalesce(client_pf.nome, client_pj.razao_social).label("cliente_nome"),
            OrdemServicoItem.nome.label("servico"),
            OrdemServicoItem.quantidade,
            OrdemServicoItem.valor_total,
        )
        .join(OrdemServicoItem, OrdemServicoItem.ordem_servico_id == OSModel.id)
        .outerjoin(ObjetoServico, ObjetoServico.id == OSModel.objeto_id)
        .outerjoin(Cliente, Cliente.id == ObjetoServico.cliente_id)
        .outerjoin(client_pf, Cliente.id == client_pf.id)
        .outerjoin(client_pj, Cliente.id == client_pj.id)
        .join(Funcionario, Funcionario.id == OSModel.funcionario_id)
        .where(
            and_(
                OSModel.status == OrdemServicoStatus.FINALIZADA,
                OSModel.data_finalizacao.isnot(None),
                OSModel.data_finalizacao >= data_inicio,
                OSModel.data_finalizacao <= data_fim,
                OSModel.funcionario_id == funcionario_id,
                Funcionario.empresa_id == empresa_id,
                OrdemServicoItem.tipo == OrdemServicoItemTipo.SERVICO,
                OrdemServicoItem.status_aprovacao != OrdemServicoItemAprovacao.REPROVADO,
            )
        )
        # O papel e lido de cima para baixo como uma linha do tempo do mes.
        .order_by(OSModel.data_finalizacao.asc(), OSModel.numero_os.asc(), OrdemServicoItem.id.asc())
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
                # Por data de criação, de propósito: aqui a pergunta é quanto
                # trabalho ENTROU, não quanto foi faturado.
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


# ---------------------------------------------------------------------------
# JUROS DE CARTAO
#
# O juros de um pagamento sempre vai para a operadora; o que muda e quem paga.
# Repassado (CLIENTE), ele esta embutido no total da venda/OS e portanto inflou
# o faturamento bruto. Absorvido (LOJA), ele nao esta em lugar nenhum do total,
# mas saiu do bolso da loja. Nos dois casos precisa ser descontado para chegar
# ao liquido — por isso as somas vem separadas por responsavel.
#
# Os filtros de periodo/empresa espelham get_formas_pagamento_* do dashboard,
# para que o desconto caia exatamente sobre o mesmo conjunto que formou o bruto.
# ---------------------------------------------------------------------------

def get_juros_vendas_por_responsavel(
    db: Session, data_inicio: datetime, data_fim: datetime, empresa_id: int
) -> Sequence:
    """Soma de juros dos pagamentos de venda, agrupada por responsavel."""
    stmt = (
        select(
            PagamentoVenda.juros_responsavel.label("responsavel"),
            func.coalesce(func.sum(PagamentoVenda.juros_valor), 0).label("total"),
        )
        .select_from(PagamentoVenda)
        .join(Venda, Venda.id == PagamentoVenda.venda_id)
        .join(Funcionario, Funcionario.id == Venda.funcionario_id)
        .where(
            and_(
                Venda.status == VendaStatus.FINALIZADA,
                Venda.criado_em >= data_inicio,
                Venda.criado_em <= data_fim,
                Funcionario.empresa_id == empresa_id,
            )
        )
        .group_by(PagamentoVenda.juros_responsavel)
    )
    return db.execute(stmt).all()


def get_juros_os_por_responsavel(
    db: Session, data_inicio: datetime, data_fim: datetime, empresa_id: int
) -> Sequence:
    """Soma de juros dos pagamentos de OS, agrupada por responsavel."""
    stmt = (
        select(
            OrdemServicoPagamento.juros_responsavel.label("responsavel"),
            func.coalesce(func.sum(OrdemServicoPagamento.juros_valor), 0).label("total"),
        )
        .select_from(OrdemServicoPagamento)
        .join(OSModel, OSModel.id == OrdemServicoPagamento.ordem_servico_id)
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
        .group_by(OrdemServicoPagamento.juros_responsavel)
    )
    return db.execute(stmt).all()
