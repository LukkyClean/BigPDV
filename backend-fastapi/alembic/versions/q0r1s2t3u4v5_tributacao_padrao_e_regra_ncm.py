"""cria tributacao_padrao e regra_tributaria_ncm

Revision ID: q0r1s2t3u4v5
Revises: p9q0r1s2t3u4
Create Date: 2026-09-12 11:05:00.000000

CONTEXTO:
A tributação sai do produto e passa a ter três níveis:

    produto (exceção)  →  regra por NCM  →  tributação padrão da loja

CSOSN, CFOP, origem e CST de PIS/COFINS são a mesma resposta para a loja
inteira, e eram perguntados em cada produto. Nenhum sistema profissional faz
assim (ver docs/cadastro-produto-plano.md §3.2).

MIGRAÇÃO DE DADOS: NENHUMA, DE PROPÓSITO.
As duas tabelas nascem VAZIAS. Enquanto estiverem vazias, a cascata não tem o
que completar e `fiscal_efetivo()` devolve o próprio `produto_fiscal` — as
lojas que já emitem continuam idênticas. O padrão da loja é criado quando o
dono confirmar, na tela, o que o motor de derivação sugerir.

Nada de `produto_fiscal` é apagado ou movido: o que já está lá continua
valendo, como exceção do produto, que é o nível mais forte da cascata.

SEGURANÇA:
- Decide pela ausência da TABELA: se o create_all() do startup já as criou,
  esta migração não faz nada.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'q0r1s2t3u4v5'
down_revision: Union[str, Sequence[str], None] = 'p9q0r1s2t3u4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _colunas_de_tributacao() -> list[sa.Column]:
    """Os campos que se repetem no catálogo — iguais nas duas tabelas."""
    return [
        sa.Column("cfop_padrao", sa.String(length=4), nullable=True),
        sa.Column("origem_mercadoria", sa.Integer(), nullable=True),
        sa.Column("cst_icms", sa.String(length=3), nullable=True),
        sa.Column("csosn", sa.String(length=3), nullable=True),
        sa.Column("aliquota_icms", sa.Integer(), nullable=True),
        sa.Column("reducao_base_icms", sa.Integer(), nullable=True),
        sa.Column("codigo_beneficio_fiscal", sa.String(length=10), nullable=True),
        sa.Column("cst_pis", sa.String(length=2), nullable=True),
        sa.Column("cst_cofins", sa.String(length=2), nullable=True),
        sa.Column("aliquota_pis", sa.Integer(), nullable=True),
        sa.Column("aliquota_cofins", sa.Integer(), nullable=True),
        sa.Column("c_class_trib", sa.String(length=20), nullable=True),
        sa.Column("cst_ibs_cbs", sa.String(length=3), nullable=True),
        sa.Column("aliquota_ibs", sa.Integer(), nullable=True),
        sa.Column("aliquota_cbs", sa.Integer(), nullable=True),
        sa.Column("c_benef", sa.String(length=10), nullable=True),
    ]


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tabelas = set(insp.get_table_names())

    if "tributacao_padrao" not in tabelas:
        op.create_table(
            "tributacao_padrao",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("empresa_id", sa.Integer(), nullable=False),
            *_colunas_de_tributacao(),
            sa.Column("confirmado_em", sa.DateTime(), nullable=True),
            sa.Column("confirmado_por", sa.String(length=120), nullable=True),
            sa.Column("data_atualizacao", sa.DateTime(), nullable=False,
                      server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("empresa_id", name="uq_tributacao_padrao_empresa"),
        )
        op.create_index("ix_tributacao_padrao_empresa_id", "tributacao_padrao", ["empresa_id"])

    if "regra_tributaria_ncm" not in tabelas:
        op.create_table(
            "regra_tributaria_ncm",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("empresa_id", sa.Integer(), nullable=False),
            sa.Column("ncm", sa.String(length=8), nullable=False),
            sa.Column("cest", sa.String(length=7), nullable=True),
            sa.Column("descricao", sa.String(length=120), nullable=True),
            *_colunas_de_tributacao(),
            sa.Column("data_atualizacao", sa.DateTime(), nullable=False,
                      server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("empresa_id", "ncm", name="uq_regra_tributaria_empresa_ncm"),
        )
        op.create_index("ix_regra_tributaria_ncm_empresa_id", "regra_tributaria_ncm", ["empresa_id"])
        op.create_index("ix_regra_tributaria_ncm_ncm", "regra_tributaria_ncm", ["ncm"])


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    tabelas = set(insp.get_table_names())

    if "regra_tributaria_ncm" in tabelas:
        op.drop_table("regra_tributaria_ncm")
    if "tributacao_padrao" in tabelas:
        op.drop_table("tributacao_padrao")
