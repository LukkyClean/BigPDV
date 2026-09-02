"""add_certificado_status_cnpj

Revision ID: 86e916edd50b
Revises: l5m6n7o8p9q0
Create Date: 2026-09-01 23:16:58.726040

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '86e916edd50b'
down_revision: Union[str, Sequence[str], None] = 'l5m6n7o8p9q0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('empresa_fiscal_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('certificado_status', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('certificado_cnpj', sa.String(length=14), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('empresa_fiscal_settings', schema=None) as batch_op:
        batch_op.drop_column('certificado_cnpj')
        batch_op.drop_column('certificado_status')

