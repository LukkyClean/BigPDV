"""contratacao explicita do modulo fiscal

Revision ID: c2a8e5d1f473
Revises: b1f4a7c92e35
Create Date: 2026-09-05 10:05:00.000000

CONTEXTO:
O gate `requer_modulo_fiscal` decidia o DIREITO ao modulo fiscal pela simples
existencia de uma linha em empresa_fiscal_settings. Só que o GET /empresas/ —
que exige apenas autenticacao, sem permissao nenhuma — fazia get_or_create +
commit dessa linha. Como esse endpoint e consumido por PixQrCode,
FormatosExibicao e IntegracoesAPIs, abrir configuracoes ou vender no PIX
destrancava o modulo fiscal inteiro. Nao era um ataque: era o fluxo normal.

Esta coluna separa as duas perguntas que estavam confundidas numa so:
  - modulo_fiscal_ativo → a empresa TEM DIREITO (e onde o billing vai entrar)
  - existencia da linha  → a empresa JA CONFIGUROU

BACKFILL:
Marca True para quem ja emitiu documento fiscal. Quem esta usando o modulo em
producao nao pode ser cortado por um deploy — e a existencia de um
DocumentoFiscal e a evidencia mais forte de uso real que temos localmente.
Todo o resto nasce False: enquanto nao houver billing, ativar e ato deliberado
(UPDATE manual ou, no futuro, o claim do JWT da licenca).

SEGURANCA:
- Decide pela AUSENCIA da coluna: o create_all() do startup roda ANTES das
  migracoes e pode te-la criado numa instalacao nova. Ver CLAUDE.md.
- O backfill so toca linha ainda nao ativada, entao rodar de novo e inocuo.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c2a8e5d1f473'
down_revision: Union[str, Sequence[str], None] = 'b1f4a7c92e35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABELA = "empresa_fiscal_settings"
COLUNA = "modulo_fiscal_ativo"
TABELA_DOCUMENTOS = "documento_fiscal"


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not insp.has_table(TABELA):
        return

    colunas = {c["name"] for c in insp.get_columns(TABELA)}
    if COLUNA not in colunas:
        op.add_column(
            TABELA,
            sa.Column(COLUNA, sa.Boolean(), nullable=False, server_default="0"),
        )

    # Normaliza qualquer NULL remanescente antes do backfill.
    conn.execute(sa.text(f"UPDATE {TABELA} SET {COLUNA} = 0 WHERE {COLUNA} IS NULL"))

    # Backfill: quem ja emitiu documento fiscal continua emitindo.
    #
    # `documento_fiscal` NAO tem empresa_id — a origem dele e a venda/OS, e a
    # instalacao e singleton (uma empresa por banco, ver services/empresa.py).
    # Entao a pergunta correta e "este banco ja emitiu alguma nota?", e a
    # resposta ativa a unica linha de configuracao existente. Nao ha como
    # (nem por que) distinguir empresas aqui.
    if insp.has_table(TABELA_DOCUMENTOS):
        ja_emitiu = conn.execute(
            sa.text(f"SELECT 1 FROM {TABELA_DOCUMENTOS} LIMIT 1")
        ).first()
        if ja_emitiu:
            conn.execute(
                sa.text(f"UPDATE {TABELA} SET {COLUNA} = 1 WHERE {COLUNA} = 0")
            )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not insp.has_table(TABELA):
        return
    if COLUNA in {c["name"] for c in insp.get_columns(TABELA)}:
        op.drop_column(TABELA, COLUNA)
