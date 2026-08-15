"""onda3a lembrete de revisao no objeto

Revision ID: 62d130ac4856
Revises: ab4637c30835
Create Date: 2026-07-11 16:08:43.461106

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '62d130ac4856'
down_revision: Union[str, Sequence[str], None] = 'ab4637c30835'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def upgrade() -> None:
    """Onda 3A: colunas de lembrete de revisão em objetos_servico (nullable, aditivas)."""
    conn = op.get_bind()
    insp = sa.inspect(conn)
    with op.batch_alter_table("objetos_servico", schema=None) as batch_op:
        if not _tem_coluna(insp, "objetos_servico", "proxima_revisao_data"):
            batch_op.add_column(sa.Column("proxima_revisao_data", sa.Date(), nullable=True))
        if not _tem_coluna(insp, "objetos_servico", "proxima_revisao_km"):
            batch_op.add_column(sa.Column("proxima_revisao_km", sa.Integer(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    with op.batch_alter_table("objetos_servico", schema=None) as batch_op:
        if _tem_coluna(insp, "objetos_servico", "proxima_revisao_km"):
            batch_op.drop_column("proxima_revisao_km")
        if _tem_coluna(insp, "objetos_servico", "proxima_revisao_data"):
            batch_op.drop_column("proxima_revisao_data")
