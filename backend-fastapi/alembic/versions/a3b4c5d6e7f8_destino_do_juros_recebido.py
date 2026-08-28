"""destino do juros recebido

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-08-28 18:20:00.000000

Acrescenta `contas_receber.juros_destino`: para ONDE vai o juros cobrado ao
quitar a conta.

  LOJA       multa por atraso. Receita da loja, entra no caixa com o principal.
  OPERADORA  juros do parcelamento na maquininha. O cliente desembolsa, mas
             esse pedaco nunca chega na loja.

POR QUE. Sem a distincao, o livro registrava como ENTRADA o total desembolsado
pelo cliente. Quando o juros era da maquininha, isso mostrava saldo que a conta
bancaria nao tem -- e numa loja com controle de caixa o turno fecharia com
sobra em todo recebimento parcelado.

Eixo DIFERENTE do `juros_responsavel` dos pagamentos de venda e OS: la a
pergunta e quem PAGA o juros, e o destino nunca muda (cartao sempre fica com a
operadora). Aqui a pergunta e quem RECEBE, e as duas respostas sao possiveis.

Aditiva, com default LOJA: e o caso da esmagadora maioria (multa por atraso), e
toda linha existente continua valendo sem mudar de significado.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, Sequence[str], None] = 'f2a3b4c5d6e7'
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
    if _tem_coluna(insp, "contas_receber", "juros_destino"):
        return

    with op.batch_alter_table("contas_receber") as batch:
        batch.add_column(
            sa.Column(
                "juros_destino", sa.String(length=10), nullable=False, server_default="LOJA"
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if _tem_tabela(insp, "contas_receber") and _tem_coluna(
        insp, "contas_receber", "juros_destino"
    ):
        with op.batch_alter_table("contas_receber") as batch:
            batch.drop_column("juros_destino")
