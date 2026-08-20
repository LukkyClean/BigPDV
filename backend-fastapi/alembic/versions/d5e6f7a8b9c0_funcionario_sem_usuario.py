"""funcionario pode existir sem usuario de acesso

Revision ID: d5e6f7a8b9c0
Revises: a1b2c3d4e5f6
Create Date: 2026-08-20

Ficha de RH e credencial de acesso sao coisas diferentes, com ciclos de vida
diferentes. O sistema ja modelava as duas em tabelas separadas -- o que existia
era uma amarra artificial (`funcionarios.usuario_id NOT NULL`) obrigando as
duas a nascerem juntas. Loja que so precisa registrar o entregador era forcada a
inventar um e-mail e uma senha para alguem que nunca vai entrar no sistema, e
essa credencial passava a existir de verdade.

Esta migration corta a amarra. O resto do codigo ja estava preparado: toda
leitura nas duas direcoes ja pergunta "existe?" antes de usar -- provavelmente
porque o Usuario Master ja podia existir sem funcionario.

`unique=True` CONTINUA na coluna, e isso e proposital: em SQL padrao (e no
SQLite) varios NULL convivem numa coluna unica, entao muitos funcionarios podem
ficar sem acesso, mas um usuario segue valendo para um funcionario so.

DECIDE PELA PRESENCA DO SCHEMA ANTIGO, nao pela ausencia do novo: no startup o
`create_all()` roda ANTES das migrations, entao num banco novo a tabela ja nasce
com a coluna nullable e nao ha o que alterar. Recriar a tabela a toa e risco
gratuito -- em SQLite, tornar coluna nullable significa COPIAR a tabela inteira,
e `funcionarios` e referenciada por vendas, OS e movimentacoes de estoque.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _coluna_usuario_id(bind) -> dict | None:
    insp = sa.inspect(bind)
    if "funcionarios" not in insp.get_table_names():
        return None
    for coluna in insp.get_columns("funcionarios"):
        if coluna["name"] == "usuario_id":
            return coluna
    return None


def upgrade() -> None:
    bind = op.get_bind()
    coluna = _coluna_usuario_id(bind)

    # Tabela ainda nao existe, ou a coluna ja aceita nulo (banco novo): nada a
    # fazer. Sair aqui e o que evita recriar `funcionarios` sem necessidade.
    if coluna is None or coluna["nullable"]:
        return

    with op.batch_alter_table("funcionarios", schema=None) as batch_op:
        batch_op.alter_column(
            "usuario_id",
            existing_type=sa.INTEGER(),
            nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    coluna = _coluna_usuario_id(bind)
    if coluna is None or not coluna["nullable"]:
        return

    # ATENCAO: isto FALHA de proposito se ja existir funcionario sem usuario.
    # Voltar atras com dados assim exigiria inventar credencial para essas
    # pessoas ou apagar as fichas delas -- as duas coisas piores que o erro.
    with op.batch_alter_table("funcionarios", schema=None) as batch_op:
        batch_op.alter_column(
            "usuario_id",
            existing_type=sa.INTEGER(),
            nullable=False,
        )
