"""sangria passa a ser regra de seguranca (requer_pin_sangria)

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-08-15

A trava da sangria nasceu em `configuracoes_vendas` e estava no lugar errado:
ela e uma protecao por PIN, e as sete irmas dela (cancelar venda, reabrir,
desconto, alterar preco, e as tres de OS) moram em `configuracoes_seguranca`.
O lojista procura todas no mesmo lugar -- e ja era o mesmo `pin_gerente`.

O padrao muda de True para False junto com a mudanca de casa, para ficar igual
as outras sete. Ligado sem PIN cadastrado, a sangria ficaria impossivel para
quem nao e master; desligado, o problema nao acontece em vez de ser explicado
por uma mensagem de erro.

SEGURO PORQUE AINDA NAO SAIU DAQUI: a coluna antiga foi criada pela migration
b2c3d4e5f6a7, desta mesma branch, e nenhum instalador com ela chegou a loja
nenhuma. Por isso a coluna e REMOVIDA em vez de deixada para tras -- coluna
morta e exatamente o que este projeto ja pagou caro com `valor_atacado`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("configuracoes_seguranca") and not _tem_coluna(
        insp, "configuracoes_seguranca", "requer_pin_sangria"
    ):
        op.add_column(
            "configuracoes_seguranca",
            sa.Column("requer_pin_sangria", sa.Boolean(), nullable=False, server_default="0"),
        )

    insp = sa.inspect(bind)
    if insp.has_table("configuracoes_vendas") and _tem_coluna(
        insp, "configuracoes_vendas", "sangria_exige_autorizacao"
    ):
        # DROP COLUMN existe no SQLite desde a 3.35. Se a versao for anterior, a
        # coluna fica para tras sem ninguem ler -- preferivel a migration falhar
        # e impedir o backend de subir, que e loja parada.
        try:
            op.drop_column("configuracoes_vendas", "sangria_exige_autorizacao")
        except Exception:
            pass


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("configuracoes_vendas") and not _tem_coluna(
        insp, "configuracoes_vendas", "sangria_exige_autorizacao"
    ):
        op.add_column(
            "configuracoes_vendas",
            sa.Column("sangria_exige_autorizacao", sa.Boolean(), nullable=False, server_default="1"),
        )

    insp = sa.inspect(bind)
    if insp.has_table("configuracoes_seguranca") and _tem_coluna(
        insp, "configuracoes_seguranca", "requer_pin_sangria"
    ):
        try:
            op.drop_column("configuracoes_seguranca", "requer_pin_sangria")
        except Exception:
            pass
