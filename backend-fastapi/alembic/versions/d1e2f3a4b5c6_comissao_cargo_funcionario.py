"""adiciona colunas de comissao (% venda/servico + meta) em cargos e funcionarios

Revision ID: d1e2f3a4b5c6
Revises: 97dd6ac91792
Create Date: 2026-07-23 16:00:00.000000

SEGURANCA (banco de cliente em producao):
- SOMENTE `ADD COLUMN` nullable — no SQLite e instantaneo, NAO recria a tabela,
  e as linhas existentes ficam com NULL. Nenhum dado e tocado/perdido.
- Guarda de existencia por coluna -> idempotente; nao falha com "already exists".
- Nenhuma alteracao/drop de coluna existente, nenhuma mudanca de tipo.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = '97dd6ac91792'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABELAS = ("cargos", "funcionarios")
_COLUNAS = (
    "comissao_venda_percentual",
    "comissao_servico_percentual",
    "meta_mensal",
)


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    for tabela in _TABELAS:
        for coluna in _COLUNAS:
            if not _tem_coluna(insp, tabela, coluna):
                op.add_column(tabela, sa.Column(coluna, sa.Integer(), nullable=True))


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    for tabela in _TABELAS:
        for coluna in _COLUNAS:
            if _tem_coluna(insp, tabela, coluna):
                op.drop_column(tabela, coluna)
