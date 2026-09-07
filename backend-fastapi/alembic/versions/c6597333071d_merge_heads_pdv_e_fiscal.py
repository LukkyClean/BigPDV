"""merge heads pdv e fiscal

Revision ID: c6597333071d
Revises: d1a2b3c4e5f6, o8p9q0r1s2t3
Create Date: 2026-09-03 21:52:22.185875

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6597333071d'
down_revision: Union[str, Sequence[str], None] = ('d1a2b3c4e5f6', 'o8p9q0r1s2t3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
