"""onda2 aprovacao e garantia por item de OS

Revision ID: ab4637c30835
Revises: 965c71a2da9a
Create Date: 2026-07-11 15:44:34.669800

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab4637c30835'
down_revision: Union[str, Sequence[str], None] = '965c71a2da9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def upgrade() -> None:
    """Onda 2: aprovacao e garantia por item de OS.

    Adiciona em ordem_servico_itens:
      - status_aprovacao (NOT NULL, default APROVADO -> linhas existentes ficam
        APROVADO, preservando o comportamento atual do total).
      - garantia_dias, garantia_km (nullable, opcionais).

    Guardas de idempotencia: create_all pode ter criado as colunas numa base nova.
    """
    conn = op.get_bind()
    insp = sa.inspect(conn)

    with op.batch_alter_table("ordem_servico_itens", schema=None) as batch_op:
        if not _tem_coluna(insp, "ordem_servico_itens", "status_aprovacao"):
            batch_op.add_column(sa.Column(
                "status_aprovacao",
                sa.Enum("PENDENTE", "APROVADO", "REPROVADO", name="ordemservicoitemaprovacao"),
                nullable=False,
                server_default="APROVADO",
            ))
        if not _tem_coluna(insp, "ordem_servico_itens", "garantia_dias"):
            batch_op.add_column(sa.Column("garantia_dias", sa.Integer(), nullable=True))
        if not _tem_coluna(insp, "ordem_servico_itens", "garantia_km"):
            batch_op.add_column(sa.Column("garantia_km", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Remove as colunas adicionadas na Onda 2."""
    conn = op.get_bind()
    insp = sa.inspect(conn)

    with op.batch_alter_table("ordem_servico_itens", schema=None) as batch_op:
        if _tem_coluna(insp, "ordem_servico_itens", "garantia_km"):
            batch_op.drop_column("garantia_km")
        if _tem_coluna(insp, "ordem_servico_itens", "garantia_dias"):
            batch_op.drop_column("garantia_dias")
        if _tem_coluna(insp, "ordem_servico_itens", "status_aprovacao"):
            batch_op.drop_column("status_aprovacao")
