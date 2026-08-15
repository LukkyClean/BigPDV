"""update sale tables

Revision ID: 7107971665b1
Revises: 5cf42db01be6
Create Date: 2026-04-21 09:36:39.763150

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7107971665b1'
down_revision: Union[str, Sequence[str], None] = '5cf42db01be6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('vendas', schema=None) as batch_op:
        batch_op.alter_column('status',
               existing_type=sa.VARCHAR(length=9),
               type_=sa.Enum('RASCUNHO', 'FINALIZADA', 'CANCELADA', name='vendastatus'),
               existing_nullable=False)
        
        # Adicione estas duas linhas para remover explicitamente as constraints
        batch_op.drop_constraint('ck_venda_adiantamento_nao_negativo', type_='check')
        batch_op.drop_constraint('ck_venda_desconto_nao_negativo', type_='check')
        
        batch_op.drop_column('adiantamento')
        batch_op.drop_column('desconto')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('vendas', schema=None) as batch_op:
        batch_op.add_column(sa.Column('desconto', sa.INTEGER(), nullable=False))
        batch_op.add_column(sa.Column('adiantamento', sa.INTEGER(), nullable=False))
        
        # Restaura as constraints em caso de rollback
        batch_op.create_check_constraint('ck_venda_adiantamento_nao_negativo', 'adiantamento >= 0')
        batch_op.create_check_constraint('ck_venda_desconto_nao_negativo', 'desconto >= 0')
        
        batch_op.alter_column('status',
               existing_type=sa.Enum('RASCUNHO', 'FINALIZADA', 'CANCELADA', name='vendastatus'),
               type_=sa.VARCHAR(length=9),
               existing_nullable=False)

    # ### end Alembic commands ###
