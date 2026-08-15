"""merge heads: pagamento venda e oficina/vendas

Revision ID: 97dd6ac91792
Revises: 70b1ca944891, 7c2a9e5f1b30
Create Date: 2026-07-22 16:31:49.590718

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '97dd6ac91792'
down_revision: Union[str, Sequence[str], None] = ('70b1ca944891', '7c2a9e5f1b30')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
