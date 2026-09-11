"""documento_fiscal: o destinatario que foi ENVIADO, congelado no documento

Revision ID: 9c4d7e2f1a05
Revises: 89eb6b730bb3
Create Date: 2026-09-11 11:00:00.000000

CONTEXTO:
O snapshot congelava os itens e nao o destinatario. A tela de detalhes lia o
cliente da VENDA -- e a nota de teste nao tem venda, entao aparecia
"Consumidor Final (Nao identificado)" numa nota que saiu com um CNPJ. Quando a
SEFAZ recusou citando um CNPJ que o ERP nao mandou, nao havia como provar o
que tinha sido enviado sem abrir o painel da emissora.

Duas colunas, gravadas junto com o snapshot, ANTES de transmitir: o documento
e o nome do destinatario exatamente como foram no payload. A tela passa a
mostrar isso quando existe, e cai no cliente da venda so para documentos
anteriores a esta migracao.

SEGURANCA: decide pela AUSENCIA da coluna (o create_all() do startup roda antes
e ja pode ter criado). Nada e convertido -- documentos antigos ficam NULL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9c4d7e2f1a05'
down_revision: Union[str, Sequence[str], None] = '89eb6b730bb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABELA = "documento_fiscal"
COLUNAS = {
    "destinatario_documento_enviado": sa.String(14),
    "destinatario_nome_enviado": sa.String(120),
}


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table(TABELA):
        return
    existentes = {c["name"] for c in insp.get_columns(TABELA)}
    for nome, tipo in COLUNAS.items():
        if nome not in existentes:
            op.add_column(TABELA, sa.Column(nome, tipo, nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_table(TABELA):
        return
    existentes = {c["name"] for c in insp.get_columns(TABELA)}
    with op.batch_alter_table(TABELA) as batch:
        for nome in COLUNAS:
            if nome in existentes:
                batch.drop_column(nome)
