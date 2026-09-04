"""forma de pagamento do adiantamento da OS

Acrescenta `ordens_servico.forma_pagamento_entrada_id`.

O adiantamento ja existia como `valor_entrada` (centavos), mas so o NUMERO era
guardado: nao havia como saber depois se o cliente adiantou em PIX, dinheiro ou
cartao. A informacao nao aparecia no resumo da finalizacao porque nunca chegou a
ser capturada.

Coluna nova em vez de linha em `ordem_servico_pagamentos`: a trava de
finalizacao e `sum(pagamentos) + valor_entrada == valor_total`
(services/ordem_servico.py), entao criar a linha faria o adiantamento ser
contado duas vezes e quebraria o fechamento nas lojas que ja rodam.

Nullable e sem default: OS anterior a este campo fica com NULL, e a tela mostra
so o valor, como hoje. Nada e inferido retroativamente -- chutar "Dinheiro" para
o historico seria inventar dado financeiro.

Guarda contra coluna ja existente: no startup o `create_all()` roda ANTES das
migracoes, entao num banco novo a tabela ja nasce com a coluna.

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, Sequence[str], None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELA = 'ordens_servico'
COLUNA = 'forma_pagamento_entrada_id'


def _existentes() -> set[str]:
    inspetor = sa.inspect(op.get_bind())
    if TABELA not in inspetor.get_table_names():
        return {COLUNA}  # sem a tabela nao ha o que migrar
    return {c['name'] for c in inspetor.get_columns(TABELA)}


def upgrade() -> None:
    if COLUNA in _existentes():
        return

    # Sem ForeignKey declarada aqui: no SQLite o ALTER TABLE nao cria constraint,
    # e exigir batch_alter_table so para isso reescreveria a tabela inteira da OS
    # -- risco desnecessario num banco de loja. O relacionamento e resolvido pelo
    # ORM (models/ordem_servico.py), que e quem le e escreve esta coluna.
    op.add_column(TABELA, sa.Column(COLUNA, sa.Integer(), nullable=True))


def downgrade() -> None:
    if COLUNA in _existentes():
        op.drop_column(TABELA, COLUNA)
