"""contas a receber

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-08-28 15:40:00.000000

Cria `contas_receber`. Puramente aditiva: nenhuma tabela existente e tocada e
nenhuma linha e migrada.

A tabela nasce para dar registro a uma promessa que o sistema JA SABIA
identificar. `registrar_pagamentos_de_venda` e a gemea da OS sempre pularam o
pagamento com vencimento futuro, com a regra escrita la -- "promessa: e conta a
receber, nao gaveta". O que faltava era a conta a receber existir.

Por isso nenhum fluxo de venda ou de OS muda de comportamento com esta
migration: eles passam a deixar um registro a mais, e so.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tem_tabela(insp, nome: str) -> bool:
    return nome in insp.get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # Defensiva contra o create_all(), que no boot roda ANTES das migrations:
    # numa instalacao que sobe direto com o codigo novo a tabela ja existe, e um
    # create cego quebraria o boot do cliente com "table already exists".
    if _tem_tabela(insp, "contas_receber"):
        return

    op.create_table(
        "contas_receber",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "empresa_id", sa.Integer(),
            sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("descricao", sa.String(length=255), nullable=False),
        sa.Column(
            "cliente_id", sa.Integer(),
            sa.ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("valor", sa.Integer(), nullable=False),
        sa.Column("taxa", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vencimento", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="PENDENTE"),
        sa.Column("valor_recebido", sa.Integer(), nullable=True),
        sa.Column("recebido_em", sa.DateTime(), nullable=True),
        sa.Column(
            "conta_bancaria_id", sa.Integer(),
            sa.ForeignKey("contas_bancarias.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column(
            "forma_pagamento_id", sa.Integer(),
            sa.ForeignKey("formas_pagamento.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column(
            "movimentacao_financeira_id", sa.Integer(),
            sa.ForeignKey("movimentacoes_financeiras.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column(
            "venda_pagamento_id", sa.Integer(),
            sa.ForeignKey("pagamentos_venda.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column(
            "ordem_servico_pagamento_id", sa.Integer(),
            sa.ForeignKey("ordem_servico_pagamentos.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("valor > 0", name="ck_conta_receber_valor_positivo"),
        sa.CheckConstraint("taxa >= 0", name="ck_conta_receber_taxa_nao_negativa"),
        sa.CheckConstraint(
            "(status = 'RECEBIDA' AND recebido_em IS NOT NULL AND valor_recebido IS NOT NULL)"
            " OR (status <> 'RECEBIDA' AND recebido_em IS NULL AND valor_recebido IS NULL)",
            name="ck_conta_receber_baixa_coerente",
        ),
    )
    for coluna in (
        "empresa_id", "cliente_id", "vencimento", "status", "criado_em",
        "venda_pagamento_id", "ordem_servico_pagamento_id",
    ):
        op.create_index(f"ix_contas_receber_{coluna}", "contas_receber", [coluna])


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if _tem_tabela(insp, "contas_receber"):
        op.drop_table("contas_receber")
