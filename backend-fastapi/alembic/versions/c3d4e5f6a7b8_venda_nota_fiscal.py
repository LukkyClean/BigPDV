"""cria tabela venda_nota_fiscal (nota fiscal por venda)

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-13 00:00:00.000000

CONTEXTO:
Fase 3 do módulo fiscal. Cria a tabela satélite 'venda_nota_fiscal' com relação
1:1 opcional com 'vendas'. Armazena dois tipos de dados:
- Parâmetros de entrada para emissão NF-e/NFC-e (natureza_operacao, finalidade…)
- Resultados da emissão Focus NFe (chave_acesso, protocolo, status…)

A emissão real via Focus NFe é fase futura. Esta migration apenas cria a
estrutura de dados. Nenhum campo é NOT NULL exceto venda_id.

SEGURANÇA (banco de cliente em produção):
- Guarda de existência por tabela → idempotente.
- FK com CASCADE DELETE: excluir uma venda remove automaticamente a nota fiscal,
  sem deixar registros órfãos.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tem_tabela(insp, tabela: str) -> bool:
    return insp.has_table(tabela)


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())

    if not _tem_tabela(insp, "venda_nota_fiscal"):
        op.create_table(
            "venda_nota_fiscal",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("venda_id", sa.Integer(), nullable=False),
            # Parâmetros de entrada
            sa.Column("natureza_operacao", sa.String(length=60), nullable=True),
            sa.Column("finalidade_emissao", sa.Integer(), nullable=True),
            sa.Column("consumidor_final", sa.Boolean(), nullable=True),
            sa.Column("indicador_presenca", sa.Integer(), nullable=True),
            # Resultados (Focus NFe — fase futura)
            sa.Column("status_nota", sa.String(length=20), nullable=True, server_default="PENDENTE"),
            sa.Column("chave_acesso", sa.String(length=44), nullable=True),
            sa.Column("numero_nota", sa.Integer(), nullable=True),
            sa.Column("serie", sa.Integer(), nullable=True),
            sa.Column("protocolo_autorizacao", sa.String(length=20), nullable=True),
            sa.Column("data_autorizacao", sa.DateTime(), nullable=True),
            sa.Column("url_danfe", sa.String(length=500), nullable=True),
            sa.Column("mensagem_sefaz", sa.String(length=500), nullable=True),
            sa.Column("qrcode", sa.Text(), nullable=True),
            sa.Column(
                "data_atualizacao",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
            ),
            sa.ForeignKeyConstraint(
                ["venda_id"],
                ["vendas.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_venda_nota_fiscal_id",
            "venda_nota_fiscal",
            ["id"],
            unique=False,
        )
        op.create_index(
            "ix_venda_nota_fiscal_venda_id",
            "venda_nota_fiscal",
            ["venda_id"],
            unique=True,  # garante a unicidade da relação 1:1
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())

    if _tem_tabela(insp, "venda_nota_fiscal"):
        op.drop_index("ix_venda_nota_fiscal_venda_id", table_name="venda_nota_fiscal")
        op.drop_index("ix_venda_nota_fiscal_id", table_name="venda_nota_fiscal")
        op.drop_table("venda_nota_fiscal")
