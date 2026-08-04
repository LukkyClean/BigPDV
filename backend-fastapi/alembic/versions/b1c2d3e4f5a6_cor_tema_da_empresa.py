"""cor do tema da empresa

Acrescenta `empresas.cor_tema`: a cor da marca escolhida pelo dono, semente da
paleta derivada no frontend. Fica ao lado de `url_logo` por ser da mesma
natureza -- identidade visual, nao regra de negocio.

NULL significa paleta de fabrica, entao a instalacao existente continua azul sem
precisar de backfill.

Guarda contra coluna ja existente: no startup o `create_all()` roda ANTES das
migracoes (app/core/tarefas.py), entao num banco novo a tabela ja nasce com a
coluna e o ADD COLUMN quebraria. Decidir pela presenca do schema, nunca pela
ausencia dele.

Revision ID: b1c2d3e4f5a6
Revises: d9e0f1a2b3c4
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'd9e0f1a2b3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELA = 'empresas'
COLUNA = 'cor_tema'


def _tem_coluna() -> bool:
    inspetor = sa.inspect(op.get_bind())
    if TABELA not in inspetor.get_table_names():
        return True  # sem a tabela nao ha o que migrar
    return COLUNA in {c['name'] for c in inspetor.get_columns(TABELA)}


def upgrade() -> None:
    if _tem_coluna():
        return
    op.add_column(TABELA, sa.Column(COLUNA, sa.String(length=7), nullable=True))


def downgrade() -> None:
    if not _tem_coluna():
        return
    op.drop_column(TABELA, COLUNA)
