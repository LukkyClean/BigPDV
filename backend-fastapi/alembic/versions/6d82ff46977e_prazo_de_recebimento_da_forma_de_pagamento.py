"""prazo de recebimento da forma de pagamento

Revision ID: 6d82ff46977e
Revises: f4a5b6c7d8e9
Create Date: 2026-09-02 16:00:00.000000

DINHEIRO DE CARTAO NAO ESTA NA CONTA NO DIA DA VENDA. A maquininha deposita
depois -- D+1 na loja que abriu este pedido, 30 dias em muita outra. Ate aqui o
sistema tratava todo recebimento como dinheiro que ja entrou, e o saldo do Fluxo
de Caixa mostrava na conta um valor que so chegaria amanha.

Tres colunas, e cada uma existe por um motivo diferente:

1. `formas_pagamento.dias_para_receber`
   O prazo DECLARADO pelo dono, por forma. Zero (o padrao) e exatamente o
   comportamento de hoje: o dinheiro entra na hora. Nenhuma loja em producao
   muda de comportamento enquanto ninguem declarar nada -- e essa e a condicao
   para isto poder entrar numa branch que ja roda em tres lojas.

2. `formas_pagamento.conta_bancaria_id`
   Em qual conta aquele dinheiro cai. Cartao cai no banco, dinheiro fica na
   gaveta -- e ate agora TODO recebimento caia na conta principal, porque nao
   havia onde declarar o contrario.

3. `contas_receber.baixa_automatica`
   A MARCA que separa o cartao do fiado, e ela e a razao de a coluna existir em
   vez de a tarefa deduzir pela forma de pagamento. As duas coisas viram conta a
   receber pelo mesmo caminho, mas o cartao com prazo declarado PODE entrar
   sozinho no dia (o dono ja disse que cai) e o fiado NAO PODE NUNCA -- cliente
   nao paga por agendamento. Deduzir na hora da baixa deixaria essa distincao
   dependendo de a forma de pagamento nao ter sido editada no meio do caminho;
   gravada na cobranca, ela vale para sempre o que valia no dia da venda.

`formas_pagamento` e catalogo GLOBAL (nao tem empresa_id) e `contas_bancarias` e
por empresa. A FK entre as duas so faz sentido porque uma instalacao atende UMA
loja -- a licenca e por maquina. Fica registrado aqui porque o dia em que isso
mudar, esta coluna e uma das que quebram.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d82ff46977e'
down_revision: Union[str, Sequence[str], None] = 'f4a5b6c7d8e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tem_tabela(insp, nome: str) -> bool:
    return nome in insp.get_table_names()


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # Defensiva contra o create_all(), que no boot roda ANTES das migrations:
    # num banco novo a tabela ja nasce com as colunas, e o add_column quebraria.
    if _tem_tabela(insp, "formas_pagamento"):
        with op.batch_alter_table("formas_pagamento") as batch:
            if not _tem_coluna(insp, "formas_pagamento", "dias_para_receber"):
                batch.add_column(
                    sa.Column(
                        "dias_para_receber", sa.Integer(),
                        nullable=False, server_default="0",
                    )
                )
            if not _tem_coluna(insp, "formas_pagamento", "conta_bancaria_id"):
                batch.add_column(
                    sa.Column("conta_bancaria_id", sa.Integer(), nullable=True)
                )

    if _tem_tabela(insp, "contas_receber") and not _tem_coluna(
        insp, "contas_receber", "baixa_automatica"
    ):
        with op.batch_alter_table("contas_receber") as batch:
            batch.add_column(
                sa.Column(
                    "baixa_automatica", sa.Boolean(),
                    nullable=False, server_default="0",
                )
            )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if _tem_tabela(insp, "contas_receber") and _tem_coluna(
        insp, "contas_receber", "baixa_automatica"
    ):
        with op.batch_alter_table("contas_receber") as batch:
            batch.drop_column("baixa_automatica")

    if _tem_tabela(insp, "formas_pagamento"):
        with op.batch_alter_table("formas_pagamento") as batch:
            if _tem_coluna(insp, "formas_pagamento", "conta_bancaria_id"):
                batch.drop_column("conta_bancaria_id")
            if _tem_coluna(insp, "formas_pagamento", "dias_para_receber"):
                batch.drop_column("dias_para_receber")
