"""snapshot dos itens no documento fiscal

Revision ID: e5b7d1c3a920
Revises: b1f4a7c92e35
Create Date: 2026-09-05 15:20:00.000000

CONTEXTO:
O DocumentoFiscal nao guardava nada dos itens. A tela de detalhes reconstruia
NCM e CFOP AO VIVO, lendo item.produto.fiscal a cada abertura
(services/documento_fiscal.py). Consequencia: trocar o NCM de um produto muda
o que uma nota JA AUTORIZADA exibe — o lojista confere e ve um documento
diferente do XML que esta na SEFAZ.

Hoje isso e latente. Vira grave assim que a derivacao automatica de campos
entrar: uma rotina que recalcula CFOP em lote reescreveria a exibicao de todo
o historico fiscal. Por isso o snapshot e PRE-REQUISITO da derivacao.

O que fica congelado sai do PAYLOAD, nao do cadastro: e o payload que foi
transmitido, e e com ele que a nota autorizada tem que bater.

SEM BACKFILL, de proposito:
Nao ha de onde tirar o que foi enviado em notas antigas — o payload nao foi
guardado. Inventar a partir do cadastro atual seria justamente o erro que esta
tabela corrige, so que gravado em disco. Documentos anteriores continuam caindo
no caminho antigo (reconstrucao ao vivo), que o servico mantem como fallback.

SEGURANCA:
- Decide pela AUSENCIA da tabela: o create_all() do startup roda ANTES das
  migracoes e pode te-la criado numa instalacao nova. Ver CLAUDE.md.
- produto_id NAO tem FK: a nota tem que se explicar sozinha mesmo depois que o
  produto sair do catalogo.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5b7d1c3a920'
down_revision: Union[str, Sequence[str], None] = 'b1f4a7c92e35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABELA = "documento_fiscal_item"


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if insp.has_table(TABELA):
        return

    op.create_table(
        TABELA,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("documento_fiscal_id", sa.Integer(), nullable=False),
        sa.Column("numero_item", sa.Integer(), nullable=False),
        # Sem ForeignKey: ver docstring.
        sa.Column("produto_id", sa.Integer(), nullable=True),
        sa.Column("descricao", sa.String(length=255), nullable=False),
        sa.Column("codigo_produto", sa.String(length=60), nullable=True),
        sa.Column("codigo_barras", sa.String(length=20), nullable=True),
        sa.Column("unidade", sa.String(length=6), nullable=True),
        sa.Column("ncm", sa.String(length=8), nullable=True),
        sa.Column("cfop", sa.String(length=4), nullable=True),
        sa.Column("cest", sa.String(length=7), nullable=True),
        sa.Column("origem_mercadoria", sa.String(length=1), nullable=True),
        sa.Column("situacao_tributaria", sa.String(length=3), nullable=True),
        sa.Column("quantidade_milesimos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valor_unitario", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valor_bruto", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valor_desconto", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("base_icms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valor_icms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("aliquota_icms_centesimos", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["documento_fiscal_id"], ["documento_fiscal.id"], ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f(f"ix_{TABELA}_documento_fiscal_id"), TABELA, ["documento_fiscal_id"],
    )
    op.create_index(op.f(f"ix_{TABELA}_id"), TABELA, ["id"])


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if insp.has_table(TABELA):
        op.drop_table(TABELA)
