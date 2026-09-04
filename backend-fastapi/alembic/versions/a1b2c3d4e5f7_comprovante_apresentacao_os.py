"""apresentacao dos comprovantes de OS (folha e densidade)

Só a FORMA do comprovante. O conteúdo é invariante — dados da empresa, do
cliente com endereço, itens discriminados e resumo do pagamento saem sempre.
Ver backend-fastapi/docs/comprovantes-perfil-plano.md

Os defaults ('A4', 'normal') reproduzem exatamente a saída atual: uma loja que
atualizar e nunca abrir a tela não percebe diferença nenhuma no papel.

Guardada pela presença das colunas porque o `create_all()` roda ANTES das
migrações no startup (ver core/tarefas.py e CLAUDE.md): num banco novo a tabela
já chega com as colunas e o add_column falharia.

Revision ID: a1b2c3d4e5f7
Revises: f1a2b3c4d5e6
Create Date: 2026-08-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELA = "configuracoes_os"

COLUNAS = (
    ("comprovante_entrada_folha", sa.String(length=2), "A4"),
    ("comprovante_entrada_densidade", sa.String(length=10), "normal"),
    ("comprovante_entrega_folha", sa.String(length=2), "A4"),
    ("comprovante_entrega_densidade", sa.String(length=10), "normal"),
)


def _colunas_existentes() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if TABELA not in inspector.get_table_names():
        return set()
    return {c["name"] for c in inspector.get_columns(TABELA)}


def upgrade() -> None:
    existentes = _colunas_existentes()
    if not existentes:
        return  # tabela ainda não existe; o create_all cuida dela

    for nome, tipo, padrao in COLUNAS:
        if nome in existentes:
            continue
        # server_default preenche as linhas JÁ existentes; sem ele o NOT NULL
        # falharia em qualquer loja que já tenha configuração de OS gravada.
        op.add_column(
            TABELA,
            sa.Column(nome, tipo, nullable=False, server_default=padrao),
        )


def downgrade() -> None:
    existentes = _colunas_existentes()
    for nome, _tipo, _padrao in reversed(COLUNAS):
        if nome in existentes:
            op.drop_column(TABELA, nome)
