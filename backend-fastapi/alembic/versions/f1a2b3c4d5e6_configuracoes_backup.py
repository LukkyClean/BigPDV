"""configuracoes_backup

Backup automatico agendado (frequencia + horario escolhidos pelo lojista).

Equivale a `d6adbf5b3d66` do master, reescrita para a cadeia desta branch: la a
migracao pende de um baseline unico (`b386f0ba5efd`) que nao existe aqui. Trazer
o arquivo do master criaria uma SEGUNDA raiz Alembic, e o `upgrade("head")` do
boot morreria com "Multiple head revisions" em todo cliente instalado.

Guarda pela presenca da tabela porque o `create_all()` roda ANTES das migracoes
no startup (ver core/tarefas.py e CLAUDE.md): num banco novo a tabela ja chega
criada e o create_table falharia.

Revision ID: f1a2b3c4d5e6
Revises: e4f5a6b7c8d9
Create Date: 2026-08-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELA = "configuracoes_backup"


def _tabela_existe(nome: str) -> bool:
    return nome in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if _tabela_existe(TABELA):
        return

    op.create_table(
        TABELA,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("backup_automatico_ativo", sa.Boolean(), nullable=False),
        sa.Column("frequencia", sa.String(length=20), nullable=False),
        sa.Column("horario", sa.String(length=5), nullable=False),
        sa.Column("data_atualizacao", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("empresa_id"),
    )
    with op.batch_alter_table(TABELA, schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_configuracoes_backup_id"), ["id"], unique=False)


def downgrade() -> None:
    if not _tabela_existe(TABELA):
        return

    with op.batch_alter_table(TABELA, schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_configuracoes_backup_id"))

    op.drop_table(TABELA)
