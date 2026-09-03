"""cria tabela inutilizacao_fiscal

Revision ID: n7o8p9q0r1s2
Revises: m6n7o8p9q0r1
Create Date: 2026-09-02 19:00:00.000000

CONTEXTO:
Desde que a emissão parou de devolver o número ao contador quando a
transmissão falha, buraco na sequência virou resultado esperado — é o preço
de nunca arriscar Rejeição 204. A contrapartida é declarar esses números à
SEFAZ como inutilizados, e esta tabela guarda esses pedidos.

SEGURANÇA:
- Decide pela ausência da TABELA: se o create_all() do startup já a criou,
  não há nada a fazer.
- Tabela nova, sem backfill: nenhuma linha existente é tocada.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'n7o8p9q0r1s2'
down_revision: Union[str, Sequence[str], None] = 'm6n7o8p9q0r1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABELA = "inutilizacao_fiscal"


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if insp.has_table(TABELA):
        return

    op.create_table(
        TABELA,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("modelo", sa.Integer(), nullable=False, server_default="55"),
        sa.Column("serie", sa.Integer(), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("numero_inicial", sa.Integer(), nullable=False),
        sa.Column("numero_final", sa.Integer(), nullable=False),
        sa.Column("justificativa", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=15), nullable=False, server_default="PENDENTE"),
        sa.Column("protocolo", sa.String(length=20), nullable=True),
        sa.Column("mensagem_sefaz", sa.String(length=500), nullable=True),
        sa.Column("codigo_status_sefaz", sa.Integer(), nullable=True),
        sa.Column("url_xml", sa.String(length=500), nullable=True),
        sa.Column("ref_api", sa.String(length=50), nullable=True),
        sa.Column("idempotency_key", sa.String(length=36), nullable=True),
        sa.Column("ambiente_emissao", sa.Integer(), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("data_solicitacao", sa.DateTime(), nullable=True),
        sa.Column("data_homologacao", sa.DateTime(), nullable=True),
        sa.Column("data_criacao", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("data_atualizacao", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "empresa_id", "serie", "ano", "numero_inicial", "numero_final",
            name="uq_inutilizacao_faixa",
        ),
    )
    op.create_index(f"ix_{TABELA}_id", TABELA, ["id"])
    op.create_index(f"ix_{TABELA}_empresa_id", TABELA, ["empresa_id"])
    op.create_index(f"ix_{TABELA}_status", TABELA, ["status"])
    op.create_index(f"ix_{TABELA}_ref_api", TABELA, ["ref_api"], unique=True)
    op.create_index(f"ix_{TABELA}_idempotency_key", TABELA, ["idempotency_key"], unique=True)


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not insp.has_table(TABELA):
        return

    op.drop_table(TABELA)
