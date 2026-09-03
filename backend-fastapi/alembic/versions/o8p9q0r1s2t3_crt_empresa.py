"""adiciona empresas.crt com backfill a partir de regime_tributario

Revision ID: o8p9q0r1s2t3
Revises: n7o8p9q0r1s2
Create Date: 2026-09-02 21:40:00.000000

CONTEXTO:
Toda a bifurcação CSOSN × CST dependia de `"simples" in regime_tributario.lower()`.
Isso retorna True para "Simples Nacional (Excesso de Sublimite)", que é CRT 2 e
usa CST — não CSOSN. Empresas nesse regime emitiam com o grupo de ICMS errado.

O CRT também é exigido pela SEFAZ como número (1..4); antes era enviado o texto.

BACKFILL:
Traduz os três rótulos que a interface oferece (empresa.constants.ts) para o CRT
correspondente. Cadastro sem correspondência fica NULL e cai no fallback de
`obter_crt()`, que assume Regime Normal — o padrão seguro: destacar ICMS a mais
se corrige por carta de correção, usar CSOSN sem ser do Simples é rejeição.

SEGURANÇA:
- Decide pela ausência da COLUNA: se o create_all() do startup já a criou, o
  backfill ainda roda (a coluna existiria vazia).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'o8p9q0r1s2t3'
down_revision: Union[str, Sequence[str], None] = 'n7o8p9q0r1s2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABELA = "empresas"
COLUNA = "crt"

# Rótulo (minúsculo) -> CRT. Espelha _ROTULO_PARA_CRT em services/fiscal/helpers.py.
BACKFILL = {
    "simples nacional": 1,
    "simples nacional (excesso de sublimite)": 2,
    "regime normal": 3,
    "mei": 4,
    "microempreendedor individual": 4,
}


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not insp.has_table(TABELA):
        return

    colunas = {c["name"] for c in insp.get_columns(TABELA)}
    if COLUNA not in colunas:
        op.add_column(TABELA, sa.Column(COLUNA, sa.Integer(), nullable=True))

    # Backfill: só preenche quem ainda está sem CRT.
    for rotulo, crt in BACKFILL.items():
        conn.execute(
            sa.text(
                f"UPDATE {TABELA} SET {COLUNA} = :crt "
                f"WHERE {COLUNA} IS NULL "
                f"AND LOWER(TRIM(regime_tributario)) = :rotulo"
            ),
            {"crt": crt, "rotulo": rotulo},
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not insp.has_table(TABELA):
        return

    colunas = {c["name"] for c in insp.get_columns(TABELA)}
    if COLUNA in colunas:
        op.drop_column(TABELA, COLUNA)
