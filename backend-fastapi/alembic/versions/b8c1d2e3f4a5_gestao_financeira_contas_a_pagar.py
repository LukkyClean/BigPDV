"""gestao financeira: plano de contas, contas bancarias e contas a pagar

Revision ID: b8c1d2e3f4a5
Revises: d1a2b3c4e5f6
Create Date: 2026-08-28 11:40:00.000000

Onda 1 do modulo de gestao financeira. Cria as quatro tabelas do lado das
DESPESAS e acrescenta ao livro do dinheiro a coluna que diz de qual conta o
dinheiro saiu.

  planos_conta          categorias de despesa e receita
  contas_bancarias      onde o dinheiro fica (gaveta, banco)
  contas_pagar          o que a loja deve
  historico_financeiro  trilha de auditoria dos documentos

  movimentacoes_financeiras.conta_bancaria_id  (nova coluna, nullable)

NADA e migrado de dado: nao ha schema antigo equivalente, este modulo nao
existia. Por isso a migration e puramente aditiva e nao mexe em linha nenhuma
que ja esteja no banco da loja.

DEFENSIVA CONTRA O create_all(). No startup, tarefas.py roda create_all()
ANTES das migrations, entao numa instalacao que sobe ja com o codigo novo as
tabelas podem existir antes desta migration rodar. Cada passo confere a
presenca antes de criar -- do contrario o upgrade quebraria no boot do cliente
com "table already exists", que e exatamente o tipo de falha que derruba loja.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c1d2e3f4a5'
down_revision: Union[str, Sequence[str], None] = 'd1a2b3c4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tem_tabela(insp, nome: str) -> bool:
    return nome in insp.get_table_names()


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # -----------------------------------------------------------------
    # 1) planos_conta
    # -----------------------------------------------------------------
    if not _tem_tabela(insp, "planos_conta"):
        op.create_table(
            "planos_conta",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column(
                "empresa_id", sa.Integer(),
                sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False,
            ),
            sa.Column("nome", sa.String(length=100), nullable=False),
            sa.Column("tipo", sa.String(length=10), nullable=False, server_default="DESPESA"),
            sa.Column("padrao", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("empresa_id", "nome", name="uq_plano_conta_empresa_nome"),
        )
        op.create_index("ix_planos_conta_empresa_id", "planos_conta", ["empresa_id"])
        op.create_index("ix_planos_conta_tipo", "planos_conta", ["tipo"])

    # -----------------------------------------------------------------
    # 2) contas_bancarias
    # -----------------------------------------------------------------
    if not _tem_tabela(insp, "contas_bancarias"):
        op.create_table(
            "contas_bancarias",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column(
                "empresa_id", sa.Integer(),
                sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False,
            ),
            sa.Column("nome", sa.String(length=100), nullable=False),
            sa.Column("tipo", sa.String(length=10), nullable=False, server_default="BANCO"),
            sa.Column("principal", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("empresa_id", "nome", name="uq_conta_bancaria_empresa_nome"),
        )
        op.create_index("ix_contas_bancarias_empresa_id", "contas_bancarias", ["empresa_id"])

    # -----------------------------------------------------------------
    # 3) contas_pagar
    # -----------------------------------------------------------------
    if not _tem_tabela(insp, "contas_pagar"):
        op.create_table(
            "contas_pagar",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column(
                "empresa_id", sa.Integer(),
                sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False,
            ),
            sa.Column("descricao", sa.String(length=255), nullable=False),
            sa.Column(
                "plano_conta_id", sa.Integer(),
                sa.ForeignKey("planos_conta.id", ondelete="SET NULL"), nullable=True,
            ),
            sa.Column(
                "fornecedor_id", sa.Integer(),
                sa.ForeignKey("fornecedores.id", ondelete="SET NULL"), nullable=True,
            ),
            sa.Column("valor", sa.Integer(), nullable=False),
            sa.Column("vencimento", sa.Date(), nullable=False),
            sa.Column("status", sa.String(length=10), nullable=False, server_default="PENDENTE"),
            sa.Column("valor_pago", sa.Integer(), nullable=True),
            sa.Column("pago_em", sa.DateTime(), nullable=True),
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
            sa.Column("recorrente", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("observacao", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("valor > 0", name="ck_conta_pagar_valor_positivo"),
            sa.CheckConstraint(
                "(status = 'PAGA' AND pago_em IS NOT NULL AND valor_pago IS NOT NULL)"
                " OR (status <> 'PAGA' AND pago_em IS NULL AND valor_pago IS NULL)",
                name="ck_conta_pagar_baixa_coerente",
            ),
        )
        op.create_index("ix_contas_pagar_empresa_id", "contas_pagar", ["empresa_id"])
        op.create_index("ix_contas_pagar_vencimento", "contas_pagar", ["vencimento"])
        op.create_index("ix_contas_pagar_status", "contas_pagar", ["status"])
        op.create_index("ix_contas_pagar_criado_em", "contas_pagar", ["criado_em"])
        op.create_index("ix_contas_pagar_plano_conta_id", "contas_pagar", ["plano_conta_id"])
        op.create_index("ix_contas_pagar_fornecedor_id", "contas_pagar", ["fornecedor_id"])

    # -----------------------------------------------------------------
    # 4) historico_financeiro
    # -----------------------------------------------------------------
    if not _tem_tabela(insp, "historico_financeiro"):
        op.create_table(
            "historico_financeiro",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column(
                "empresa_id", sa.Integer(),
                sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False,
            ),
            sa.Column("entidade", sa.String(length=30), nullable=False),
            sa.Column("entidade_id", sa.Integer(), nullable=False),
            sa.Column("campo", sa.String(length=50), nullable=False),
            sa.Column("valor_antigo", sa.Text(), nullable=True),
            sa.Column("valor_novo", sa.Text(), nullable=True),
            sa.Column(
                "funcionario_id", sa.Integer(),
                sa.ForeignKey("funcionarios.id", ondelete="SET NULL"), nullable=True,
            ),
            sa.Column("funcionario_nome", sa.String(length=255), nullable=True),
            sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_historico_financeiro_empresa_id", "historico_financeiro", ["empresa_id"])
        op.create_index("ix_historico_financeiro_entidade", "historico_financeiro", ["entidade"])
        op.create_index(
            "ix_historico_financeiro_entidade_id", "historico_financeiro", ["entidade_id"]
        )
        op.create_index("ix_historico_financeiro_criado_em", "historico_financeiro", ["criado_em"])

    # -----------------------------------------------------------------
    # 5) movimentacoes_financeiras.conta_bancaria_id
    # -----------------------------------------------------------------
    # A tabela existe desde o modulo de caixa; aqui so ganha a coluna. Nullable
    # e sem default: as linhas antigas ficam com NULL, que significa "nao se sabe
    # de qual conta saiu" -- e e a verdade, nao havia onde registrar.
    if _tem_tabela(insp, "movimentacoes_financeiras") and not _tem_coluna(
        insp, "movimentacoes_financeiras", "conta_bancaria_id"
    ):
        # batch_alter_table porque o SQLite nao sabe ADD CONSTRAINT: o Alembic
        # recria a tabela por baixo. Sem isto a FK seria silenciosamente perdida.
        with op.batch_alter_table("movimentacoes_financeiras") as batch:
            batch.add_column(sa.Column("conta_bancaria_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                "fk_mov_financeira_conta_bancaria",
                "contas_bancarias",
                ["conta_bancaria_id"],
                ["id"],
                ondelete="SET NULL",
            )
        op.create_index(
            "ix_movimentacoes_financeiras_conta_bancaria_id",
            "movimentacoes_financeiras",
            ["conta_bancaria_id"],
        )


def downgrade() -> None:
    """Desfaz na ordem inversa das dependencias.

    O downgrade APAGA as contas cadastradas -- nao ha para onde salva-las num
    schema que nao tem o modulo. E o mesmo custo de qualquer downgrade que
    remove tabela, e a razao de este caminho nunca ser usado em loja.
    """
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if _tem_tabela(insp, "movimentacoes_financeiras") and _tem_coluna(
        insp, "movimentacoes_financeiras", "conta_bancaria_id"
    ):
        with op.batch_alter_table("movimentacoes_financeiras") as batch:
            batch.drop_column("conta_bancaria_id")

    for tabela in ("historico_financeiro", "contas_pagar", "contas_bancarias", "planos_conta"):
        if _tem_tabela(insp, tabela):
            op.drop_table(tabela)
