"""elo da recorrencia em contas a pagar

Revision ID: d0e1f2a3b4c5
Revises: c9d2e3f4a5b6
Create Date: 2026-08-28 14:55:00.000000

Acrescenta `contas_pagar.gerada_por_id`: qual conta, ao ser paga, gerou esta
pela recorrencia.

POR QUE. Sem o elo a recorrencia nao tinha volta e nem trava. Estornar o
pagamento devolvia a conta para pendente mas deixava a ocorrencia do mes
seguinte na lista -- a loja aparentava dever duas contas de internet. E pagar de
novo criava MAIS uma, porque nada dizia que a proxima ja existia: a divida se
multiplicava a cada estorno-e-repagamento.

Aditiva e nullable. As linhas ja existentes ficam com NULL, que significa
"lancada a mao" -- e e a verdade para todas elas, exceto as que a recorrencia
gerou antes desta migration. Essas ficam orfas do elo: nao da para descobrir
retroativamente qual pagamento as criou, e inventar o vinculo seria pior que
admitir a lacuna. Na pratica so afeta quem estornar uma conta paga ANTES desta
versao, e o efeito e o comportamento antigo (a ocorrencia fica).

Sem FK declarada, pela mesma razao de `parcelamento_id`: aponta para a propria
tabela e serve como marca, nao como integridade referencial.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, Sequence[str], None] = 'c9d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tem_tabela(insp, nome: str) -> bool:
    return nome in insp.get_table_names()


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not _tem_tabela(insp, "contas_pagar"):
        return
    # Defensiva contra o create_all(), que no boot roda ANTES das migrations.
    if _tem_coluna(insp, "contas_pagar", "gerada_por_id"):
        return

    with op.batch_alter_table("contas_pagar") as batch:
        batch.add_column(sa.Column("gerada_por_id", sa.Integer(), nullable=True))

    op.create_index("ix_contas_pagar_gerada_por_id", "contas_pagar", ["gerada_por_id"])


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if _tem_tabela(insp, "contas_pagar") and _tem_coluna(insp, "contas_pagar", "gerada_por_id"):
        with op.batch_alter_table("contas_pagar") as batch:
            batch.drop_column("gerada_por_id")
