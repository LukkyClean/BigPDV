"""abertura de caixa pode exigir PIN do gerente (requer_pin_abrir_caixa)

Revision ID: a5b6c7d8e9f0
Revises: d5e6f7a8b9c0
Create Date: 2026-08-21

O vendedor de balcao abrir o caixa sozinho e o comeco do turno: define o troco
inicial, e o troco inicial e a base contra a qual o fechamento vai acusar falta
ou sobra. A loja que quer um supervisor conferindo isso agora tem a chave.

A coluna mora em `configuracoes_vendas`, e nao em `configuracoes_seguranca`
junto das oito irmas de PIN. Foi decisao do dono: e uma regra do CAIXA, e ele a
procura no bloco do caixa, ao lado de "exigir caixa aberto para vender". A
sangria ficou do outro lado (c4d5e6f7a8b9) e a linha de rodape daquele bloco
continua apontando para Seguranca -- as duas travas do caixa em telas diferentes
e o preco consciente dessa escolha.

O segredo continua sendo UM SO: a validacao le o `pin_gerente` de
`configuracoes_seguranca`. Um segundo PIN seria mais uma coisa para o lojista
esquecer.

Padrao "0" (desligado), como todas as outras chaves do caixa: loja que atualiza
e nao mexe em nada continua abrindo o caixa exatamente como abria. Ligado sem
PIN cadastrado, a abertura ficaria impossivel para quem nao e master -- o
servico avisa isso com mensagem propria, mas o padrao desligado evita o problema
em vez de explica-lo.

DECIDE PELA PRESENCA DA COLUNA, e nao pela ausencia: no startup o `create_all()`
roda ANTES das migrations, entao num banco novo a coluna ja nasce e nao ha o que
adicionar.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a5b6c7d8e9f0"
down_revision: Union[str, Sequence[str], None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("configuracoes_vendas") and not _tem_coluna(
        insp, "configuracoes_vendas", "requer_pin_abrir_caixa"
    ):
        op.add_column(
            "configuracoes_vendas",
            sa.Column(
                "requer_pin_abrir_caixa",
                sa.Boolean(),
                nullable=False,
                server_default="0",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("configuracoes_vendas") and _tem_coluna(
        insp, "configuracoes_vendas", "requer_pin_abrir_caixa"
    ):
        # DROP COLUMN existe no SQLite desde a 3.35. Se a versao for anterior, a
        # coluna fica para tras sem ninguem ler -- preferivel a migration falhar
        # e impedir o backend de subir, que e loja parada.
        try:
            op.drop_column("configuracoes_vendas", "requer_pin_abrir_caixa")
        except Exception:
            pass
