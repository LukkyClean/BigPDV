"""adiciona codigo_sefaz em formas_pagamento

Revision ID: g1h2i3j4k5l6
Revises: f6a7b8c9d0e1
Create Date: 2026-08-17 10:00:00.000000

CONTEXTO:
NFe/NFCe exige código padronizado do SEFAZ para forma de pagamento (tPag).
O campo codigo_sefaz armazena o código de 2 dígitos (01=Dinheiro, 03=Cartão
Crédito, 04=Cartão Débito, 05=Crédito Loja, 15=Boleto, 17=PIX, 99=Outros).

O campo é nullable — a obrigatoriedade é validada apenas no gate de emissão.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'g1h2i3j4k5l6'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())

    if not _tem_coluna(insp, "formas_pagamento", "codigo_sefaz"):
        op.add_column(
            "formas_pagamento",
            sa.Column("codigo_sefaz", sa.String(length=2), nullable=True),
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())

    if _tem_coluna(insp, "formas_pagamento", "codigo_sefaz"):
        op.drop_column("formas_pagamento", "codigo_sefaz")
