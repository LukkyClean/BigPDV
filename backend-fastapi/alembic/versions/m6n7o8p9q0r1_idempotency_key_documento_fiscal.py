"""adiciona documento_fiscal.idempotency_key

Revision ID: m6n7o8p9q0r1
Revises: 86e916edd50b
Create Date: 2026-09-02 18:00:00.000000

CONTEXTO:
Sem uma chave estável por tentativa de emissão, a retentativa do operador após
um timeout de rede chega à API intermediária como uma emissão nova — risco de
duas notas válidas para a mesma venda. A coluna guarda um UUID gerado ANTES do
disparo HTTP, reenviado em X-Idempotency-Key.

SEGURANÇA:
- Decide pela AUSÊNCIA da coluna, não pela presença da tabela: no startup o
  create_all() já pode ter criado documento_fiscal com a coluna nova, e nesse
  caso não há nada a fazer (ver CLAUDE.md).
- Coluna nullable: os documentos já emitidos ficam sem chave, o que é correto —
  eles não serão retransmitidos.
- O índice único é criado à parte para poder ser removido no downgrade.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'm6n7o8p9q0r1'
down_revision: Union[str, Sequence[str], None] = '86e916edd50b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABELA = "documento_fiscal"
COLUNA = "idempotency_key"
INDICE = "ix_documento_fiscal_idempotency_key"


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not insp.has_table(TABELA):
        return

    colunas = {c["name"] for c in insp.get_columns(TABELA)}
    if COLUNA in colunas:
        return

    op.add_column(TABELA, sa.Column(COLUNA, sa.String(36), nullable=True))
    op.create_index(INDICE, TABELA, [COLUNA], unique=True)


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not insp.has_table(TABELA):
        return

    colunas = {c["name"] for c in insp.get_columns(TABELA)}
    if COLUNA not in colunas:
        return

    indices = {i["name"] for i in insp.get_indexes(TABELA)}
    if INDICE in indices:
        op.drop_index(INDICE, table_name=TABELA)

    op.drop_column(TABELA, COLUNA)
