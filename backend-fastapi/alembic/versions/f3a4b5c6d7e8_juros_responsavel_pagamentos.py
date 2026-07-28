"""adiciona juros_valor e juros_responsavel nos pagamentos de OS e de venda

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-07-27 16:00:00.000000

CONTEXTO:
Ate aqui o juros de cartao era SEMPRE repassado ao cliente: entrava embutido no
`valor` do pagamento e somava no `acrescimo` da OS/venda. Agora a loja escolhe,
por pagamento, se repassa (CLIENTE) ou absorve (LOJA).

SEGURANCA (banco de cliente em producao):
- SOMENTE `ADD COLUMN` com default — no SQLite e instantaneo, NAO recria a tabela.
- `juros_responsavel` nasce 'CLIENTE' nas linhas existentes, que e exatamente o
  comportamento historico: todo juros ja cobrado foi repassado ao cliente.
- `juros_valor` nasce 0. Nenhum total, nenhum `acrescimo` e recalculado — os
  registros antigos continuam batendo com o que foi impresso e recebido.
- Guarda de existencia por coluna -> idempotente. Necessario porque o
  `create_all` roda ANTES das migrations no startup: em instalacao nova a
  tabela ja nasce com as colunas e o `add_column` falharia.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3a4b5c6d7e8'
down_revision: Union[str, Sequence[str], None] = 'e2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABELAS = ("ordem_servico_pagamentos", "pagamentos_venda")


def _tem_tabela(insp, tabela: str) -> bool:
    return insp.has_table(tabela)


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    for tabela in _TABELAS:
        if not _tem_tabela(insp, tabela):
            continue
        if not _tem_coluna(insp, tabela, "juros_valor"):
            op.add_column(
                tabela,
                sa.Column("juros_valor", sa.Integer(), nullable=False, server_default="0"),
            )
        if not _tem_coluna(insp, tabela, "juros_responsavel"):
            op.add_column(
                tabela,
                sa.Column(
                    "juros_responsavel",
                    sa.String(length=10),
                    nullable=False,
                    server_default="CLIENTE",
                ),
            )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    for tabela in _TABELAS:
        if not _tem_tabela(insp, tabela):
            continue
        for coluna in ("juros_responsavel", "juros_valor"):
            if _tem_coluna(insp, tabela, coluna):
                op.drop_column(tabela, coluna)
