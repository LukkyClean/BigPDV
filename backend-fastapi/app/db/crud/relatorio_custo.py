# ---------------------------------------------------------------------------
# ARQUIVO: crud/relatorio_custo.py
# DESCRICAO: As consultas de CUSTO da mercadoria vendida. Apenas leitura.
# ---------------------------------------------------------------------------
"""
Separado de `crud/relatorio.py` em 05/09/2026, pelo MESMO motivo que ja tinha
quebrado o crud do financeiro e o service em dois: o PyArmor da licenca trial
recusa ofuscar modulo acima de um teto de BYTECODE, e o `build:sidecar` morre
com "out of license".

O teto foi MEDIDO, nao chutado. `crud/relatorio.py` estava em 18.360 bytes de
bytecode e passava; ao ganhar o detalhamento do CMV e a nova base de comissao
foi para 25.598, acima dos 22.300 que ja tinham sido recusados. Tirar estas
seis funcoes o devolve para ~17.400.

O corte seguiu uma fronteira que ja existia no arquivo -- a secao "CMV" tinha
moldura propria. Nenhuma regra mudou de lugar dentro dela.
"""

from datetime import datetime
from typing import Sequence

from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_

from app.db.models.venda import Venda
from app.db.models.venda_produto import ProdutoVenda
from app.db.models.produto import Produto
from app.db.models.movimentacao_estoque import MovimentacaoEstoque
from app.db.models.ordem_servico import OrdemServico as OSModel
from app.db.models.ordem_servico_item import OrdemServicoItem
from app.db.models.funcionario import Funcionario
from app.core.enum import (
    VendaStatus,
    OrdemServicoStatus,
    MovimentacaoOrigem,
    MovimentacaoTipo,
    OrdemServicoItemAprovacao,
)


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


# ---------------------------------------------------------------------------
# DETALHE DO CMV — de onde vem cada centavo do "Custo do que vendeu"
#
# O card mostrava um total e mais nada. O dono passou uma tarde em 05/09/2026
# conferindo R$ 846 no papel, OS por OS, sem ter onde abrir o numero -- e o que
# faltava era um custo lancado num item avulso, invisivel depois de a OS
# finalizar.
#
# As quatro parcelas do `custo_mercadoria.calcular_cmv` viram LINHAS aqui, com
# os mesmos filtros de cada uma. Se as duas somas divergirem, e bug: o detalhe
# tem que fechar com o total, senao ele piora a desconfianca em vez de resolver.
# ---------------------------------------------------------------------------

def get_detalhe_cmv(
    db: Session, data_inicio: datetime, data_fim: datetime, empresa_id: int
) -> list[dict]:
    """Uma linha por origem de custo no periodo, ja ordenada por data."""
    linhas: list[dict] = []

    # --- 1 e 2: peca que saiu do estoque, custo congelado no livro -----------
    for origem, modelo, ancora, ref_col, status_ok in (
        (
            MovimentacaoOrigem.VENDA.value, Venda, Venda.criado_em,
            Venda.numero_venda, Venda.status == VendaStatus.FINALIZADA,
        ),
        (
            MovimentacaoOrigem.ORDEM_SERVICO.value, OSModel, OSModel.data_finalizacao,
            OSModel.numero_os, OSModel.status == OrdemServicoStatus.FINALIZADA,
        ),
    ):
        chave = (
            MovimentacaoEstoque.venda_id if origem == MovimentacaoOrigem.VENDA.value
            else MovimentacaoEstoque.ordem_servico_id
        )
        stmt = (
            select(
                ancora.label("data"),
                ref_col.label("referencia"),
                Produto.nome.label("descricao"),
                MovimentacaoEstoque.quantidade,
                MovimentacaoEstoque.custo_unitario,
                MovimentacaoEstoque.tipo,
            )
            .join(modelo, modelo.id == chave)
            .outerjoin(Produto, Produto.id == MovimentacaoEstoque.produto_id)
            .outerjoin(Funcionario, Funcionario.id == modelo.funcionario_id)
            .where(
                and_(
                    MovimentacaoEstoque.origem == origem,
                    MovimentacaoEstoque.tipo.in_(
                        [MovimentacaoTipo.ENTRADA, MovimentacaoTipo.SAIDA]
                    ),
                    status_ok,
                    ancora >= data_inicio,
                    ancora <= data_fim,
                    or_(
                        Funcionario.empresa_id == empresa_id,
                        modelo.funcionario_id.is_(None),
                    ),
                )
            )
        )
        for r in db.execute(stmt).all():
            valor = round((r.quantidade or 0) * (r.custo_unitario or 0))
            estorno = r.tipo != MovimentacaoTipo.SAIDA
            linhas.append({
                "data": r.data,
                "origem": "VENDA" if origem == MovimentacaoOrigem.VENDA.value else "OS",
                "referencia": str(r.referencia or "—"),
                "descricao": r.descricao or "Produto removido",
                "quantidade": r.quantidade or 0,
                # Estorno entra NEGATIVO, como no CMV: a peca voltou pra
                # prateleira e o custo dela sai da conta.
                "custo": -valor if estorno else valor,
                "fonte": "ESTORNO" if estorno else "ESTOQUE",
            })

    # --- 3: custo declarado a mao no item da OS ------------------------------
    stmt_os = (
        select(
            OSModel.data_finalizacao.label("data"),
            OSModel.numero_os.label("referencia"),
            OrdemServicoItem.nome.label("descricao"),
            OrdemServicoItem.quantidade,
            OrdemServicoItem.custo_unitario,
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
                or_(
                    Funcionario.empresa_id == empresa_id,
                    OSModel.funcionario_id.is_(None),
                ),
            )
        )
    )
    for r in db.execute(stmt_os).all():
        linhas.append({
            "data": r.data,
            "origem": "OS",
            "referencia": str(r.referencia or "—"),
            "descricao": r.descricao,
            "quantidade": r.quantidade or 0,
            "custo": round((r.quantidade or 0) * (r.custo_unitario or 0)),
            "fonte": "DECLARADO",
        })

    # --- 4: custo declarado a mao no item avulso da venda --------------------
    stmt_venda = (
        select(
            Venda.criado_em.label("data"),
            Venda.numero_venda.label("referencia"),
            ProdutoVenda.descricao_avulsa.label("descricao"),
            ProdutoVenda.quantidade,
            ProdutoVenda.custo_unitario,
        )
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
    for r in db.execute(stmt_venda).all():
        linhas.append({
            "data": r.data,
            "origem": "VENDA",
            "referencia": str(r.referencia or "—"),
            "descricao": r.descricao or "Item avulso",
            "quantidade": r.quantidade or 0,
            "custo": round((r.quantidade or 0) * (r.custo_unitario or 0)),
            "fonte": "DECLARADO",
        })

    # Mais recente primeiro: conferencia comeca pelo que acabou de acontecer.
    linhas.sort(key=lambda l: (l["data"] is not None, l["data"]), reverse=True)
    return linhas
