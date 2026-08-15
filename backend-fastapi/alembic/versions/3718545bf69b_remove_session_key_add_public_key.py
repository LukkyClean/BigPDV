"""remove_session_key_add_public_key

Revision ID: 3718545bf69b
Revises: 706b2c881cab
Create Date: 2026-06-28 22:34:40.628107

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3718545bf69b'
down_revision: Union[str, Sequence[str], None] = '706b2c881cab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema.

    - Adiciona coluna 'public_key' (Text, nullable) para armazenar a chave
      pública RSA PEM encriptada com AES-256-GCM (derivada do HWID).
    - Remove coluna 'session_key' que era usada para o mesmo propósito.
    - batch_alter_table é obrigatório porque o SQLite não suporta
      ALTER TABLE DROP COLUMN nativamente.
    """
    with op.batch_alter_table('configuracoes_licenca', schema=None) as batch_op:
        batch_op.add_column(sa.Column('public_key', sa.Text(), nullable=True))
        batch_op.drop_column('session_key')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('configuracoes_licenca', schema=None) as batch_op:
        batch_op.add_column(sa.Column('session_key', sa.TEXT(), nullable=False, server_default=''))
        batch_op.drop_column('public_key')
