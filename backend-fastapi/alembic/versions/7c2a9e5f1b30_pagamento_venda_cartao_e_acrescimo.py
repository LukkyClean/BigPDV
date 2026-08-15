"""pagamento de venda: bandeira/vencimento/detalhes + acrescimo na venda

Revision ID: 7c2a9e5f1b30
Revises: 62d130ac4856
Create Date: 2026-07-20 10:00:00.000000

Traz o pagamento de venda para o mesmo nivel do pagamento de OS:
  pagamentos_venda:  + bandeira_cartao, + vencimento, + detalhes (JSON)
  vendas:            + acrescimo (juros/cartao aplicado no checkout)

Todas as colunas sao aditivas e nullable (acrescimo NOT NULL com default 0),
portanto seguras para o banco de producao existente (ADD COLUMN nativo do
SQLite, sem recriar a tabela).

Corrige tambem a CHECK bugada de parcelamento em pagamentos_venda, que exigia
'parcelado IS FALSE' e portanto rejeitava qualquer pagamento parcelado. Isso so
e aplicado se a constraint antiga estiver de fato presente (rebuild via batch).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c2a9e5f1b30'
down_revision: Union[str, Sequence[str], None] = '62d130ac4856'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tem_tabela(insp, nome: str) -> bool:
    return nome in insp.get_table_names()


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def _check_bugado(insp) -> bool:
    """True se a CHECK antiga (que exige parcelado FALSO) ainda estiver na tabela."""
    try:
        checks = insp.get_check_constraints("pagamentos_venda")
    except Exception:
        return False
    for c in checks:
        if c.get("name") == "ck_pagamento_venda_parcelas_min_1":
            texto = (c.get("sqltext") or "").upper()
            return "IS FALSE" in texto
    return False


def upgrade() -> None:
    """Colunas aditivas de pagamento de venda + acrescimo (nullable/seguras)."""
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # 1) pagamentos_venda: campos de cartao/boleto/transferencia (ADD COLUMN nativo)
    if _tem_tabela(insp, "pagamentos_venda"):
        if not _tem_coluna(insp, "pagamentos_venda", "bandeira_cartao"):
            op.add_column("pagamentos_venda", sa.Column("bandeira_cartao", sa.String(length=50), nullable=True))
        if not _tem_coluna(insp, "pagamentos_venda", "vencimento"):
            op.add_column("pagamentos_venda", sa.Column("vencimento", sa.Date(), nullable=True))
        if not _tem_coluna(insp, "pagamentos_venda", "detalhes"):
            op.add_column("pagamentos_venda", sa.Column("detalhes", sa.JSON(), nullable=True))

    # 2) vendas: acrescimo de juros aplicado no checkout
    if _tem_tabela(insp, "vendas") and not _tem_coluna(insp, "vendas", "acrescimo"):
        op.add_column("vendas", sa.Column("acrescimo", sa.Integer(), nullable=False, server_default="0"))

    # 3) Corrige a CHECK de parcelamento (rebuild via batch), apenas se a antiga existir
    if _tem_tabela(insp, "pagamentos_venda") and _check_bugado(insp):
        with op.batch_alter_table("pagamentos_venda", schema=None) as batch_op:
            batch_op.drop_constraint("ck_pagamento_venda_parcelas_min_1", type_="check")
            batch_op.create_check_constraint(
                "ck_pagamento_venda_parcelas_min_1",
                "(NOT parcelado AND qtd_parcelas IS NULL) OR (parcelado AND qtd_parcelas >= 1)",
            )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if _tem_tabela(insp, "vendas") and _tem_coluna(insp, "vendas", "acrescimo"):
        op.drop_column("vendas", "acrescimo")

    if _tem_tabela(insp, "pagamentos_venda"):
        if _tem_coluna(insp, "pagamentos_venda", "detalhes"):
            op.drop_column("pagamentos_venda", "detalhes")
        if _tem_coluna(insp, "pagamentos_venda", "vencimento"):
            op.drop_column("pagamentos_venda", "vencimento")
        if _tem_coluna(insp, "pagamentos_venda", "bandeira_cartao"):
            op.drop_column("pagamentos_venda", "bandeira_cartao")
