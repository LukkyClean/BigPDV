"""parcelamento em contas a pagar

Revision ID: c9d2e3f4a5b6
Revises: b8c1d2e3f4a5
Create Date: 2026-08-28 14:20:00.000000

Acrescenta o agrupamento de parcelas em `contas_pagar`. Puramente aditiva: tres
colunas nullable, nenhuma linha existente e tocada.

  parcelamento_id  id da PRIMEIRA parcela do grupo (aponta para a propria tabela)
  parcela_numero   3, em "3 de 10"
  parcela_total    10, em "3 de 10"

POR QUE NAO HA TABELA-PAI. A unidade de controle nos ERPs e a PARCELA, nao o
contrato: o Odoo gera "um item contabil para cada data de vencimento", cada um
com cobranca e baixa proprias. `contas_pagar` ja estava nesse grao -- uma linha,
um vencimento, uma baixa. Faltava so saber quais linhas sao a mesma compra, e
para isso basta a marca.

`parcelamento_id` referencia a primeira parcela do proprio grupo, o que dispensa
sequence e tabela auxiliar. Sem FK declarada de proposito: uma FK para a mesma
tabela impediria apagar a primeira parcela sem mexer nas outras, e nao ha nada a
proteger -- a coluna e agrupamento, nao integridade referencial.

Nada e criado para CARTAO_CREDITO: o tipo da conta bancaria e String e o novo
valor do enum nao pede migration.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'b8c1d2e3f4a5'
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
        # Instalacao que ainda nao rodou a migration anterior; o create_all do
        # boot cria a tabela ja completa e nao ha o que acrescentar.
        return

    # Defensiva contra o create_all(), que no startup roda ANTES das migrations:
    # numa instalacao que sobe direto com o codigo novo a tabela ja nasce com as
    # colunas, e um ADD COLUMN cego quebraria o boot do cliente.
    novas = (
        ("parcelamento_id", sa.Integer()),
        ("parcela_numero", sa.Integer()),
        ("parcela_total", sa.Integer()),
    )
    faltando = [
        (nome, tipo) for nome, tipo in novas
        if not _tem_coluna(insp, "contas_pagar", nome)
    ]
    if not faltando:
        return

    with op.batch_alter_table("contas_pagar") as batch:
        for nome, tipo in faltando:
            batch.add_column(sa.Column(nome, tipo, nullable=True))

    if any(nome == "parcelamento_id" for nome, _ in faltando):
        op.create_index(
            "ix_contas_pagar_parcelamento_id", "contas_pagar", ["parcelamento_id"]
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not _tem_tabela(insp, "contas_pagar"):
        return

    with op.batch_alter_table("contas_pagar") as batch:
        for nome in ("parcela_total", "parcela_numero", "parcelamento_id"):
            if _tem_coluna(insp, "contas_pagar", nome):
                batch.drop_column(nome)
