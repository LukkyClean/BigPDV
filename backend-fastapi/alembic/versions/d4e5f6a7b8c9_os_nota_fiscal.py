"""cria tabela ordem_servico_nota_fiscal (nota fiscal por OS)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-14 00:00:00.000000

CONTEXTO:
Fase 4 do módulo fiscal. Cria a tabela satélite 'ordem_servico_nota_fiscal'
com relação 1:1 opcional com 'ordens_servico'.

Diferente da venda, a OS pode gerar dois documentos distintos:
- NFe/NFCe para itens de produto (peças)
- NFSe para itens de serviço (mão de obra)

Por isso existem dois blocos de campos de resultado independentes (status_nfe,
chave_acesso_nfe... e status_nfse, numero_nfse...). Os campos de entrada
(natureza_operacao, finalidade_emissao…) são compartilhados.

A emissão real via Focus NFe é fase futura. Esta migration apenas cria a
estrutura de dados. Nenhum campo é NOT NULL exceto os_id.

SEGURANÇA (banco de cliente em produção):
- Guarda de existência por tabela → idempotente.
- FK com CASCADE DELETE: excluir uma OS remove automaticamente a nota fiscal,
  sem deixar registros órfãos.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tem_tabela(insp, tabela: str) -> bool:
    return insp.has_table(tabela)


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())

    if not _tem_tabela(insp, "ordem_servico_nota_fiscal"):
        op.create_table(
            "ordem_servico_nota_fiscal",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("os_id", sa.Integer(), nullable=False),
            # Parâmetros de entrada (compartilhados entre NFe e NFSe)
            sa.Column("natureza_operacao", sa.String(length=60), nullable=True),
            sa.Column("finalidade_emissao", sa.Integer(), nullable=True),
            sa.Column("consumidor_final", sa.Boolean(), nullable=True),
            sa.Column("indicador_presenca", sa.Integer(), nullable=True),
            sa.Column("emitir_nfe", sa.Boolean(), nullable=True, server_default="1"),
            sa.Column("emitir_nfse", sa.Boolean(), nullable=True, server_default="1"),
            # Resultado NFe/NFCe (peças — Focus NFe, fase futura)
            sa.Column("status_nfe", sa.String(length=20), nullable=True, server_default="PENDENTE"),
            sa.Column("chave_acesso_nfe", sa.String(length=44), nullable=True),
            sa.Column("numero_nfe", sa.Integer(), nullable=True),
            sa.Column("serie_nfe", sa.Integer(), nullable=True),
            sa.Column("protocolo_nfe", sa.String(length=20), nullable=True),
            sa.Column("data_autorizacao_nfe", sa.DateTime(), nullable=True),
            sa.Column("url_danfe", sa.String(length=500), nullable=True),
            sa.Column("mensagem_nfe", sa.String(length=500), nullable=True),
            sa.Column("qrcode_nfe", sa.Text(), nullable=True),
            # Resultado NFSe (mão de obra — Focus NFe, fase futura)
            sa.Column("status_nfse", sa.String(length=20), nullable=True, server_default="PENDENTE"),
            sa.Column("numero_nfse", sa.String(length=20), nullable=True),
            sa.Column("codigo_verificacao_nfse", sa.String(length=50), nullable=True),
            sa.Column("data_emissao_nfse", sa.DateTime(), nullable=True),
            sa.Column("url_nfse", sa.String(length=500), nullable=True),
            sa.Column("mensagem_nfse", sa.String(length=500), nullable=True),
            sa.Column(
                "data_atualizacao",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
            ),
            sa.ForeignKeyConstraint(
                ["os_id"],
                ["ordens_servico.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_ordem_servico_nota_fiscal_id",
            "ordem_servico_nota_fiscal",
            ["id"],
            unique=False,
        )
        op.create_index(
            "ix_ordem_servico_nota_fiscal_os_id",
            "ordem_servico_nota_fiscal",
            ["os_id"],
            unique=True,  # garante a unicidade da relação 1:1
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())

    if _tem_tabela(insp, "ordem_servico_nota_fiscal"):
        op.drop_index("ix_ordem_servico_nota_fiscal_os_id", table_name="ordem_servico_nota_fiscal")
        op.drop_index("ix_ordem_servico_nota_fiscal_id", table_name="ordem_servico_nota_fiscal")
        op.drop_table("ordem_servico_nota_fiscal")
