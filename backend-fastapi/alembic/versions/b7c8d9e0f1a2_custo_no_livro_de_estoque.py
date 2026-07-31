"""custo no livro de estoque: custo_unitario no movimento e custo_medio no produto

Revision ID: b7c8d9e0f1a2
Revises: a4b5c6d7e8f9
Create Date: 2026-07-31 10:00:00.000000

CONTEXTO:
O relatorio so sabia faturamento bruto. Para saber LUCRO e preciso o CMV (custo
da mercadoria vendida), e para o CMV ser confiavel o custo tem que ficar
congelado no instante em que a peca sai — senao todo reajuste do fornecedor
reescreve o lucro do passado.

  movimentacoes_estoque.custo_unitario
      ENTRADA de compra -> valor efetivamente PAGO por unidade
      SAIDA             -> custo medio no instante da saida (= o CMV daquela
                           venda/OS), congelado para nunca mais mudar

  estoque.custo_medio
      Media ponderada, recalculada SO em entrada de compra. Nao confundir com
      `valor_entrada`, que continua sendo o ultimo preco de compra digitado no
      cadastro, como referencia para o usuario.

SEGURANCA (banco de cliente em producao):
- SOMENTE `ADD COLUMN` — no SQLite e instantaneo, NAO recria nenhuma tabela.
  Recriar `movimentacoes_estoque` (o livro-razao) foi avaliado e descartado:
  uma migracao que falha impede o backend de subir, e o unico ganho seria
  trocar um ON DELETE que hoje nao tem como disparar (nao existe delete fisico
  de produto no sistema).
- As duas colunas nascem NULL em tudo que ja existe. NADA e estimado
  retroativamente: o custo das movimentacoes antigas nao e recuperavel, e
  preencher com o preco de hoje seria inventar lucro que ninguem apurou. O
  relatorio le esse NULL como "periodo sem custo apurado" e diz isso na tela.
- `estoque.custo_medio` fica NULL de proposito, inclusive onde ha
  `valor_entrada`. Enquanto for NULL o sistema cai para `valor_entrada`
  (services/movimentacao_estoque.custo_atual), o que preserva exatamente o
  comportamento atual da loja; a media so assume quando existir uma compra de
  verdade, com valor pago informado. Backfill aqui endureceria esse degrau sem
  necessidade.
- Guarda de existencia por coluna -> idempotente. Necessario porque o
  `create_all` roda ANTES das migrations no startup.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, Sequence[str], None] = 'a4b5c6d7e8f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _colunas(tabela: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {coluna["name"] for coluna in inspector.get_columns(tabela)}


def upgrade() -> None:
    if "custo_unitario" not in _colunas("movimentacoes_estoque"):
        op.add_column(
            "movimentacoes_estoque",
            sa.Column("custo_unitario", sa.Integer(), nullable=True),
        )

    if "custo_medio" not in _colunas("estoque"):
        op.add_column(
            "estoque",
            sa.Column("custo_medio", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    if "custo_medio" in _colunas("estoque"):
        op.drop_column("estoque", "custo_medio")

    if "custo_unitario" in _colunas("movimentacoes_estoque"):
        op.drop_column("movimentacoes_estoque", "custo_unitario")
