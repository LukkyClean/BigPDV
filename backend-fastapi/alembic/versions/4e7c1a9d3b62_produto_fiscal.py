"""cria tabela produto_fiscal (dados fiscais de produto)

Revision ID: 4e7c1a9d3b62
Revises: 6d82ff46977e
Create Date: 2026-08-13 00:00:00.000000

CONTEXTO:
Fase 1 do módulo fiscal. Cria a tabela satélite 'produto_fiscal' com relação
1:1 opcional com 'produtos'. Nenhum campo fiscal é NOT NULL — a obrigatoriedade
é verificada na service layer, apenas no momento de emissão. Isso garante que
o sistema continue intacto para empresas sem o módulo fiscal ativo.

SEGURANÇA (banco de cliente em produção):
- Guarda de existência por tabela → idempotente. O create_all() roda antes das
  migrations no startup: em instalação nova a tabela já nasce e o CREATE TABLE
  falharia sem essa verificação.
- FK com CASCADE DELETE: excluir um produto remove automaticamente seus dados
  fiscais, sem deixar registros órfãos.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4e7c1a9d3b62'
down_revision: Union[str, Sequence[str], None] = '6d82ff46977e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tem_tabela(insp, tabela: str) -> bool:
    return insp.has_table(tabela)


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())

    if not _tem_tabela(insp, "produto_fiscal"):
        op.create_table(
            "produto_fiscal",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("produto_id", sa.Integer(), nullable=False),
            # Campos fiscais — todos nullable (obrigatoriedade na service layer)
            sa.Column("ncm", sa.String(length=8), nullable=True),
            sa.Column("cest", sa.String(length=7), nullable=True),
            sa.Column("cfop_padrao", sa.String(length=4), nullable=True),
            sa.Column("origem_mercadoria", sa.Integer(), nullable=True),
            sa.Column("unidade_tributavel", sa.String(length=6), nullable=True),
            sa.Column("gtin_tributavel", sa.String(length=14), nullable=True),
            sa.Column("cst_icms", sa.String(length=3), nullable=True),
            sa.Column("csosn", sa.String(length=3), nullable=True),
            sa.Column(
                "data_atualizacao",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
            ),
            sa.ForeignKeyConstraint(
                ["produto_id"],
                ["produtos.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_produto_fiscal_id",
            "produto_fiscal",
            ["id"],
            unique=False,
        )
        op.create_index(
            "ix_produto_fiscal_produto_id",
            "produto_fiscal",
            ["produto_id"],
            unique=True,  # garante a unicidade da relação 1:1
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())

    if _tem_tabela(insp, "produto_fiscal"):
        op.drop_index("ix_produto_fiscal_produto_id", table_name="produto_fiscal")
        op.drop_index("ix_produto_fiscal_id", table_name="produto_fiscal")
        op.drop_table("produto_fiscal")
