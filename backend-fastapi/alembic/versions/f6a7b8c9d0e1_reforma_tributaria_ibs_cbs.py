"""adiciona campos da reforma tributária (IBS/CBS) em produto_fiscal e servico_fiscal

Revision ID: f6a7b8c9d0e1
Revises: d4e5f6a7b8c9
Create Date: 2026-08-15 12:00:00.000000

CONTEXTO:
A reforma tributária brasileira de 2026 introduz o IVA Dual (IBS + CBS),
substituindo ICMS, ISS, PIS e COFINS. Para evitar rejeição na SEFAZ, os
produtos e serviços precisam informar:

  - c_class_trib   — Código de Classificação Tributária IBS/CBS
  - cst_ibs_cbs    — CST exclusivo para IBS/CBS (3 dígitos)
  - aliquota_ibs   — Alíquota IBS em centésimos (500 = 5,00%)
  - aliquota_cbs   — Alíquota CBS em centésimos
  - c_benef        — Código de Benefício Fiscal IBS/CBS

Todos os campos são nullable (obrigatoriedade na service layer, na emissão).

NOTA: Os códigos CST IBS/CBS são baseados na legislação em tramitação e
precisarão ser atualizados quando a SEFAZ publicar a tabela definitiva.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_COLUNAS_REFORMA = [
    ("c_class_trib", sa.String(length=20)),
    ("cst_ibs_cbs", sa.String(length=3)),
    ("aliquota_ibs", sa.Integer()),
    ("aliquota_cbs", sa.Integer()),
    ("c_benef", sa.String(length=10)),
]

_TABELAS = ["produto_fiscal", "servico_fiscal"]


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def _tem_tabela(insp, tabela: str) -> bool:
    return insp.has_table(tabela)


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())

    for tabela in _TABELAS:
        if not _tem_tabela(insp, tabela):
            continue
        for nome, tipo in _COLUNAS_REFORMA:
            if not _tem_coluna(insp, tabela, nome):
                op.add_column(tabela, sa.Column(nome, tipo, nullable=True))


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())

    for tabela in _TABELAS:
        if not _tem_tabela(insp, tabela):
            continue
        for nome, _ in _COLUNAS_REFORMA:
            if _tem_coluna(insp, tabela, nome):
                op.drop_column(tabela, nome)
