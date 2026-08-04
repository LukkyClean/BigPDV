"""chave pix da empresa

Acrescenta `empresas.chave_pix` e `empresas.pix_ativo`.

A chave fica ao lado de `url_logo` e `cor_tema` pelo mesmo motivo: e dado da
empresa, nao regra de negocio. O QR e montado offline a partir dela -- nao ha
integracao bancaria envolvida, e por isso nao ha credencial a proteger aqui.

`pix_ativo` e separado da chave para permitir desligar sem apagar o que foi
cadastrado. Default False: instalacao existente nao passa a exibir QR sozinha.

Guarda contra coluna ja existente: no startup o `create_all()` roda ANTES das
migracoes, entao num banco novo a tabela ja nasce com as colunas.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELA = 'empresas'
COLUNAS = {
    'chave_pix': sa.Column('chave_pix', sa.String(length=77), nullable=True),
    'pix_ativo': sa.Column('pix_ativo', sa.Boolean(), nullable=False, server_default=sa.false()),
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
