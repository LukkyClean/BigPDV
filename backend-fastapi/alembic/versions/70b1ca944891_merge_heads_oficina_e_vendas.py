"""merge_heads_oficina_e_vendas

Revision ID: 70b1ca944891
Revises: 62d130ac4856, a978a58b6d5d
Create Date: 2026-07-20 16:36:32.478673

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70b1ca944891'
down_revision: Union[str, Sequence[str], None] = ('62d130ac4856', 'a978a58b6d5d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
