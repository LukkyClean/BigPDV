"""adiciona produtos.localizacao_estoque

Revision ID: p9q0r1s2t3u4
Revises: 9c4d7e2f1a05
Create Date: 2026-09-12 10:20:00.000000

CONTEXTO:
"Localização no Estoque" era um campo FANTASMA. Existia na tela
(DadosProdutoSection.vue), no Zod, nos payloads de criação e de atualização, e
até no dicionário de campos legíveis do histórico de edições
(services/produto.py) — mas a coluna estava comentada no model e no schema.
O lojista digitava "Corredor A, Prateleira 3", salvava com sucesso e o dado
era descartado em silêncio, sem erro nenhum.

A escolha foi ENTREGAR o campo em vez de removê-lo: ele já está na tela e o
usuário conta com ele; tirar seria remover função que ele enxerga. É também o
que os sistemas de referência têm (no Tiny, "localização" está até na edição
em massa de produtos).

SEGURANÇA:
- Decide pela ausência da COLUNA, não pela revisão: se o create_all() do
  startup já a criou, esta migração não faz nada. Mesmo padrão da
  965c71a2da9a e da o8p9q0r1s2t3.
- Nullable: cadastros antigos ficam vazios, sem backfill.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'p9q0r1s2t3u4'
down_revision: Union[str, Sequence[str], None] = '9c4d7e2f1a05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABELA = "produtos"
COLUNA = "localizacao_estoque"


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not insp.has_table(TABELA):
        return

    colunas = {c["name"] for c in insp.get_columns(TABELA)}
    if COLUNA not in colunas:
        op.add_column(TABELA, sa.Column(COLUNA, sa.String(length=255), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not insp.has_table(TABELA):
        return

    colunas = {c["name"] for c in insp.get_columns(TABELA)}
    if COLUNA in colunas:
        op.drop_column(TABELA, COLUNA)
