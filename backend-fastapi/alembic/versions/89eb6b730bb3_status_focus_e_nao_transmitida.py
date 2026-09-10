"""documento_fiscal: status_focus e limpeza das notas nunca transmitidas

Revision ID: 89eb6b730bb3
Revises: e5b7d1c3a920
Create Date: 2026-09-10 15:10:00.000000

CONTEXTO:
Duas coisas, nascidas do mesmo defeito: tres desfechos diferentes viravam um so,
e por isso uma lista de "rejeitadas" nao dizia quais notas chegaram na SEFAZ.

1. `documento_fiscal.status_focus` — o status CRU da emissora, ao lado do
   normalizado. `denegado` e `erro_autorizacao` viram ambos uma recusa no campo
   `status`, e sao coisas diferentes: denegada e decisao da SEFAZ sobre o
   CONTRIBUINTE, e reenviar nao adianta.

2. Os fantasmas. A reemissao cria uma linha PENDENTE com `ref_api` nova e NAO
   transmite. Algo consultava essas linhas, a emissora respondia 404, e o 404
   virava REJEITADA -- nota que nunca saiu do predio aparecia como recusada pela
   SEFAZ. Pior: PENDENTE conta como documento ATIVO, entao cada fantasma
   trancava a venda dele em "ja possui uma emissao em andamento", para sempre.

   Estas linhas passam a NAO_TRANSMITIDA, que nao e consultado nem tranca venda.

SEGURANCA:
- Decide pela AUSENCIA da coluna: o create_all() do startup roda ANTES das
  migracoes e ja pode ter criado a coluna numa instalacao nova. Testar a
  presenca do schema novo e o que mantem a migracao idempotente nos dois
  caminhos. Ver CLAUDE.md.
- A conversao de status so alcanca PENDENTE. Nao toca em AUTORIZADA, PROCESSANDO
  nem INDETERMINADA -- em especial INDETERMINADA, que significa "foi transmitida
  e nao sabemos o desfecho" e cuja reemissao produziria nota duplicada.
- PENDENTE so nasce da reemissao. A emissao cria o documento ja como
  PROCESSANDO, e `salvar_documento` so da flush dentro da transacao da request:
  um processo que morre no meio do HTTP nao deixa linha nenhuma. Por isso
  "PENDENTE => nunca transmitida" e seguro aqui.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '89eb6b730bb3'
down_revision: Union[str, Sequence[str], None] = 'e5b7d1c3a920'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABELA = "documento_fiscal"
COLUNA = "status_focus"


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not insp.has_table(TABELA):
        return

    colunas = {c["name"] for c in insp.get_columns(TABELA)}
    if COLUNA not in colunas:
        op.add_column(TABELA, sa.Column(COLUNA, sa.String(30), nullable=True))

    # Os fantasmas. Idempotente por construcao: depois de rodar nao sobra
    # PENDENTE para converter, e rodar de novo nao acha nada.
    conn.execute(
        sa.text(
            "UPDATE documento_fiscal "
            "SET status = 'NAO_TRANSMITIDA', "
            "    mensagem_sefaz = COALESCE(mensagem_sefaz, "
            "        'Tentativa criada e nunca transmitida a emissora.') "
            "WHERE status = 'PENDENTE'"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not insp.has_table(TABELA):
        return

    # O status volta a PENDENTE para nao deixar um valor que o codigo antigo
    # nao conhece. O codigo antigo tratava PENDENTE como consultavel -- e o
    # defeito volta junto, que e o que downgrade significa.
    conn.execute(
        sa.text(
            "UPDATE documento_fiscal SET status = 'PENDENTE' "
            "WHERE status = 'NAO_TRANSMITIDA'"
        )
    )

    colunas = {c["name"] for c in insp.get_columns(TABELA)}
    if COLUNA in colunas:
        op.drop_column(TABELA, COLUNA)
