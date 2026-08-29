"""alertas dispensados (snooze do painel de atencao)

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-08-29 12:40:00.000000

Cria `alertas_dispensados`: o alerta que o dono mandou calar, ate uma data.

E o snooze do portlet de lembretes do NetSuite, e e a peca que decide se um
painel de alertas sobrevive ao segundo mes. Sem ela, "R$ 300 gastos sem
categoria" grita todo dia para quem ja decidiu nao categorizar -- e quando o
dono aprende a ignorar o painel, some junto o aviso que importava.

ADIAR, NUNCA APAGAR: nao ha "dispensar para sempre". Alerta financeiro que
some de vez vira problema escondido. O prazo devolve o aviso a tela, e se o
problema tiver sido resolvido no meio tempo ele nem reaparece.

Uma linha por empresa/codigo (UNIQUE): o alerta e da LOJA, nao de quem clicou.

Tabela nova e isolada -- nenhuma linha existente muda de significado, e loja
que nunca clicar em "adiar" nunca tera uma linha aqui.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6e7f8a9b0c1'
down_revision: Union[str, Sequence[str], None] = 'c5d6e7f8a9b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # Defensiva contra o create_all() do boot, que roda ANTES das migrations:
    # num banco novo a tabela ja nasce pronta.
    if "alertas_dispensados" in insp.get_table_names():
        return

    op.create_table(
        "alertas_dispensados",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=40), nullable=False),
        sa.Column("dispensado_ate", sa.Date(), nullable=False),
        sa.Column("funcionario_id", sa.Integer(), nullable=True),
        sa.Column("funcionario_nome", sa.String(length=255), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["funcionario_id"], ["funcionarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("empresa_id", "codigo", name="uq_alerta_dispensado_empresa_codigo"),
    )
    op.create_index("ix_alertas_dispensados_empresa_id", "alertas_dispensados", ["empresa_id"])
    op.create_index("ix_alertas_dispensados_dispensado_ate", "alertas_dispensados", ["dispensado_ate"])


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "alertas_dispensados" in insp.get_table_names():
        op.drop_table("alertas_dispensados")
