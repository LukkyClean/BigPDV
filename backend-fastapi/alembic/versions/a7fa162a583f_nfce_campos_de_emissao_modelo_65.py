"""nfce: campos de emissao do modelo 65

Revision ID: a7fa162a583f
Revises: c6597333071d
Create Date: 2026-09-04 06:34:16.032557

CONTEXTO:
Habilita a emissao de NFC-e (modelo 65). As colunas de serie, numeracao e CSC
ja existiam em empresa_fiscal_settings; faltavam quatro coisas para emitir e
imprimir o cupom:

1. `empresa_fiscal_settings.limite_consumidor_anonimo` — teto em CENTAVOS para
   emitir sem identificar o comprador. Configuravel porque a faixa e estadual
   (na maioria das UFs R$ 10.000,00) e muda por legislacao.

2. `venda_nota_fiscal.documento_consumidor` — o CPF/CNPJ digitado no caixa.
   Fica aqui, e nao em vendas.cliente_id, para o consumidor de passagem nao
   virar cadastro.

3. `documento_fiscal.qrcode` / `url_consulta` / `valor_tributos` — o que o
   DANFE NFC-e precisa imprimir. Ficam no documento (e nao so na nota da
   venda) porque a REIMPRESSAO parte dali: sem eles seria preciso consultar o
   provedor de novo com o cliente no balcao.

SEGURANCA:
- Decide pela AUSENCIA de cada coluna: o create_all() do startup roda ANTES das
  migracoes e pode ter criado as colunas vazias numa instalacao nova. Testar a
  presenca do schema novo (e nao a ausencia) e o que mantem a migracao
  idempotente nos dois caminhos. Ver CLAUDE.md.
- Nao ha backfill de dado: `limite_consumidor_anonimo` recebe o default de
  1000000 centavos nas linhas existentes, e os demais nascem nulos.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7fa162a583f'
down_revision: Union[str, Sequence[str], None] = 'c6597333071d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LIMITE_PADRAO_CENTAVOS = 1000000  # R$ 10.000,00

# (tabela, coluna, tipo, nullable, server_default)
COLUNAS_NOVAS = [
    (
        "empresa_fiscal_settings", "limite_consumidor_anonimo",
        sa.Integer(), False, str(LIMITE_PADRAO_CENTAVOS),
    ),
    ("venda_nota_fiscal", "documento_consumidor", sa.String(14), True, None),
    ("documento_fiscal", "qrcode", sa.Text(), True, None),
    ("documento_fiscal", "url_consulta", sa.String(300), True, None),
    ("documento_fiscal", "valor_tributos", sa.Integer(), True, None),
]


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    for tabela, coluna, tipo, nullable, default in COLUNAS_NOVAS:
        if not insp.has_table(tabela):
            continue

        colunas = {c["name"] for c in insp.get_columns(tabela)}
        if coluna in colunas:
            continue

        op.add_column(
            tabela,
            sa.Column(coluna, tipo, nullable=nullable, server_default=default),
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    for tabela, coluna, _tipo, _nullable, _default in reversed(COLUNAS_NOVAS):
        if not insp.has_table(tabela):
            continue
        if coluna not in {c["name"] for c in insp.get_columns(tabela)}:
            continue
        op.drop_column(tabela, coluna)
