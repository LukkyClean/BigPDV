"""carencia de pagamento na licenca

Acrescenta `configuracoes_licenca.em_carencia` e
`configuracoes_licenca.data_limite_carencia`.

NAO confundir com a coluna `grace_period`, que ja existia: aquela e validade
OFFLINE (quanto tempo a loja roda sem falar com o servidor de licenca). Estas
duas sao a janela em que o gateway ainda esta re-tentando um cartao que falhou
-- assunto de pagamento, nao de conectividade. Os dois prazos correm juntos e
independentes, e a carencia afrouxa so o vencimento do plano.

Ambas NULAS: instalacao que ainda nao sincronizou depois da atualizacao
continua se comportando exatamente como antes, e uma licenca no PIX nunca as
preenche.

Guarda contra coluna ja existente: no startup o `create_all()` roda ANTES das
migracoes, entao num banco novo a tabela ja nasce com as colunas.

Revision ID: d1a2b3c4e5f6
Revises: c7d8e9f0a1b2
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd1a2b3c4e5f6'
down_revision: Union[str, Sequence[str], None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELA = 'configuracoes_licenca'
COLUNAS = {
    'em_carencia': sa.Column('em_carencia', sa.Boolean(), nullable=True),
    'data_limite_carencia': sa.Column('data_limite_carencia', sa.DateTime(), nullable=True),
}


def _existentes() -> set[str]:
    inspetor = sa.inspect(op.get_bind())
    if TABELA not in inspetor.get_table_names():
        return set(COLUNAS)  # sem a tabela nao ha o que migrar
    return {c['name'] for c in inspetor.get_columns(TABELA)}


def upgrade() -> None:
    ja_tem = _existentes()
    for nome, coluna in COLUNAS.items():
        if nome not in ja_tem:
            op.add_column(TABELA, coluna)


def downgrade() -> None:
    ja_tem = _existentes()
    for nome in COLUNAS:
        if nome in ja_tem:
            op.drop_column(TABELA, nome)
