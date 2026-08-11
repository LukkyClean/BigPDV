"""add configuracoes_backup

Revision ID: d6adbf5b3d66
Revises: b386f0ba5efd
Create Date: 2026-08-07 15:37:26.908397

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd6adbf5b3d66'
down_revision: Union[str, Sequence[str], None] = 'b386f0ba5efd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('configuracoes_backup',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('backup_automatico_ativo', sa.Boolean(), nullable=False),
    sa.Column('frequencia', sa.String(length=20), nullable=False),
    sa.Column('horario', sa.String(length=5), nullable=False),
    sa.Column('data_atualizacao', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('empresa_id')
    )
    with op.batch_alter_table('configuracoes_backup', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_configuracoes_backup_id'), ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('configuracoes_backup', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_configuracoes_backup_id'))

    op.drop_table('configuracoes_backup')
