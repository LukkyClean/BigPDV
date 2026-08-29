"""saldo informado da conta bancaria

Revision ID: c5d6e7f8a9b0
Revises: a3b4c5d6e7f8
Create Date: 2026-08-29 09:10:00.000000

Acrescenta `contas_bancarias.saldo_informado` e `saldo_informado_em`: quanto a
loja tem HOJE, declarado pelo dono.

POR QUE DECLARADO E NAO CALCULADO. O sistema nao sabe o saldo. O livro
(`movimentacoes_financeiras`) so recebe venda e OS quando a empresa liga
`controlar_caixa` E existe turno aberto -- numa loja que nao usa caixa,
derivar o saldo do livro daria so as despesas, um numero fundo negativo. E
`contas_bancarias` nunca teve coluna de saldo: guardava so o nome do lugar.

Sem esse numero o Fluxo de Caixa consegue dizer "vai sair mais do que entra no
periodo", mas nao "no dia 12 o dinheiro acaba" -- que e a pergunta pela qual o
modulo existe.

A DATA nao e enfeite: o saldo e um retrato, nao um saldo que anda sozinho. Com
`saldo_informado_em` a tela avisa "informado ha 12 dias, confira" em vez de
projetar em cima de numero velho fingindo que e de hoje. NULL = nunca informou,
e ai a tela pede antes de desenhar qualquer linha.

Aditiva e com default 0: toda linha existente continua valendo, e nenhuma loja
em producao muda de comportamento -- ninguem le essas colunas fora do Fluxo de
Caixa, que e FINANCEIRO_PRO.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5d6e7f8a9b0'
down_revision: Union[str, Sequence[str], None] = 'a3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tem_tabela(insp, nome: str) -> bool:
    return nome in insp.get_table_names()


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not _tem_tabela(insp, "contas_bancarias"):
        return

    # Defensiva contra o create_all(), que no boot roda ANTES das migrations:
    # num banco novo a tabela ja nasce com as colunas, e o add_column quebraria.
    if not _tem_coluna(insp, "contas_bancarias", "saldo_informado"):
        with op.batch_alter_table("contas_bancarias") as batch:
            batch.add_column(
                sa.Column("saldo_informado", sa.Integer(), nullable=False, server_default="0")
            )

    if not _tem_coluna(insp, "contas_bancarias", "saldo_informado_em"):
        with op.batch_alter_table("contas_bancarias") as batch:
            batch.add_column(sa.Column("saldo_informado_em", sa.Date(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not _tem_tabela(insp, "contas_bancarias"):
        return

    with op.batch_alter_table("contas_bancarias") as batch:
        if _tem_coluna(insp, "contas_bancarias", "saldo_informado_em"):
            batch.drop_column("saldo_informado_em")
        if _tem_coluna(insp, "contas_bancarias", "saldo_informado"):
            batch.drop_column("saldo_informado")
