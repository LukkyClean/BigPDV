"""adiciona coluna comissao_modo ('direto' | 'meta') em cargos e funcionarios

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-07-24 10:00:00.000000

SEGURANCA (banco de cliente em producao):
- SOMENTE `ADD COLUMN` nullable — no SQLite e instantaneo, NAO recria a tabela,
  e as linhas existentes ficam com NULL. Nenhum dado e tocado/perdido.
- NULL na cascata (funcionario -> cargo) resolve para 'direto' no service, entao
  cargos/funcionarios ja existentes seguem pagando comissao linear (retrocompativel).
- Guarda de existencia por coluna -> idempotente; nao falha com "already exists".
- Nenhuma alteracao/drop de coluna existente, nenhuma mudanca de tipo.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABELAS = ("cargos", "funcionarios")
_COLUNA = "comissao_modo"


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    for tabela in _TABELAS:
        if not _tem_coluna(insp, tabela, _COLUNA):
            op.add_column(tabela, sa.Column(_COLUNA, sa.String(length=10), nullable=True))


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    for tabela in _TABELAS:
        if _tem_coluna(insp, tabela, _COLUNA):
            op.drop_column(tabela, _COLUNA)
