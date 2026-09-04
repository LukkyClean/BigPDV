"""fila do caixa: vendas.enviada_ao_caixa_em

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-08-21

Fase 2 do plano em docs/pdv-fila-do-caixa-plano.md.

Numa loja onde um atende e outro recebe, o atendente monta o carrinho e entrega
a venda ao caixa. Ate aqui as duas situacoes eram indistinguiveis na lista: uma
venda ATIVA podia ser "pronta, esperando o caixa" ou "pela metade, ainda sendo
montada". Esta coluna e a diferenca -- NULL = em montagem, preenchida = na fila.

POR QUE COLUNA E NAO UM STATUS NOVO. O modulo compara `VendaStatus` por
igualdade em varios lugares: a listagem em `db/crud/venda.py` e o
`get_sales_status`, que alimenta os cards ATIVAS / FINALIZADAS / CANCELADAS. Um
`AGUARDANDO_PAGAMENTO` obrigaria a revisar TODA comparacao de status do modulo,
e uma esquecida faz a venda sumir de uma contagem sem erro nenhum -- com tres
lojas em producao nessas telas. Assim o status continua ATIVA nos dois casos.

Timestamp e nao booleano: custa o mesmo e da a ordem da fila de graca, alem de
permitir medir tempo de espera depois, se um dia interessar.

Nullable e sem server_default: NULL ja significa "em montagem", que e o estado
de toda venda que existe hoje. Loja que atualiza e nao usa a funcionalidade nao
ve diferenca nenhuma -- nao ha backfill a fazer.

DECIDE PELA PRESENCA DA COLUNA, e nao pela ausencia: no startup o `create_all()`
roda ANTES das migrations, entao num banco novo a coluna ja nasce e nao ha o que
adicionar.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b6c7d8e9f0a1"
down_revision: Union[str, Sequence[str], None] = "a5b6c7d8e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("vendas") and not _tem_coluna(insp, "vendas", "enviada_ao_caixa_em"):
        op.add_column(
            "vendas",
            sa.Column("enviada_ao_caixa_em", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("vendas") and _tem_coluna(insp, "vendas", "enviada_ao_caixa_em"):
        # DROP COLUMN existe no SQLite desde a 3.35. Se a versao for anterior, a
        # coluna fica para tras sem ninguem ler -- preferivel a migration falhar
        # e impedir o backend de subir, que e loja parada.
        try:
            op.drop_column("vendas", "enviada_ao_caixa_em")
        except Exception:
            pass
