"""empresa razao_social e documento nullable

Revision ID: c1d2e3f4a5b6
Revises: 0bafd944816a
Create Date: 2026-06-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = '0bafd944816a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Torna razao_social e documento nullable na tabela empresas."""
    connection = op.get_bind()
    connection.execute(sa.text("PRAGMA foreign_keys=OFF"))

    with op.batch_alter_table('empresas') as batch_op:
        batch_op.alter_column(
            'razao_social',
            existing_type=sa.String(255),
            nullable=True,
        )
        batch_op.alter_column(
            'documento',
            existing_type=sa.String(14),
            nullable=True,
        )

    connection.execute(sa.text("PRAGMA foreign_keys=ON"))


def downgrade() -> None:
    """Reverte razao_social e documento para NOT NULL."""
    connection = op.get_bind()
    connection.execute(sa.text("PRAGMA foreign_keys=OFF"))

    with op.batch_alter_table('empresas') as batch_op:
        batch_op.alter_column(
            'razao_social',
            existing_type=sa.String(255),
            nullable=False,
        )
        batch_op.alter_column(
            'documento',
            existing_type=sa.String(14),
            nullable=False,
        )

    connection.execute(sa.text("PRAGMA foreign_keys=ON"))
