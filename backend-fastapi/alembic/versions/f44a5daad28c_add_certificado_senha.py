"""add_certificado_senha

Revision ID: f44a5daad28c
Revises: h1i2j3k4l5m6
Create Date: 2026-08-19 13:13:26.274168

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f44a5daad28c'
down_revision: Union[str, Sequence[str], None] = 'h1i2j3k4l5m6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('empresa_fiscal_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('certificado_senha', sa.String(length=200), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('empresa_fiscal_settings', schema=None) as batch_op:
        batch_op.drop_column('certificado_senha')