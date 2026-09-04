"""caixa e livro do dinheiro (fase 1 do PDV: so schema)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f7
Create Date: 2026-08-15

FASE 1 DO PDV -- SO SCHEMA. Nenhum codigo de negocio le ou escreve nada disto
ainda. Depois desta migration a loja continua vendendo exatamente como vendia:
as colunas novas ficam NULL e as chaves de configuracao nascem com o valor que
reproduz o comportamento de hoje.

O que entra:
  1. sessao_caixa            -> terminal_hwid, saldo_final_informado e a trava
                                de UMA sessao aberta por terminal
  2. movimentacoes_financeiras -> tabela nova: o livro-razao unico do dinheiro
  3. pagamentos_venda        -> sessao_caixa_id
  4. ordem_servico_pagamentos -> sessao_caixa_id e data_pagamento
  5. configuracoes_vendas    -> as 4 chaves do controle de caixa
  6. terminais_conectados    -> nome e papel do terminal

NOTAS DE PROJETO
- Guarda por existencia (tabela/coluna/indice) em tudo: o `create_all()` roda
  ANTES das migrations no startup, entao a tabela nova pode JA existir quando
  esta migration rodar. Decidir pela presenca do schema, nunca pela ausencia.
- FK nao e adicionada junto da coluna: no SQLite isso exigiria recriar a tabela.
  A integridade fica na aplicacao, como ja e o caso em toda esta base (ver
  a4b5c6d7e8f9, que estabeleceu o padrao).
- Os `server_default` das chaves de configuracao existem para as linhas que JA
  estao na tabela: sem eles, a coluna NOT NULL nao pode ser adicionada e as
  empresas ja cadastradas ficariam sem valor.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LIVRO = "movimentacoes_financeiras"


def _tem_coluna(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def _tem_indice(insp, tabela: str, indice: str) -> bool:
    return any(i["name"] == indice for i in insp.get_indexes(tabela))


def _add_coluna(insp, tabela: str, coluna: sa.Column, indexar: bool = False) -> None:
    """Acrescenta a coluna se ela ainda nao existir. Idempotente."""
    if not insp.has_table(tabela):
        return
    if _tem_coluna(insp, tabela, coluna.name):
        return
    op.add_column(tabela, coluna)
    if indexar:
        op.create_index(f"ix_{tabela}_{coluna.name}", tabela, [coluna.name])


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # -----------------------------------------------------------------
    # 1) sessao_caixa: onde a sessao foi aberta e quanto foi contado
    # -----------------------------------------------------------------
    # A tabela existe desde o schema inicial, mas nunca foi usada -- nao ha
    # nenhuma linha para migrar, so colunas a acrescentar.
    _add_coluna(insp, "sessao_caixa", sa.Column("terminal_hwid", sa.String(length=255), nullable=True), indexar=True)
    _add_coluna(insp, "sessao_caixa", sa.Column("saldo_final_informado", sa.Integer(), nullable=True))

    # A trava de uma sessao ABERTA por terminal e do banco, nao da tela: dois
    # cliques simultaneos na mesma maquina nao podem abrir dois turnos.
    if insp.has_table("sessao_caixa"):
        insp = sa.inspect(bind)  # recarrega apos os add_column acima
        if not _tem_indice(insp, "sessao_caixa", "ix_sessao_caixa_aberta_por_terminal"):
            op.create_index(
                "ix_sessao_caixa_aberta_por_terminal",
                "sessao_caixa",
                ["terminal_hwid"],
                unique=True,
                sqlite_where=sa.text("status = 'ABERTO'"),
            )

    # -----------------------------------------------------------------
    # 2) O livro do dinheiro
    # -----------------------------------------------------------------
    insp = sa.inspect(bind)
    if not insp.has_table(LIVRO):
        op.create_table(
            LIVRO,
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            # O valor e sempre positivo; quem da o sinal e o tipo.
            sa.Column("tipo", sa.String(length=10), nullable=False),
            sa.Column("origem", sa.String(length=20), nullable=False),
            sa.Column("valor", sa.Integer(), nullable=False),
            # NULL = nao passou por gaveta nenhuma (loja sem caixa, ou boleto
            # pago pelo banco, que e movimento real mas nao encosta no caixa).
            sa.Column("sessao_caixa_id", sa.Integer(), nullable=True),
            sa.Column("venda_pagamento_id", sa.Integer(), nullable=True),
            sa.Column("ordem_servico_pagamento_id", sa.Integer(), nullable=True),
            sa.Column("forma_pagamento_id", sa.Integer(), nullable=True),
            sa.Column("funcionario_id", sa.Integer(), nullable=True),
            sa.Column("funcionario_nome", sa.String(length=255), nullable=True),
            sa.Column("motivo", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    insp = sa.inspect(bind)
    if insp.has_table(LIVRO):
        for coluna in (
            "id", "tipo", "origem", "sessao_caixa_id", "venda_pagamento_id",
            "ordem_servico_pagamento_id", "funcionario_id", "criado_em",
        ):
            nome_indice = f"ix_{LIVRO}_{coluna}"
            if not _tem_indice(insp, LIVRO, nome_indice):
                op.create_index(nome_indice, LIVRO, [coluna])

    # -----------------------------------------------------------------
    # 3) e 4) O carimbo da sessao nas cobrancas
    # -----------------------------------------------------------------
    insp = sa.inspect(bind)
    _add_coluna(insp, "pagamentos_venda", sa.Column("sessao_caixa_id", sa.Integer(), nullable=True), indexar=True)

    insp = sa.inspect(bind)
    _add_coluna(insp, "ordem_servico_pagamentos", sa.Column("sessao_caixa_id", sa.Integer(), nullable=True), indexar=True)
    # Nullable de proposito: as linhas antigas nao tem instante de registro
    # recuperavel, e inventar um seria pior que admitir a lacuna.
    insp = sa.inspect(bind)
    _add_coluna(insp, "ordem_servico_pagamentos", sa.Column("data_pagamento", sa.DateTime(), nullable=True))

    # -----------------------------------------------------------------
    # 5) As chaves do controle de caixa (padrao = comportamento de hoje)
    # -----------------------------------------------------------------
    insp = sa.inspect(bind)
    for nome, padrao in (
        ("controlar_caixa", "0"),
        ("exigir_caixa_aberto", "0"),
        ("fechamento_cego", "0"),
        # A unica ligada: e a que protege dinheiro saindo. Suprimento fica livre.
        ("sangria_exige_autorizacao", "1"),
    ):
        insp = sa.inspect(bind)
        _add_coluna(
            insp,
            "configuracoes_vendas",
            sa.Column(nome, sa.Boolean(), nullable=False, server_default=padrao),
        )

    # -----------------------------------------------------------------
    # 6) Nome e papel do terminal
    # -----------------------------------------------------------------
    # Ausencia tem significado: terminal sem papel se comporta como PDV. E o que
    # faz a loja de um PC so funcionar sem configurar nada.
    insp = sa.inspect(bind)
    _add_coluna(insp, "terminais_conectados", sa.Column("nome", sa.String(length=60), nullable=True))
    insp = sa.inspect(bind)
    _add_coluna(insp, "terminais_conectados", sa.Column("papel", sa.String(length=20), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    def _drop(tabela: str, coluna: str) -> None:
        i = sa.inspect(bind)
        if not i.has_table(tabela) or not _tem_coluna(i, tabela, coluna):
            return
        try:
            op.drop_index(f"ix_{tabela}_{coluna}", table_name=tabela)
        except Exception:
            pass
        op.drop_column(tabela, coluna)

    for coluna in ("papel", "nome"):
        _drop("terminais_conectados", coluna)

    for coluna in ("sangria_exige_autorizacao", "fechamento_cego",
                   "exigir_caixa_aberto", "controlar_caixa"):
        _drop("configuracoes_vendas", coluna)

    for coluna in ("data_pagamento", "sessao_caixa_id"):
        _drop("ordem_servico_pagamentos", coluna)

    _drop("pagamentos_venda", "sessao_caixa_id")

    insp = sa.inspect(bind)
    if insp.has_table(LIVRO):
        op.drop_table(LIVRO)

    insp = sa.inspect(bind)
    if insp.has_table("sessao_caixa"):
        if _tem_indice(insp, "sessao_caixa", "ix_sessao_caixa_aberta_por_terminal"):
            op.drop_index("ix_sessao_caixa_aberta_por_terminal", table_name="sessao_caixa")
    _drop("sessao_caixa", "saldo_final_informado")
    _drop("sessao_caixa", "terminal_hwid")
