"""
A rede de seguranca da decisao de NAO migrar as colunas de quantidade.

`db/models/estoque.py` trocou `quantidade` de Integer para Float SEM migration,
apostando que o SQLite guarda 2.5 numa coluna declarada INTEGER sem perda (a
afinidade so converte quando a conversao e exata). A aposta e o que evita um
`batch_alter_table` recriando a tabela no banco vivo de duas lojas em producao.

O resto da suite NAO exercita isso: o conftest monta o banco com create_all, que
gera colunas REAL. Quem roda hoje na loja tem INTEGER — o schema que estes testes
recriam a mao, com o DDL antigo, para verificar o caminho completo pelo
SQLAlchemy (escrita, releitura em sessao nova, soma e subtracao).
"""

import sqlite3

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.models.estoque import Estoque

# DDL do schema ANTIGO: quantidade e companhia declaradas INTEGER.
DDL_ESTOQUE_LEGADO = """
CREATE TABLE estoque (
    id INTEGER NOT NULL,
    quantidade INTEGER,
    quantidade_ideal INTEGER,
    quantidade_minima INTEGER,
    valor_entrada INTEGER,
    custo_medio INTEGER,
    valor_varejo INTEGER NOT NULL,
    valor_atacado INTEGER,
    PRIMARY KEY (id)
)
"""


@pytest.fixture
def sessao_legada(tmp_path):
    """Sessao SQLAlchemy (modelos atuais, Float) sobre um banco de schema ANTIGO."""
    caminho = tmp_path / "legado.db"

    conn = sqlite3.connect(caminho)
    try:
        conn.execute(DDL_ESTOQUE_LEGADO)
        conn.commit()
    finally:
        conn.close()

    engine = create_engine(f"sqlite:///{caminho}")
    Session = sessionmaker(bind=engine)
    yield Session, caminho
    engine.dispose()


def _tipo_declarado(caminho, coluna="quantidade") -> str:
    conn = sqlite3.connect(caminho)
    try:
        return next(
            r[2] for r in conn.execute("PRAGMA table_info(estoque)").fetchall()
            if r[1] == coluna
        )
    finally:
        conn.close()


def test_o_schema_do_teste_e_mesmo_o_antigo(sessao_legada):
    """Guarda: se este teste falhar, os demais nao provam mais nada."""
    _, caminho = sessao_legada
    assert _tipo_declarado(caminho) == "INTEGER"


def test_dois_e_meio_kg_sobrevive_em_coluna_integer(sessao_legada):
    """2,5 kg gravado e relido numa sessao NOVA (sem cache de identidade)."""
    Session, caminho = sessao_legada

    with Session() as s:
        s.add(Estoque(id=1, quantidade=2.5, valor_varejo=1000))
        s.commit()

    with Session() as s:
        assert s.get(Estoque, 1).quantidade == 2.5

    # E no disco esta como real, nao truncado pela afinidade da coluna.
    conn = sqlite3.connect(caminho)
    try:
        valor, tipo = conn.execute(
            "SELECT quantidade, typeof(quantidade) FROM estoque WHERE id=1"
        ).fetchone()
    finally:
        conn.close()

    assert (valor, tipo) == (2.5, "real")


def test_inteiro_continua_inteiro(sessao_legada):
    """A afinidade converte quando e sem perda — e isso nao pode incomodar."""
    Session, caminho = sessao_legada

    with Session() as s:
        s.add(Estoque(id=1, quantidade=3.0, valor_varejo=1000))
        s.commit()

    with Session() as s:
        assert s.get(Estoque, 1).quantidade == 3

    conn = sqlite3.connect(caminho)
    try:
        assert conn.execute(
            "SELECT typeof(quantidade) FROM estoque WHERE id=1"
        ).fetchone()[0] == "integer"
    finally:
        conn.close()


def test_soma_e_baixa_de_estoque_nao_arredondam(sessao_legada):
    """
    O que a loja faz de verdade: somar o estoque e dar baixa de um quilo quebrado.
    Se a coluna truncasse, e aqui que o dinheiro sumiria.
    """
    Session, _ = sessao_legada

    with Session() as s:
        s.add_all([
            Estoque(id=1, quantidade=2.5, valor_varejo=1000),
            Estoque(id=2, quantidade=1.25, valor_varejo=1000),
        ])
        s.commit()

        assert s.execute(text("SELECT SUM(quantidade) FROM estoque")).scalar() == 3.75

        # Baixa de 0,75 kg sobre 2,5 kg
        item = s.get(Estoque, 1)
        item.quantidade = item.quantidade - 0.75
        s.commit()

    with Session() as s:
        assert s.get(Estoque, 1).quantidade == 1.75
