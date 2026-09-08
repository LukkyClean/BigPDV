"""backfill do CRT da empresa (inclui MEI)

Revision ID: b1f4a7c92e35
Revises: 3ddff83ca0d4
Create Date: 2026-09-05 09:40:00.000000

CONTEXTO:
A coluna `empresas.crt` existe desde a o8p9q0r1s2t3, mas NENHUM servico jamais a
escreveu — so havia leituras (helpers.obter_crt). Na pratica toda empresa tinha
crt NULL e caia no CRT_PADRAO = 3 (Regime Normal), inclusive o MEI, que deveria
ser CRT 4. Como o CRT decide o grupo de ICMS da nota, um MEI vinha emitindo com
CST no lugar de CSOSN: rejeicao na SEFAZ ou, pior, nota aceita e errada.

A partir de agora o servico de empresa deriva e persiste o CRT no save
(helpers.crt_efetivo). Esta migracao acerta quem ja estava cadastrado.

BACKFILL:
Mesma regra do crt_efetivo, nesta ordem:
  1. O rotulo de `regime_tributario` manda, quando reconhecido.
  2. Sem rotulo util, `natureza_juridica = 'MEI'` resolve como CRT 4.
  3. Sem os dois, CRT 3 (Regime Normal) — o padrao seguro, porque destacar ICMS
     a mais se corrige por carta de correcao, enquanto usar CSOSN sem ser do
     Simples e rejeicao na origem.

Os rotulos novos "Lucro Presumido" e "Lucro Real" tambem entram como CRT 3: sao
os dois sabores do Regime Normal. A diferenca entre eles nao esta no CRT e sim
no regime de apuracao do PIS/COFINS (ver tax_engine/constants.py).

SEGURANCA:
- Decide pela AUSENCIA da coluna: o create_all() do startup roda ANTES das
  migracoes e pode te-la criado numa instalacao nova. Ver CLAUDE.md.
- So preenche linha com crt NULO — rodar de novo nao desfaz escolha nenhuma.
- Nao ha downgrade destrutivo: a coluna nao e removida aqui, porque quem a
  criou foi a o8p9q0r1s2t3. Reverter apenas volta as linhas para NULL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1f4a7c92e35'
down_revision: Union[str, Sequence[str], None] = '3ddff83ca0d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABELA = "empresas"
COLUNA = "crt"

# Espelha _ROTULO_PARA_CRT de app/services/fiscal/helpers.py.
ROTULO_PARA_CRT = {
    "simples nacional": 1,
    "simples nacional (excesso de sublimite)": 2,
    "regime normal": 3,
    "lucro presumido": 3,
    "lucro real": 3,
    "mei": 4,
    "microempreendedor individual": 4,
}

CRT_MEI = 4
CRT_PADRAO = 3


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not insp.has_table(TABELA):
        return

    colunas = {c["name"] for c in insp.get_columns(TABELA)}
    if COLUNA not in colunas:
        op.add_column(TABELA, sa.Column(COLUNA, sa.Integer(), nullable=True))
        colunas.add(COLUNA)

    # 1. Pelo rotulo de regime tributario.
    for rotulo, crt in ROTULO_PARA_CRT.items():
        conn.execute(
            sa.text(
                f"UPDATE {TABELA} SET {COLUNA} = :crt "
                f"WHERE {COLUNA} IS NULL "
                f"  AND LOWER(TRIM(COALESCE(regime_tributario, ''))) = :rotulo"
            ),
            {"crt": crt, "rotulo": rotulo},
        )

    # 2. Sem rotulo util, a natureza juridica ainda pode revelar o MEI.
    if "natureza_juridica" in colunas:
        conn.execute(
            sa.text(
                f"UPDATE {TABELA} SET {COLUNA} = :crt "
                f"WHERE {COLUNA} IS NULL "
                f"  AND UPPER(TRIM(COALESCE(natureza_juridica, ''))) = 'MEI'"
            ),
            {"crt": CRT_MEI},
        )

    # 3. O resto assume Regime Normal.
    conn.execute(
        sa.text(f"UPDATE {TABELA} SET {COLUNA} = :crt WHERE {COLUNA} IS NULL"),
        {"crt": CRT_PADRAO},
    )


def downgrade() -> None:
    """
    Devolve as linhas para NULL sem remover a coluna — quem a criou foi a
    o8p9q0r1s2t3, e derruba-la aqui quebraria aquela revisao.
    """
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not insp.has_table(TABELA):
        return
    if COLUNA in {c["name"] for c in insp.get_columns(TABELA)}:
        conn.execute(sa.text(f"UPDATE {TABELA} SET {COLUNA} = NULL"))
