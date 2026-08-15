"""add numero_venda and rename status RASCUNHO to ORCAMENTO

Revision ID: a3b1c2d4e5f6
Revises: 7107971665b1
Create Date: 2026-05-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3b1c2d4e5f6'
down_revision: Union[str, Sequence[str], None] = '7107971665b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Renomear status RASCUNHO -> ORCAMENTO (SQLite armazena como string)
    op.execute("UPDATE vendas SET status = 'ORCAMENTO' WHERE status = 'RASCUNHO'")

    # 2. Adicionar coluna numero_venda
    op.add_column('vendas', sa.Column('numero_venda', sa.Integer(), nullable=True))

    # 3. Criar index e unique via SQL direto (SQLite nao suporta ALTER para constraints)
    op.execute("CREATE UNIQUE INDEX uq_venda_numero_venda ON vendas (numero_venda)")
    op.execute("CREATE INDEX ix_venda_numero_venda ON vendas (numero_venda)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE vendas SET status = 'RASCUNHO' WHERE status = 'ORCAMENTO'")
    op.execute("DROP INDEX IF EXISTS ix_venda_numero_venda")
    op.execute("DROP INDEX IF EXISTS uq_venda_numero_venda")
    op.drop_column('vendas', 'numero_venda')
