"""fila do caixa vira opcional (configuracoes_vendas.usar_fila_do_caixa)

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-08-21

A fila do caixa nasceu ligada junto com `controlar_caixa` (migration
b6c7d8e9f0a1), e isso estava errado: as duas coisas nao sao a mesma pergunta.

`controlar_caixa` responde "esta loja controla a gaveta?". A fila responde
"quem monta a venda e quem recebe o dinheiro sao pessoas diferentes?". Numa loja
de um PC so a resposta e nao -- e ali o botao "Enviar para o caixa" e um comando
que nunca serve, ocupando espaco na tela mais usada do sistema.

Padrao "0" (desligada), como todas as chaves do bloco do caixa: loja que
atualiza e nao mexe em nada nao ve o botao, nem o selo na lista, nem o filtro.
Quem quiser a fila liga em Configuracoes > Regras de Vendas.

A COLUNA `vendas.enviada_ao_caixa_em` NAO E TOCADA. Desligar a chave esconde a
funcionalidade, nao apaga historico: venda que ja estava na fila continua ATIVA
e finalizavel normalmente, so deixa de exibir o selo.

DECIDE PELA PRESENCA DA COLUNA, e nao pela ausencia: no startup o `create_all()`
roda ANTES das migrations, entao num banco novo a coluna ja nasce e nao ha o que
adicionar.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, Sequence[str], None] = "b6c7d8e9f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("configuracoes_vendas") and not _tem_coluna(
        insp, "configuracoes_vendas", "usar_fila_do_caixa"
    ):
        op.add_column(
            "configuracoes_vendas",
            sa.Column(
                "usar_fila_do_caixa",
                sa.Boolean(),
                nullable=False,
                server_default="0",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("configuracoes_vendas") and _tem_coluna(
        insp, "configuracoes_vendas", "usar_fila_do_caixa"
    ):
        # DROP COLUMN existe no SQLite desde a 3.35. Se a versao for anterior, a
        # coluna fica para tras sem ninguem ler -- preferivel a migration falhar
        # e impedir o backend de subir, que e loja parada.
        try:
            op.drop_column("configuracoes_vendas", "usar_fila_do_caixa")
        except Exception:
            pass
