"""mercado vira pdv no segmento da empresa

Revision ID: b3c4d5e6f7a8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-15

O produto atende adega, mercearia, papelaria e distribuicao com o MESMO motor,
entao o valor gravado passou a se chamar 'pdv' -- o nome tem que dizer o que a
coisa e, nao o ramo de um cliente.

RISCO BAIXO, e vale registrar por que: `empresas.segmento` e String(50)
nullable, texto puro. Nao ha enum no banco nem constraint para brigar, entao o
UPDATE nao pode falhar por integridade.

NA PRATICA DEVE TOCAR ZERO LINHAS: as tres lojas em producao sao
assistencia_tecnica, oficina_mecanica e serigrafia. Esta migration existe para o
caso de alguma instalacao ter escolhido "Mercado" no onboarding. Se ficasse para
tras, essa loja teria um segmento que o `Literal` de SEGMENTOS_VALIDOS recusa --
e o sintoma seria falha ao salvar os dados da empresa, sem relacao aparente com
esta mudanca.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("empresas"):
        return
    bind.execute(
        sa.text("UPDATE empresas SET segmento = 'pdv' WHERE segmento = 'mercado'")
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("empresas"):
        return
    bind.execute(
        sa.text("UPDATE empresas SET segmento = 'mercado' WHERE segmento = 'pdv'")
    )
