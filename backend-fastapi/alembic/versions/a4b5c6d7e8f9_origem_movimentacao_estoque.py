"""adiciona origem, venda_id e ordem_servico_id em movimentacoes_estoque

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-07-27 18:00:00.000000

CONTEXTO:
`movimentacoes_estoque` passa a ser o livro-razao UNICO do estoque. Antes,
venda gravava em `logs_produto` e o resto gravava aqui — o historico de estoque
nunca mostrava venda. Agora tudo grava nesta tabela, e `origem` diz de onde veio.

SEGURANCA (banco de cliente em producao):
- SOMENTE `ADD COLUMN` — no SQLite e instantaneo, NAO recria a tabela.
- As linhas existentes recebem `origem = 'LEGADO'`, nao 'MANUAL'. A origem real
  delas nao e recuperavel (podiam ser cadastro ou ajuste), e marcar como MANUAL
  seria afirmar algo que nao sabemos. LEGADO diz a verdade: veio de antes.
- `venda_id` e `ordem_servico_id` nascem NULL em tudo que ja existe. Nenhum
  vinculo e inventado retroativamente.
- `logs_produto` NAO e tocada: os dados historicos dela continuam intactos. Ela
  so deixa de receber escritas novas.
- Guarda de existencia por coluna -> idempotente. Necessario porque o
  `create_all` roda ANTES das migrations no startup.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a4b5c6d7e8f9'
down_revision: Union[str, Sequence[str], None] = 'f3a4b5c6d7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABELA = "movimentacoes_estoque"


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(_TABELA):
        return

    if not _tem_coluna(insp, _TABELA, "origem"):
        op.add_column(
            _TABELA,
            sa.Column("origem", sa.String(length=20), nullable=False, server_default="LEGADO"),
        )
        op.create_index(f"ix_{_TABELA}_origem", _TABELA, ["origem"])

    # FKs nao sao adicionadas junto da coluna: no SQLite, adicionar constraint a
    # uma tabela existente exigiria recria-la. A integridade e garantida na
    # aplicacao, e o SQLite so aplica FK com PRAGMA foreign_keys ligado.
    if not _tem_coluna(insp, _TABELA, "venda_id"):
        op.add_column(_TABELA, sa.Column("venda_id", sa.Integer(), nullable=True))
        op.create_index(f"ix_{_TABELA}_venda_id", _TABELA, ["venda_id"])

    if not _tem_coluna(insp, _TABELA, "ordem_servico_id"):
        op.add_column(_TABELA, sa.Column("ordem_servico_id", sa.Integer(), nullable=True))
        op.create_index(f"ix_{_TABELA}_ordem_servico_id", _TABELA, ["ordem_servico_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(_TABELA):
        return

    for coluna in ("ordem_servico_id", "venda_id", "origem"):
        if _tem_coluna(insp, _TABELA, coluna):
            try:
                op.drop_index(f"ix_{_TABELA}_{coluna}", table_name=_TABELA)
            except Exception:
                pass
            op.drop_column(_TABELA, coluna)
