"""medidas da sacola viram referencias

Migra `dados_adicionais.medidas` -> `dados_adicionais.referencias` nas OS de
sacola da serigrafia.

O campo de sacola era uma linha de texto so ("Medidas (L x A x fole)"). O dono
nao trabalha assim: ele trabalha por REFERENCIA ("20.1", "22", "Bolo"), e uma
mesma producao sai com varios tamanhos. O campo virou `referencias`, do tipo
`lista` (repetivel) -- e com isso `medidas` deixou de ser desenhado.

Sem esta migracao o valor continuaria no banco mas sumiria da tela E da via
impressa (as duas sao dirigidas pelo contrato do segmento): uma OS aberta com
"30x40x10" perderia a instrucao de producao no meio do trabalho.

NAO APAGA `medidas`. So acrescenta `referencias` com o valor antigo dentro. O
custo de manter a chave orfa e zero (JSON livre, ninguem le), e o de apagar
seria irreversivel se a conversao estiver errada em algum caso que nao previ.

Idempotente: pula quem ja tem `referencias`, entao rodar duas vezes nao duplica.

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
"""
import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, Sequence[str], None] = 'd3e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABELA = 'ordens_servico'
COLUNA = 'dados_adicionais'

# So OS de sacola: em camisa `medidas` nao existe, e mexer em dado de outro
# tipo de trabalho seria escrever onde ninguem pediu.
TIPOS_DE_SACOLA = {'sacola_plastica', 'sacola_papel'}


def _tabela_disponivel(conexao) -> bool:
    inspetor = sa.inspect(conexao)
    if TABELA not in inspetor.get_table_names():
        return False
    return COLUNA in {c['name'] for c in inspetor.get_columns(TABELA)}


def upgrade() -> None:
    conexao = op.get_bind()
    if not _tabela_disponivel(conexao):
        return

    linhas = conexao.execute(
        sa.text(f"SELECT id, {COLUNA} FROM {TABELA} WHERE {COLUNA} IS NOT NULL")
    ).fetchall()

    for os_id, bruto in linhas:
        # A coluna e JSON: o driver pode devolver dict ja decodificado ou texto.
        if isinstance(bruto, str):
            try:
                dados = json.loads(bruto)
            except (json.JSONDecodeError, TypeError):
                continue
        else:
            dados = bruto

        if not isinstance(dados, dict):
            continue
        if dados.get('tipo_trabalho') not in TIPOS_DE_SACOLA:
            continue
        if dados.get('referencias'):
            continue  # ja migrada

        medida = dados.get('medidas')
        if not isinstance(medida, str) or not medida.strip():
            continue

        dados['referencias'] = [medida.strip()]

        conexao.execute(
            sa.text(f"UPDATE {TABELA} SET {COLUNA} = :dados WHERE id = :id"),
            {"dados": json.dumps(dados, ensure_ascii=False), "id": os_id},
        )


def downgrade() -> None:
    """
    Remove apenas as `referencias` de UM item que sejam copia exata de `medidas`
    -- ou seja, o que esta migracao criou. Lista com mais de um item foi o
    usuario que montou depois, e apagar isso seria destruir trabalho dele.
    """
    conexao = op.get_bind()
    if not _tabela_disponivel(conexao):
        return

    linhas = conexao.execute(
        sa.text(f"SELECT id, {COLUNA} FROM {TABELA} WHERE {COLUNA} IS NOT NULL")
    ).fetchall()

    for os_id, bruto in linhas:
        if isinstance(bruto, str):
            try:
                dados = json.loads(bruto)
            except (json.JSONDecodeError, TypeError):
                continue
        else:
            dados = bruto

        if not isinstance(dados, dict):
            continue

        referencias = dados.get('referencias')
        medida = dados.get('medidas')
        if (
            isinstance(referencias, list)
            and len(referencias) == 1
            and isinstance(medida, str)
            and referencias[0] == medida.strip()
        ):
            dados.pop('referencias')
            conexao.execute(
                sa.text(f"UPDATE {TABELA} SET {COLUNA} = :dados WHERE id = :id"),
                {"dados": json.dumps(dados, ensure_ascii=False), "id": os_id},
            )
