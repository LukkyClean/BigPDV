"""adiciona documento_fiscal.caminho_xml_local e caminho_pdf_local

Revision ID: r1s2t3u4v5w6
Revises: q0r1s2t3u4v5
Create Date: 2026-09-13 09:10:00.000000

CONTEXTO:
O ERP guardava só `url_pdf` e `url_xml` — endereços na emissora. Os documentos
fiscais da loja dependiam de a plataforma e a Focus estarem no ar, do link não
expirar e de continuarmos clientes da mesma emissora.

Quem é obrigado a guardar o XML por cinco anos é o EMITENTE. A partir daqui o
XML autorizado é gravado no disco da loja (`services/fiscal/arquivos.py`) e o
caminho fica nesta coluna.

Documentos anteriores ficam com NULL e continuam funcionando pela URL. O
preenchimento retroativo é assunto de uma tarefa à parte, não desta migração.

SEGURANÇA:
- Decide pela ausência da COLUNA: se o create_all() do startup já a criou,
  esta migração não faz nada.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'r1s2t3u4v5w6'
down_revision: Union[str, Sequence[str], None] = 'q0r1s2t3u4v5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABELA = "documento_fiscal"
# O XML é obrigação legal de cinco anos e entra no backup; o DANFE é derivado
# dele e fica só local (ver `backup/_constants.py`). Duas colunas porque os
# arquivos vivem em pastas diferentes por causa disso.
COLUNAS = ("caminho_xml_local", "caminho_pdf_local")


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not insp.has_table(TABELA):
        return

    colunas = {c["name"] for c in insp.get_columns(TABELA)}
    for coluna in COLUNAS:
        if coluna not in colunas:
            op.add_column(TABELA, sa.Column(coluna, sa.String(length=500), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not insp.has_table(TABELA):
        return

    colunas = {c["name"] for c in insp.get_columns(TABELA)}
    for coluna in COLUNAS:
        if coluna in colunas:
            op.drop_column(TABELA, coluna)
