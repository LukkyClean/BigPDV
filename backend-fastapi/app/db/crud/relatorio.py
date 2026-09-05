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
from sqlalchemy import select, func, and_, or_, case, literal

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

    Ancorado em data_finalizacao: a receita da OS pertence ao dia em que ela foi
    fechada, nao ao dia em que o equipamento entrou. Bate com o get_stats_agregados
    do dashboard, que usa a mesma ancora.
    """
    stmt = (
        select(
            func.date(OSModel.data_finalizacao).label("dia"),
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
        .group_by(func.date(OSModel.data_finalizacao))
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
    # ===================================================================
    # A BASE E O LUCRO, NAO O FATURAMENTO (decisao do dono, 05/09/2026)
    #
    # "O dono acaba pagando comissao em uma coisa que nao e lucro no servico."
    # O caso que abriu isto: OS de "Troca de Tela R$ 240" onde a tela custou
    # R$ 165. A loja ganhou R$ 75 de mao de obra e pagava comissao sobre 240.
    #
    # Nesta loja a peca vai EMBUTIDA no preco do servico -- o cliente ve
    # "Troca de Tela R$ 240" e nunca o preco da tela. O padrao de mercado e
    # itemizar (servico R$ 75 + peca R$ 165) e comissionar so a linha de
    # servico; aqui isso exporia a peca na via do cliente, o que a loja nao
    # quer. Por isso a base desconta o `custo_unitario` DECLARADO no item, que
    # e interno e nunca impresso (ver db/models/ordem_servico_item.py).
    #
    # ⚠️ DEPENDE DO CUSTO ESTAR PREENCHIDO. Item de servico sem
    # `custo_unitario` e lido como 100% mao de obra e comissiona sobre o valor
    # cheio -- que e exatamente o comportamento antigo. O erro, quando houver,
    # e a favor do funcionario e nunca contra, o que e o lado certo de errar.
    #
    # ⚠️ TROCAR A BASE SEM RECALIBRAR O PERCENTUAL E CORTE DE SALARIO. 5% de
    # 240 = R$ 12,00; 5% de 75 = R$ 3,75. Para o tecnico manter o que ganhava,
    # a taxa precisa subir (~16% no exemplo). Margem e um numero menor, entao o
    # percentual sobre ela e maior -- isso e a mecanica do modelo, nao um
    # detalhe de implementacao.
    # ===================================================================

    # --- OS: so item de SERVICO, e so a mao de obra dele -------------------
    #
    # Item de PRODUTO fica de fora inteiro: peca e repasse, nao trabalho.
    # REPROVADO fica de fora porque o servico nao foi feito -- mesma regra que
    # o total da OS e o CMV ja usam.
    os_sub = (
        select(
            OSModel.funcionario_id.label("fid"),
            func.coalesce(
                func.sum(
                    OrdemServicoItem.valor_total
                    - OrdemServicoItem.quantidade
                    * func.coalesce(OrdemServicoItem.custo_unitario, 0)
                ),
                0,
            ).label("os_valor"),
        )
        .join(OSModel, OSModel.id == OrdemServicoItem.ordem_servico_id)
        .where(
            and_(
                OSModel.status == OrdemServicoStatus.FINALIZADA,
                OSModel.data_finalizacao.isnot(None),
                OSModel.data_finalizacao >= data_inicio,
                OSModel.data_finalizacao <= data_fim,
                OrdemServicoItem.tipo == OrdemServicoItemTipo.SERVICO,
                OrdemServicoItem.status_aprovacao
                != OrdemServicoItemAprovacao.REPROVADO,
            )
        )
        .group_by(OSModel.funcionario_id)
        .subquery()
    )

    # --- Venda: a MARGEM (o que sobrou depois do custo da mercadoria) ------
    #
    # Tres parcelas, espelhando `services/custo_mercadoria.calcular_cmv` para
    # que a comissao e o lucro do mes falem do mesmo numero:
    #   receita  Venda.total ja pos-desconto, menos o juros da operadora
    #   custo 1  peca do catalogo, custo congelado no livro de estoque
    #   custo 2  item avulso, custo declarado a mao (nao passa pelo estoque)
    venda_receita_sub = (
        select(
            Venda.funcionario_id.label("fid"),
            func.coalesce(
                func.sum(Venda.total - func.coalesce(Venda.acrescimo, 0)), 0
            ).label("receita"),
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

    # SAIDA soma, ENTRADA subtrai: a venda cancelada devolve o custo sozinha,
    # sem ninguem cacar estorno na mao (mesma regra do CMV).
    venda_custo_estoque_sub = (
        select(
            Venda.funcionario_id.label("fid"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            MovimentacaoEstoque.tipo == MovimentacaoTipo.SAIDA,
                            MovimentacaoEstoque.quantidade
                            * func.coalesce(MovimentacaoEstoque.custo_unitario, 0),
                        ),
                        else_=-MovimentacaoEstoque.quantidade
                        * func.coalesce(MovimentacaoEstoque.custo_unitario, 0),
                    )
                ),
                0,
            ).label("custo"),
        )
        .join(Venda, Venda.id == MovimentacaoEstoque.venda_id)
        .where(
            and_(
                MovimentacaoEstoque.origem == MovimentacaoOrigem.VENDA.value,
                MovimentacaoEstoque.tipo.in_(
                    [MovimentacaoTipo.ENTRADA, MovimentacaoTipo.SAIDA]
                ),
                Venda.status == VendaStatus.FINALIZADA,
                Venda.criado_em >= data_inicio,
                Venda.criado_em <= data_fim,
            )
        )
        .group_by(Venda.funcionario_id)
        .subquery()
    )

    venda_custo_avulso_sub = (
        select(
            Venda.funcionario_id.label("fid"),
            func.coalesce(
                func.sum(ProdutoVenda.quantidade * ProdutoVenda.custo_unitario), 0
            ).label("custo"),
        )
        .join(Venda, Venda.id == ProdutoVenda.venda_id)
        .where(
            and_(
                ProdutoVenda.custo_unitario.isnot(None),
                # Item COM produto_id ja tem custo congelado no livro; somar os
                # dois dobraria o custo e zeraria a comissao do vendedor.
                ProdutoVenda.produto_id.is_(None),
                Venda.status == VendaStatus.FINALIZADA,
                Venda.criado_em >= data_inicio,
                Venda.criado_em <= data_fim,
            )
        )
        .group_by(Venda.funcionario_id)
        .subquery()
    )

    # Piso em zero: venda no prejuizo (liquidacao abaixo do custo) daria margem
    # negativa, e margem negativa viraria comissao negativa -- descontando do
    # que o funcionario ganhou nas outras vendas. Prejuizo e risco do dono.
    _margem_venda = (
        func.coalesce(venda_receita_sub.c.receita, 0)
        - func.coalesce(venda_custo_estoque_sub.c.custo, 0)
        - func.coalesce(venda_custo_avulso_sub.c.custo, 0)
    )
    _mao_de_obra = func.coalesce(os_sub.c.os_valor, 0)

    vendas_valor = case((_margem_venda < 0, 0), else_=_margem_venda)
    os_valor = case((_mao_de_obra < 0, 0), else_=_mao_de_obra)

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
        .outerjoin(venda_receita_sub, venda_receita_sub.c.fid == Funcionario.id)
        .outerjoin(
            venda_custo_estoque_sub, venda_custo_estoque_sub.c.fid == Funcionario.id
        )
        .outerjoin(
            venda_custo_avulso_sub, venda_custo_avulso_sub.c.fid == Funcionario.id
        )
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
            # O custo da peca embutida, para o extrato poder mostrar a MAO DE
            # OBRA -- que desde 05/09/2026 e a base da comissao. Sem esta
            # coluna o tecnico conferia um numero (o valor cheio do servico) e
            # recebia sobre outro, e um funcionario que nao consegue conferir o
            # proprio pagamento desconfia dele.
            func.coalesce(OrdemServicoItem.custo_unitario, 0).label("custo_unitario"),
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
