"""cria tabela documento_fiscal (documentos fiscais emitidos)

Revision ID: h1i2j3k4l5m6
Revises: g1h2i3j4k5l6
Create Date: 2026-08-17 14:00:00.000000

CONTEXTO:
Tabela unificada de documentos fiscais emitidos, usada pelo Centro Fiscal.
Registra cada emissão (NFe, NFCe, NFSe) com referência polimórfica à origem
(Venda ou Ordem de Serviço). Todos os campos de resultado são nullable —
preenchidos pelo retorno da Focus NFe.

SEGURANÇA (banco de cliente em produção):
- Guarda de existência por tabela → idempotente. O create_all() roda antes das
  migrations no startup: em instalação nova a tabela já nasce e o CREATE TABLE
  falharia sem essa verificação.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'h1i2j3k4l5m6'
down_revision: Union[str, Sequence[str], None] = 'g1h2i3j4k5l6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tem_tabela(insp, tabela: str) -> bool:
    return insp.has_table(tabela)


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())

    if not _tem_tabela(insp, "documento_fiscal"):
        op.create_table(
            "documento_fiscal",
            sa.Column("id", sa.Integer(), nullable=False),
            # Tipo e origem polimórfica
            sa.Column("tipo_documento", sa.String(length=5), nullable=False),
            sa.Column("origem_tipo", sa.String(length=15), nullable=False),
            sa.Column("origem_id", sa.Integer(), nullable=True),
            sa.Column("origem_numero_os", sa.String(length=20), nullable=True),
            # Status
            sa.Column("status", sa.String(length=15), nullable=False, server_default="PENDENTE"),
            # Dados do documento
            sa.Column("chave_acesso", sa.String(length=44), nullable=True),
            sa.Column("numero_documento", sa.Integer(), nullable=True),
            sa.Column("serie", sa.Integer(), nullable=True),
            sa.Column("protocolo_autorizacao", sa.String(length=20), nullable=True),
            sa.Column("data_autorizacao", sa.DateTime(), nullable=True),
            # Arquivos
            sa.Column("url_pdf", sa.String(length=500), nullable=True),
            sa.Column("url_xml", sa.String(length=500), nullable=True),
            # SEFAZ feedback
            sa.Column("mensagem_sefaz", sa.String(length=500), nullable=True),
            sa.Column("codigo_status_sefaz", sa.Integer(), nullable=True),
            sa.Column("motivo_rejeicao", sa.Text(), nullable=True),
            # Valor total (centavos)
            sa.Column("valor_total", sa.Integer(), nullable=True),
            # Timestamps
            sa.Column("data_emissao", sa.DateTime(), nullable=True),
            sa.Column(
                "data_criacao",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
            ),
            sa.Column(
                "data_atualizacao",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_documento_fiscal_id", "documento_fiscal", ["id"], unique=False)
        op.create_index("ix_documento_fiscal_status", "documento_fiscal", ["status"], unique=False)
        op.create_index("ix_documento_fiscal_origem_id", "documento_fiscal", ["origem_id"], unique=False)
        op.create_index("ix_documento_fiscal_origem_numero_os", "documento_fiscal", ["origem_numero_os"], unique=False)
        op.create_index("ix_documento_fiscal_tipo_documento", "documento_fiscal", ["tipo_documento"], unique=False)


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())

    if _tem_tabela(insp, "documento_fiscal"):
        op.drop_index("ix_documento_fiscal_tipo_documento", table_name="documento_fiscal")
        op.drop_index("ix_documento_fiscal_origem_numero_os", table_name="documento_fiscal")
        op.drop_index("ix_documento_fiscal_origem_id", table_name="documento_fiscal")
        op.drop_index("ix_documento_fiscal_status", table_name="documento_fiscal")
        op.drop_index("ix_documento_fiscal_id", table_name="documento_fiscal")
        op.drop_table("documento_fiscal")
