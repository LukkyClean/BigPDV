"""merge: unifica head do módulo fiscal com head da chain anterior (master)

Revision ID: e5f6a7b8c9d0
Revises: c2d3e4f5a6b7, d4e5f6a7b8c9
Create Date: 2026-08-15 00:00:00.000000

CONTEXTO:
O merge do PR #55 (feat/fiscal-module → master) trouxe dois conjuntos de
migrations independentes para o mesmo diretório alembic/versions:

  - Chain "master" (base: 51db61228566 / 5cf42db01be6):
    ... → 97dd6ac91792 → d1e2f3a4b5c6 → ... → c2d3e4f5a6b7  (HEAD 1)

  - Chain "nova baseline" (base: b386f0ba5efd):
    b386f0ba5efd → d6adbf5b3d66 → a1b2c3d4e5f6 → ... → d4e5f6a7b8c9  (HEAD 2)

Sem um merge migration, `alembic upgrade head` falha com:
  "Multiple head revisions are present for given argument 'head'"

Para DBs na chain "nova baseline" (que iniciou em b386f0ba5efd), a chain
"master" nunca foi executada. O `_corrigir_branches_inacessiveis` em
migrations.py registra o branch inacessível via stamp, mas o stamp não
executa o SQL das migrations. Esta migration aplica as colunas que faltam
de forma idempotente (guarda "coluna já existe" em cada ADD COLUMN).

Colunas que dependem da chain "master" e ainda não existem na chain nova:
  - empresas.cor_tema   (migration b1c2d3e4f5a6)
  - empresas.chave_pix  (migration c2d3e4f5a6b7)
  - empresas.pix_ativo  (migration c2d3e4f5a6b7)

NOTA PARA FUTURAS MIGRATIONS:
Toda migration nova deve ter `down_revision = 'e5f6a7b8c9d0'`.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = ('c2d3e4f5a6b7', 'd4e5f6a7b8c9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABELA = 'empresas'
_COLUNAS = {
    'cor_tema': sa.Column('cor_tema', sa.String(length=7), nullable=True),
    'chave_pix': sa.Column('chave_pix', sa.String(length=77), nullable=True),
    'pix_ativo': sa.Column(
        'pix_ativo', sa.Boolean(), nullable=False, server_default=sa.false()
    ),
}


def _colunas_existentes() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if _TABELA not in insp.get_table_names():
        return set(_COLUNAS)  # tabela inexistente — nada a fazer
    return {c['name'] for c in insp.get_columns(_TABELA)}


def upgrade() -> None:
    existentes = _colunas_existentes()
    for nome, coluna in _COLUNAS.items():
        if nome not in existentes:
            op.add_column(_TABELA, coluna)


def downgrade() -> None:
    existentes = _colunas_existentes()
    for nome in _COLUNAS:
        if nome in existentes:
            op.drop_column(_TABELA, nome)
