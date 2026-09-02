"""saldo que anda e custo de mercadoria

Revision ID: f4a5b6c7d8e9
Revises: d6e7f8a9b0c1
Create Date: 2026-09-02 10:00:00.000000

DUAS CORRECOES DO MESMO DEFEITO, e por isso na mesma migration: o dinheiro que a
loja tem e o lucro que ela faz eram os dois numeros que o Financeiro nao sabia
responder. Aplicar so uma metade deixaria a conta do dono pior do que estava --
o caso que abriu isto foi um servico de R$ 160 com uma peca de R$ 60 comprada na
hora, em que o esperado era 200 no caixa e a tela mostrava 100.

1. `contas_bancarias.saldo_informado_instante`
   O saldo declarado virou ANCORA em vez de foto: o saldo de hoje passa a ser a
   ancora mais o que o livro registrou depois dela. Faltava o INSTANTE do
   retrato -- so com o dia, um saldo declarado as 15h contaria de novo a venda
   das 10h, porque ela ja estava dentro do numero que o dono contou na gaveta.

   Aditiva e NULL nas linhas existentes. Quem esta NULL cai na convencao
   conservadora do Conta Azul (corte no fim do dia declarado): perde o movimento
   daquele dia, mas nunca conta nada duas vezes.

2. "Fornecedores / Mercadoria" passa de DESPESA para CUSTO
   Plano de contas gerencial tem TRES grupos (receita, custo, despesa), e a
   diferenca entre os dois ultimos e a conta do lucro. Compra de mercadoria nao
   e despesa: o dinheiro virou estoque. Ela sai do caixa, mas so sai do LUCRO no
   dia em que a peca e vendida, pelo CMV. E o mesmo desenho do QuickBooks e do
   Xero, onde comprar estoque debita ativo e so a venda debita CMV.

   Sem esta reclassificacao, ligar o CMV no Financeiro descontaria a mesma peca
   DUAS vezes -- uma como despesa paga, outra como custo da venda.

   So a categoria SEMEADA pelo sistema (`padrao = 1`) e so se ainda estiver como
   DESPESA. Categoria criada a mao pelo lojista nao e tocada: nao da para
   adivinhar o que ele quis dizer com o nome dela, e mudar o tipo por baixo
   mudaria o lucro dele sem aviso.

O QUE MUDA PARA QUEM JA USA. O lucro dos meses passados e recalculado na
leitura, entao um mes em que a loja lancou compra de mercadoria como conta a
pagar vai mostrar lucro MAIOR do que mostrava -- e o numero novo e o certo: o
antigo descontava a peca no dia da compra e de novo no dia da venda. O Fluxo de
Caixa nao muda por causa disto: la a compra continua saindo do caixa.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4a5b6c7d8e9'
down_revision: Union[str, Sequence[str], None] = 'd6e7f8a9b0c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATEGORIA_MERCADORIA = "Fornecedores / Mercadoria"


def _tem_tabela(insp, nome: str) -> bool:
    return nome in insp.get_table_names()


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # --- 1. O instante da ancora ---
    #
    # Defensiva contra o create_all(), que no boot roda ANTES das migrations:
    # num banco novo a tabela ja nasce com a coluna, e o add_column quebraria.
    if _tem_tabela(insp, "contas_bancarias") and not _tem_coluna(
        insp, "contas_bancarias", "saldo_informado_instante"
    ):
        with op.batch_alter_table("contas_bancarias") as batch:
            batch.add_column(
                sa.Column("saldo_informado_instante", sa.DateTime(), nullable=True)
            )

    # --- 2. Mercadoria vira CUSTO ---
    if _tem_tabela(insp, "planos_conta"):
        conn.execute(
            sa.text(
                "UPDATE planos_conta SET tipo = 'CUSTO' "
                "WHERE padrao = 1 AND tipo = 'DESPESA' AND nome = :nome"
            ),
            {"nome": CATEGORIA_MERCADORIA},
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if _tem_tabela(insp, "planos_conta"):
        conn.execute(
            sa.text(
                "UPDATE planos_conta SET tipo = 'DESPESA' "
                "WHERE padrao = 1 AND tipo = 'CUSTO' AND nome = :nome"
            ),
            {"nome": CATEGORIA_MERCADORIA},
        )

    if _tem_tabela(insp, "contas_bancarias") and _tem_coluna(
        insp, "contas_bancarias", "saldo_informado_instante"
    ):
        with op.batch_alter_table("contas_bancarias") as batch:
            batch.drop_column("saldo_informado_instante")
