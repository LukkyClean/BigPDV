"""juros no recebimento de contas a receber

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-08-28 17:30:00.000000

Acrescenta `contas_receber.juros`: juros e multa cobrados do cliente por atraso,
na hora de quitar.

POR QUE COLUNA PROPRIA e nao embutido em `valor_recebido`: juros de mora e
RECEITA FINANCEIRA, nao venda. Somado ao principal ele inflaria o faturamento
do mes com dinheiro que nao veio de mercadoria nem de servico, e "recebi R$ 110
de uma divida de R$ 100" ficaria indistinguivel de "o cliente pagou errado".

Aditiva e com default zero: toda linha existente continua valendo, e recebimento
sem juros -- a maioria -- nao muda em nada.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tem_tabela(insp, nome: str) -> bool:
    return nome in insp.get_table_names()


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not _tem_tabela(insp, "contas_receber"):
        return
    # Defensiva contra o create_all(), que no boot roda ANTES das migrations.
    if _tem_coluna(insp, "contas_receber", "juros"):
        return

    with op.batch_alter_table("contas_receber") as batch:
        batch.add_column(
            sa.Column("juros", sa.Integer(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if _tem_tabela(insp, "contas_receber") and _tem_coluna(insp, "contas_receber", "juros"):
        with op.batch_alter_table("contas_receber") as batch:
            batch.drop_column("juros")
