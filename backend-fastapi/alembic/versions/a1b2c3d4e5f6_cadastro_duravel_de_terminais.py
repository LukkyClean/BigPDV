"""cadastro duravel de terminais (nome e papel que sobrevivem ao logout)

Revision ID: a1b2c3d4e5f6
Revises: c4d5e6f7a8b9
Create Date: 2026-08-17

`terminais_conectados` e tabela de PRESENCA: esvaziada no boot, no shutdown, e
perde a linha no logout. As colunas `nome` e `papel` foram postas la e evaporam
junto -- o dono marca o PC dele como RETAGUARDA, sai no fim do dia, e amanha a
maquina voltou a ser um caixa qualquer.

Esta migration cria a tabela `terminais`, que guarda o que a loja sabe sobre
cada maquina e continua sabendo amanha. A de presenca segue existindo e segue
sendo esvaziada -- presenca velha e pior que presenca nenhuma.

AS COLUNAS ANTIGAS NAO SAO REMOVIDAS AQUI, de proposito. Elas foram criadas
pela migration da fase 1 desta mesma branch e ja estao no banco de quem testou;
remove-las agora obrigaria um rebuild do sidecar so para apagar duas colunas que
nao atrapalham. Ficam mortas e documentadas no modelo, e saem numa faxina
propria quando a fase 3 estiver rodando na loja.

SEM DEFAULT PARA `papel`: NULL significa PDV, que e o comportamento seguro.
Uma maquina que ninguem configurou continua sendo cobrada por
`exigir_caixa_aberto`. RETAGUARDA e excecao explicita, nunca fallback.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Guarda pela PRESENCA do que a migration cria, e nao pela ausencia: o
    # `create_all()` do startup roda ANTES das migrations e pode ter criado a
    # tabela vazia. Sem esta condicao, o upgrade quebraria no cliente atualizado.
    if insp.has_table("terminais"):
        return

    op.create_table(
        "terminais",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "empresa_id",
            sa.Integer(),
            sa.ForeignKey("empresas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("hwid", sa.String(length=255), nullable=False),
        sa.Column("nome", sa.String(length=60), nullable=True),
        sa.Column("papel", sa.String(length=20), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_terminais_hwid", "terminais", ["hwid"], unique=True)
    op.create_index("ix_terminais_empresa_id", "terminais", ["empresa_id"])

    # Aproveita o que ja foi digitado: quem testou a fase 1 e nomeou a maquina
    # nao deve perder o nome so porque a casa mudou. So copia o que existe, e
    # so quando a tabela de presenca ainda tem as colunas.
    colunas_presenca = {c["name"] for c in insp.get_columns("terminais_conectados")} \
        if insp.has_table("terminais_conectados") else set()

    if {"hwid", "nome", "papel"} <= colunas_presenca:
        empresa = bind.execute(sa.text("SELECT id FROM empresas ORDER BY id LIMIT 1")).first()
        if empresa:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO terminais (empresa_id, hwid, nome, papel, ativo,
                                           criado_em, atualizado_em)
                    SELECT :empresa_id, hwid, nome, papel, 1,
                           CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                      FROM terminais_conectados
                     WHERE hwid IS NOT NULL
                       AND (nome IS NOT NULL OR papel IS NOT NULL)
                    """
                ),
                {"empresa_id": empresa[0]},
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("terminais"):
        return
    op.drop_index("ix_terminais_empresa_id", table_name="terminais")
    op.drop_index("ix_terminais_hwid", table_name="terminais")
    op.drop_table("terminais")
