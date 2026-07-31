"""custo e sigilo da peca na OS: custo_unitario e visivel_cliente no item

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-07-31 12:00:00.000000

CONTEXTO A — `custo_unitario` (o gasto que ninguem registrava):
Na OS o comum e nao cadastrar peca: lanca-se so o servico ("Troca de conector —
R$ 150"). Mas o conector custou R$ 40, e sem registrar isso o relatorio de lucro
do mes fica maior do que foi. Este campo e o lugar de declarar esse gasto.

E INTERNO por decisao explicita da loja: NAO sai em nenhuma via impressa. O
cliente nunca deve ver quanto foi pago pela peca. So vale para item sem
`produto_id` — com produto do catalogo o custo vem do livro de estoque, e contar
os dois dobraria o CMV.

CONTEXTO B — `visivel_cliente` (a peca do estoque que nao deve aparecer):
As vezes a loja cobra pelo SERVICO e nao quer expor a peca usada: cobra R$ 150
pela troca do conector e nao interessa que o cliente saiba que o conector custou
R$ 40. Mas a peca precisa sair do estoque e pesar no custo, senao o lucro do mes
fica errado.

`visivel_cliente = False` marca a peca como EMBUTIDA no servico:
  - continua dando baixa no estoque e congelando custo -> entra no CMV
  - NAO e listada nas vias impressas do cliente (A4, cupom e ESC/POS)
  - vale ZERO; o dinheiro fica na linha do servico

O valor zero e obrigatorio porque as vias imprimem as linhas visiveis E o total
da OS. Uma linha escondida com valor faria as duas coisas divergirem, e o cliente
receberia um documento que nao fecha — pior do que ver a peca.

SEGURANCA (banco de cliente em producao):
- SOMENTE `ADD COLUMN` — no SQLite e instantaneo, NAO recria a tabela.
- `visivel_cliente` com `server_default="1"`: todo item que ja existe nasce
  VISIVEL, exatamente como e impresso hoje. Nenhuma OS antiga muda de aparencia.
- `custo_unitario` nasce NULL: nao inventamos gasto retroativo em OS antiga. O
  relatorio le NULL como "sem custo declarado" e nao como "custo zero apurado".
- Guarda de existencia por coluna -> idempotente. Necessario porque o
  `create_all` roda ANTES das migrations no startup.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c8d9e0f1a2b3'
down_revision: Union[str, Sequence[str], None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _colunas(tabela: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {coluna["name"] for coluna in inspector.get_columns(tabela)}


def upgrade() -> None:
    colunas = _colunas("ordem_servico_itens")

    if "custo_unitario" not in colunas:
        op.add_column(
            "ordem_servico_itens",
            sa.Column("custo_unitario", sa.Integer(), nullable=True),
        )

    if "visivel_cliente" not in colunas:
        op.add_column(
            "ordem_servico_itens",
            sa.Column(
                "visivel_cliente",
                sa.Boolean(),
                nullable=False,
                server_default="1",
            ),
        )


def downgrade() -> None:
    colunas = _colunas("ordem_servico_itens")

    if "visivel_cliente" in colunas:
        op.drop_column("ordem_servico_itens", "visivel_cliente")

    if "custo_unitario" in colunas:
        op.drop_column("ordem_servico_itens", "custo_unitario")
