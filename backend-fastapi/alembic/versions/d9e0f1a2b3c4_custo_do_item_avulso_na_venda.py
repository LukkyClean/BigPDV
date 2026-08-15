"""custo do item avulso na venda: custo_unitario em produtos_venda

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-07-31 14:00:00.000000

CONTEXTO:
Fecha o ultimo buraco do CMV. Venda de produto CADASTRADO ja da baixa no estoque
e tem o custo congelado no livro (movimentacoes_estoque). Ja o item AVULSO —
aquele digitado na hora, que nao esta no catalogo — NAO movimenta estoque
(services/venda.py so chama decrease_product_in_stock para CADASTRADO). Sem
custo, ele entrava no relatorio como receita pura e inflava o lucro.

E o mesmo formato do que foi resolvido na OS, e a mesma regra: o campo so vale
para item SEM produto do catalogo; com produto, quem manda e o livro, e contar
os dois dobraria o CMV.

E INTERNO: nao sai em nenhuma via impressa. O cliente nunca deve ver quanto foi
pago pela peca.

SEGURANCA (banco de cliente em producao):
- SOMENTE `ADD COLUMN` — no SQLite e instantaneo, NAO recria a tabela.
- Nasce NULL em tudo que ja existe. Venda antiga nao ganha custo inventado; o
  relatorio le NULL como "sem custo apurado", nao como "custo zero".
- Guarda de existencia por coluna -> idempotente. Necessario porque o
  `create_all` roda ANTES das migrations no startup.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd9e0f1a2b3c4'
down_revision: Union[str, Sequence[str], None] = 'c8d9e0f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _colunas(tabela: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {coluna["name"] for coluna in inspector.get_columns(tabela)}


def upgrade() -> None:
    if "custo_unitario" not in _colunas("produtos_venda"):
        op.add_column(
            "produtos_venda",
            sa.Column("custo_unitario", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    if "custo_unitario" in _colunas("produtos_venda"):
        op.drop_column("produtos_venda", "custo_unitario")
