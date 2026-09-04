"""
Regressao da migracao e4f5a6b7c8d9 (medidas da sacola -> referencias).

O campo de sacola era uma linha de texto ("Medidas (L x A x fole)") e virou
`referencias`, do tipo `lista`. Como formulario E via impressa sao dirigidos
pelo contrato do segmento, o `medidas` de uma OS ja aberta sumiria das duas
telas de uma vez -- a instrucao de producao evaporaria no meio do trabalho.

Estes testes exercitam a funcao de migracao contra um SQLite de verdade, e
travam o que ela NAO pode fazer: encostar em OS de camisa, sobrescrever
referencia que o usuario montou, ou apagar o `medidas` original.
"""

import json
import sqlite3

import pytest
import sqlalchemy as sa

# A migracao vive em alembic/versions/, fora do pacote `app` -- carregada por
# caminho para poder chamar upgrade()/downgrade() direto.
import importlib.util
import pathlib

_CAMINHO = (
    pathlib.Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "e4f5a6b7c8d9_medidas_da_sacola_viram_referencias.py"
)
_spec = importlib.util.spec_from_file_location("migracao_referencias", _CAMINHO)
migracao = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(migracao)


DDL = """
CREATE TABLE ordens_servico (
    id INTEGER PRIMARY KEY,
    dados_adicionais TEXT
)
"""


@pytest.fixture
def engine(tmp_path, monkeypatch):
    """SQLite em arquivo + `op.get_bind()` apontando para ele."""
    caminho = tmp_path / "os.db"
    conn = sqlite3.connect(caminho)
    conn.execute(DDL)
    conn.commit()
    conn.close()

    eng = sa.create_engine(f"sqlite:///{caminho}")
    conexao = eng.connect()

    monkeypatch.setattr(migracao.op, "get_bind", lambda: conexao)
    yield conexao
    conexao.close()


def _inserir(conexao, os_id: int, dados: dict) -> None:
    conexao.execute(
        sa.text("INSERT INTO ordens_servico (id, dados_adicionais) VALUES (:id, :d)"),
        {"id": os_id, "d": json.dumps(dados, ensure_ascii=False)},
    )
    conexao.commit()


def _ler(conexao, os_id: int) -> dict:
    bruto = conexao.execute(
        sa.text("SELECT dados_adicionais FROM ordens_servico WHERE id = :id"),
        {"id": os_id},
    ).scalar()
    return json.loads(bruto)


def test_medida_da_sacola_vira_referencia(engine):
    _inserir(engine, 1, {"tipo_trabalho": "sacola_plastica", "medidas": "30x40x10"})

    migracao.upgrade()

    dados = _ler(engine, 1)
    assert dados["referencias"] == ["30x40x10"]
    # O original fica: apagar seria irreversivel se a conversao estivesse errada.
    assert dados["medidas"] == "30x40x10"


def test_sacola_de_papel_tambem_migra(engine):
    _inserir(engine, 1, {"tipo_trabalho": "sacola_papel", "medidas": "20x30"})

    migracao.upgrade()

    assert _ler(engine, 1)["referencias"] == ["20x30"]


def test_nao_encosta_em_os_de_camisa(engine):
    """Camisa nao tem sacola; escrever ali seria inventar dado."""
    _inserir(engine, 1, {"tipo_trabalho": "camisa", "medidas": "P"})

    migracao.upgrade()

    assert "referencias" not in _ler(engine, 1)


def test_nao_sobrescreve_referencias_ja_preenchidas(engine):
    """Idempotente: rodar de novo nao pode atropelar o que o usuario montou."""
    _inserir(engine, 1, {
        "tipo_trabalho": "sacola_plastica",
        "medidas": "30x40x10",
        "referencias": ["20.1", "22"],
    })

    migracao.upgrade()

    assert _ler(engine, 1)["referencias"] == ["20.1", "22"]


def test_medida_vazia_nao_vira_referencia_em_branco(engine):
    _inserir(engine, 1, {"tipo_trabalho": "sacola_plastica", "medidas": "   "})

    migracao.upgrade()

    assert "referencias" not in _ler(engine, 1)


def test_os_sem_dados_adicionais_nao_quebra(engine):
    engine.execute(
        sa.text("INSERT INTO ordens_servico (id, dados_adicionais) VALUES (2, NULL)")
    )
    engine.commit()
    _inserir(engine, 1, {"tipo_trabalho": "sacola_plastica", "medidas": "30x40"})

    migracao.upgrade()  # nao pode levantar

    assert _ler(engine, 1)["referencias"] == ["30x40"]


def test_downgrade_desfaz_so_o_que_a_migracao_criou(engine):
    _inserir(engine, 1, {"tipo_trabalho": "sacola_plastica", "medidas": "30x40x10"})
    _inserir(engine, 2, {
        "tipo_trabalho": "sacola_plastica",
        "medidas": "30x40x10",
        "referencias": ["20.1", "22"],  # montada pelo usuario
    })

    migracao.upgrade()
    migracao.downgrade()

    assert "referencias" not in _ler(engine, 1)
    # Trabalho do usuario sobrevive ao downgrade.
    assert _ler(engine, 2)["referencias"] == ["20.1", "22"]
