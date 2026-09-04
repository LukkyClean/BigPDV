"""add aliquotas ao produto_fiscal e tabela aliquota_uf

Revision ID: k4l5m6n7o8p9
Revises: i2j3k4l5m6n7
Create Date: 2026-08-24 20:00:00.000000

CONTEXTO:
Fase 1 do FiscalTaxEngine — adiciona campos de alíquota ao produto_fiscal
(override por produto) e cria tabela aliquota_uf com defaults por UF.

Campos novos em produto_fiscal:
  - aliquota_icms, reducao_base_icms, codigo_beneficio_fiscal
  - aliquota_pis, aliquota_cofins, cst_pis, cst_cofins

Tabela nova aliquota_uf:
  - uf (PK), aliquota_icms_interna, aliquota_pis_padrao, aliquota_cofins_padrao
  - Seed data com as 27 UFs e alíquotas internas vigentes

SEGURANÇA:
Guarda por coluna/tabela → idempotente com create_all().
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'k4l5m6n7o8p9'
down_revision: Union[str, Sequence[str], None] = 'i2j3k4l5m6n7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELA_PRODUTO_FISCAL = "produto_fiscal"
TABELA_ALIQUOTA_UF = "aliquota_uf"


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    conn = op.get_bind()

    # --- 1. Adicionar colunas ao produto_fiscal ---
    if insp.has_table(TABELA_PRODUTO_FISCAL):
        colunas_novas = [
            ("aliquota_icms", sa.Integer()),
            ("reducao_base_icms", sa.Integer()),
            ("codigo_beneficio_fiscal", sa.String(10)),
            ("aliquota_pis", sa.Integer()),
            ("aliquota_cofins", sa.Integer()),
            ("cst_pis", sa.String(2)),
            ("cst_cofins", sa.String(2)),
        ]
        for col_nome, col_tipo in colunas_novas:
            if not _tem_coluna(insp, TABELA_PRODUTO_FISCAL, col_nome):
                op.add_column(
                    TABELA_PRODUTO_FISCAL,
                    sa.Column(col_nome, col_tipo, nullable=True),
                )

    # --- 2. Criar tabela aliquota_uf ---
    if not insp.has_table(TABELA_ALIQUOTA_UF):
        op.create_table(
            TABELA_ALIQUOTA_UF,
            sa.Column("uf", sa.String(2), primary_key=True),
            sa.Column("aliquota_icms_interna", sa.Integer(), nullable=False),
            sa.Column("aliquota_pis_padrao", sa.Integer(), nullable=False, server_default="165"),
            sa.Column("aliquota_cofins_padrao", sa.Integer(), nullable=False, server_default="760"),
        )

    # --- 3. Seed data (27 UFs com alíquotas internas vigentes em agosto/2026) ---
    count = conn.execute(sa.text(f"SELECT COUNT(*) FROM {TABELA_ALIQUOTA_UF}")).scalar()
    if count == 0:
        aliquota_uf_table = sa.table(
            TABELA_ALIQUOTA_UF,
            sa.column("uf", sa.String),
            sa.column("aliquota_icms_interna", sa.Integer),
            sa.column("aliquota_pis_padrao", sa.Integer),
            sa.column("aliquota_cofins_padrao", sa.Integer),
        )
        # Alíquotas ICMS internas padrão por UF (centésimos de pp)
        ALIQUOTAS_UF = {
            "AC": 1900, "AL": 1900, "AP": 1800, "AM": 2000, "BA": 2050,
            "CE": 2000, "DF": 2000, "ES": 1700, "GO": 1900, "MA": 2200,
            "MT": 1700, "MS": 1700, "MG": 1800, "PA": 1900, "PB": 2000,
            "PR": 1950, "PE": 2050, "PI": 2100, "RJ": 2200, "RN": 1800,
            "RS": 1700, "RO": 1950, "RR": 2000, "SC": 1700, "SP": 1800,
            "SE": 1900, "TO": 2000,
        }
        op.bulk_insert(
            aliquota_uf_table,
            [
                {
                    "uf": uf,
                    "aliquota_icms_interna": aliq,
                    "aliquota_pis_padrao": 165,
                    "aliquota_cofins_padrao": 760,
                }
                for uf, aliq in ALIQUOTAS_UF.items()
            ],
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())

    # --- 1. Remover tabela aliquota_uf ---
    if insp.has_table(TABELA_ALIQUOTA_UF):
        op.drop_table(TABELA_ALIQUOTA_UF)

    # --- 2. Remover colunas do produto_fiscal ---
    if insp.has_table(TABELA_PRODUTO_FISCAL):
        for col_nome in [
            "cst_cofins", "cst_pis", "aliquota_cofins", "aliquota_pis",
            "codigo_beneficio_fiscal", "reducao_base_icms", "aliquota_icms",
        ]:
            if _tem_coluna(insp, TABELA_PRODUTO_FISCAL, col_nome):
                op.drop_column(TABELA_PRODUTO_FISCAL, col_nome)
