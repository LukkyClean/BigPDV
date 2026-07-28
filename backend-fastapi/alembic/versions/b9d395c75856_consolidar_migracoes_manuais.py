"""consolidar_migracoes_manuais

Revision ID: b9d395c75856
Revises: 3718545bf69b
Create Date: 2026-07-06

Migração que consolida operações que existiam apenas no
_aplicar_migracoes() manual de tarefas.py:
  1. clientes.saldo_credito (INTEGER NOT NULL DEFAULT 0)
  2. configuracoes_licenca.bloqueada (BOOLEAN NOT NULL DEFAULT 0)
  3. Migração de dados: requer_pin_acessar_config_sensivel -> secoes_protegidas
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b9d395c75856'
down_revision: Union[str, Sequence[str], None] = '3718545bf69b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(f"PRAGMA table_info('{table_name}')"))
    columns = [row[1] for row in result.fetchall()]
    return column_name in columns


def upgrade() -> None:
    # 1. clientes.saldo_credito
    if not _column_exists('clientes', 'saldo_credito'):
        with op.batch_alter_table('clientes', schema=None) as batch_op:
            batch_op.add_column(
                sa.Column('saldo_credito', sa.Integer(), nullable=False, server_default='0')
            )

    # 2. configuracoes_licenca.bloqueada
    if not _column_exists('configuracoes_licenca', 'bloqueada'):
        with op.batch_alter_table('configuracoes_licenca', schema=None) as batch_op:
            batch_op.add_column(
                sa.Column('bloqueada', sa.Boolean(), nullable=False, server_default='0')
            )

    # 3. Migração de dados: requer_pin_acessar_config_sensivel -> secoes_protegidas
    if _column_exists('configuracoes_seguranca', 'requer_pin_acessar_config_sensivel'):
        conn = op.get_bind()
        conn.execute(sa.text(
            "UPDATE configuracoes_seguranca "
            "SET secoes_protegidas = '[\"regras-de-vendas\",\"financeiro-taxas\"]' "
            "WHERE requer_pin_acessar_config_sensivel = 1"
        ))


def downgrade() -> None:
    with op.batch_alter_table('configuracoes_licenca', schema=None) as batch_op:
        batch_op.drop_column('bloqueada')

    with op.batch_alter_table('clientes', schema=None) as batch_op:
        batch_op.drop_column('saldo_credito')
