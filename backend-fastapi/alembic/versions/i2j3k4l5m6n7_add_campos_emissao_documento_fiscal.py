"""add campos emissao documento_fiscal (ref_api, ambiente, tentativa_anterior)

Revision ID: i2j3k4l5m6n7
Revises: f44a5daad28c
Create Date: 2026-08-21 10:00:00.000000

CONTEXTO:
Adiciona colunas para integração com API de emissão e cadeia de tentativas.
- ref_api: referência única enviada à API (idempotência)
- ambiente_emissao: 1=Produção, 2=Homologação (registra em qual ambiente foi emitido)
- tentativa_anterior_id: FK self-referencing para linked list de tentativas

SEGURANÇA:
Guarda por coluna (_tem_coluna) → idempotente com create_all().
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'i2j3k4l5m6n7'
down_revision: Union[str, Sequence[str], None] = 'f44a5daad28c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELA = "documento_fiscal"


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    colunas = [c["name"] for c in insp.get_columns(tabela)]
    return coluna in colunas


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())

    if not insp.has_table(TABELA):
        return

    if not _tem_coluna(insp, TABELA, "ref_api"):
        op.add_column(TABELA, sa.Column("ref_api", sa.String(50), nullable=True))
        op.create_index("ix_documento_fiscal_ref_api", TABELA, ["ref_api"], unique=True)

    if not _tem_coluna(insp, TABELA, "ambiente_emissao"):
        op.add_column(TABELA, sa.Column("ambiente_emissao", sa.Integer(), nullable=True))

    if not _tem_coluna(insp, TABELA, "tentativa_anterior_id"):
        # SQLite não suporta ALTER TABLE ADD CONSTRAINT FK.
        # Adicionamos como Integer simples; o create_all() de instalação nova
        # já cria com FK. Em bancos existentes a FK é apenas lógica (app-level).
        op.add_column(
            TABELA,
            sa.Column("tentativa_anterior_id", sa.Integer(), nullable=True),
        )
        op.create_index(
            "ix_documento_fiscal_tentativa_anterior_id",
            TABELA,
            ["tentativa_anterior_id"],
            unique=False,
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())

    if not insp.has_table(TABELA):
        return

    if _tem_coluna(insp, TABELA, "tentativa_anterior_id"):
        op.drop_index("ix_documento_fiscal_tentativa_anterior_id", table_name=TABELA)
        op.drop_column(TABELA, "tentativa_anterior_id")

    if _tem_coluna(insp, TABELA, "ambiente_emissao"):
        op.drop_column(TABELA, "ambiente_emissao")

    if _tem_coluna(insp, TABELA, "ref_api"):
        op.drop_index("ix_documento_fiscal_ref_api", table_name=TABELA)
        op.drop_column(TABELA, "ref_api")
