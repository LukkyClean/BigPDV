"""cria tabela servico_fiscal (dados fiscais de serviço)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-13 00:00:00.000000

CONTEXTO:
Fase 2 do módulo fiscal. Cria a tabela satélite 'servico_fiscal' com relação
1:1 opcional com 'servicos'. Campos voltados a NFSe (LC 116/2003, CNAE, ISS).
Nenhum campo fiscal é NOT NULL — a obrigatoriedade é verificada na service
layer, apenas no momento de emissão.

SEGURANÇA (banco de cliente em produção):
- Guarda de existência por tabela → idempotente. O create_all() roda antes das
  migrations no startup: em instalação nova a tabela já nasce e o CREATE TABLE
  falharia sem essa verificação.
- FK com CASCADE DELETE: excluir um serviço remove automaticamente seus dados
  fiscais, sem deixar registros órfãos.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a8c4d02b5e31'
down_revision: Union[str, Sequence[str], None] = 'f7b3c91a4d20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tem_tabela(insp, tabela: str) -> bool:
    return insp.has_table(tabela)


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())

    if not _tem_tabela(insp, "servico_fiscal"):
        op.create_table(
            "servico_fiscal",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("servico_id", sa.Integer(), nullable=False),
            # Campos NFSe — todos nullable (obrigatoriedade na service layer)
            sa.Column("codigo_servico_lc116", sa.String(length=10), nullable=True),
            sa.Column("cnae", sa.String(length=7), nullable=True),
            sa.Column("aliquota_iss", sa.Integer(), nullable=True),
            sa.Column("codigo_tributacao_municipio", sa.String(length=20), nullable=True),
            # Campos NF-e (nota mista)
            sa.Column("cfop_padrao", sa.String(length=4), nullable=True),
            sa.Column("cst_icms", sa.String(length=3), nullable=True),
            sa.Column("csosn", sa.String(length=3), nullable=True),
            sa.Column("unidade_tributavel", sa.String(length=6), nullable=True),
            sa.Column(
                "data_atualizacao",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
            ),
            sa.ForeignKeyConstraint(
                ["servico_id"],
                ["servicos.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_servico_fiscal_id",
            "servico_fiscal",
            ["id"],
            unique=False,
        )
        op.create_index(
            "ix_servico_fiscal_servico_id",
            "servico_fiscal",
            ["servico_id"],
            unique=True,  # garante a unicidade da relação 1:1
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())

    if _tem_tabela(insp, "servico_fiscal"):
        op.drop_index("ix_servico_fiscal_servico_id", table_name="servico_fiscal")
        op.drop_index("ix_servico_fiscal_id", table_name="servico_fiscal")
        op.drop_table("servico_fiscal")
