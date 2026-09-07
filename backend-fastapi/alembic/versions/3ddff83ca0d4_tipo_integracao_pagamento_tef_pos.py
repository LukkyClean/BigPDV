"""tipo de integracao da forma de pagamento (TEF x POS)

Revision ID: 3ddff83ca0d4
Revises: a7fa162a583f
Create Date: 2026-09-04 07:12:00.000000

CONTEXTO:
A NF-e/NFC-e descreve, no grupo `card`, se o pagamento em cartao passou por
maquininha INTEGRADA ao PDV (tpIntegra 1) ou AUTONOMA, digitada a mao
(tpIntegra 2). Ate aqui o sistema nao guardava essa informacao e todo cartao
saia sem o grupo.

BACKFILL:
- Formas de CARTAO (codigo SEFAZ 03 credito e 04 debito) recebem 'POS'. E o
  arranjo da maioria das lojas pequenas, e afirmar uma integracao TEF que nao
  existe descreveria mal a operacao num documento fiscal. Quem tem TEF troca
  no cadastro.
- As demais recebem 'NAO_SE_APLICA': dinheiro, PIX e boleto nao passam por
  maquininha, e deixa-las nulas faria a tela mostrar um seletor vazio sem
  motivo.

SEGURANCA:
- Decide pela AUSENCIA da coluna: o create_all() do startup roda ANTES das
  migracoes e pode te-la criado vazia numa instalacao nova — nesse caso o
  backfill ainda precisa rodar. Ver CLAUDE.md.
- O backfill so preenche linha com o campo NULO, entao rodar de novo nao
  desfaz uma escolha do lojista.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3ddff83ca0d4'
down_revision: Union[str, Sequence[str], None] = 'a7fa162a583f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABELA = "formas_pagamento"
COLUNA = "tipo_integracao"

# Codigos SEFAZ que representam cartao — os unicos em que o grupo `card` existe.
CODIGOS_CARTAO = ("03", "04")


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not insp.has_table(TABELA):
        return

    colunas = {c["name"] for c in insp.get_columns(TABELA)}
    if COLUNA not in colunas:
        op.add_column(TABELA, sa.Column(COLUNA, sa.String(15), nullable=True))

    # Backfill: so quem ainda esta sem classificacao.
    conn.execute(
        sa.text(
            f"UPDATE {TABELA} SET {COLUNA} = 'POS' "
            f"WHERE {COLUNA} IS NULL AND codigo_sefaz IN ('03', '04')"
        )
    )
    conn.execute(
        sa.text(
            f"UPDATE {TABELA} SET {COLUNA} = 'NAO_SE_APLICA' "
            f"WHERE {COLUNA} IS NULL"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not insp.has_table(TABELA):
        return
    if COLUNA in {c["name"] for c in insp.get_columns(TABELA)}:
        op.drop_column(TABELA, COLUNA)
