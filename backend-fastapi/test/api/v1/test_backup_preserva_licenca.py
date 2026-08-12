"""
Regressao: a licenca NUNCA pode viajar dentro de um restore.

`configuracoes_licenca.chave_ativacao` e cifrada em AES-256-GCM com chave
derivada do HWID da maquina. No boot, verificar_licenca_ativa decifra esse campo
com o HWID LOCAL e, falhando, levanta CLONAGEM_DETECTADA — antes de consultar a
nuvem, que nem chega a ser chamada.

Como o restore troca o ARQUIVO inteiro do banco, a linha de licenca do backup
entraria junto. O cenario que isso quebra e exatamente o que justifica ter backup
em nuvem: o servidor da loja queimou, o dono instala numa maquina nova, entra na
conta e restaura — e o sistema subiria bloqueado, acusando-o de ter copiado o
banco.

A licenca do cliente e UMA so e vive na nuvem; entre maquinas muda apenas como
ela fica cifrada no disco. Por isso a linha local e sempre a correta.
"""

import os
import sqlite3

import pytest

from app.services.backup import _preserve_local_license, LICENSE_TABLE
from app.services.licenca import encriptar_valor, decriptar_valor

HWID_SERVIDOR_ANTIGO = "HWID-DO-SERVIDOR-QUE-QUEIMOU"
HWID_MAQUINA_NOVA = "HWID-DA-MAQUINA-FORMATADA"
CHAVE_DO_CLIENTE = "CHAVE-ATIVACAO-UNICA-DO-CLIENTE"

DDL_LICENCA = f"""
CREATE TABLE {LICENSE_TABLE} (
    id INTEGER PRIMARY KEY,
    cliente_id TEXT,
    hwid TEXT,
    licenca_id TEXT,
    chave_ativacao TEXT,
    token TEXT
)
"""


def _criar_banco(caminho: str, hwid: str | None, token: str = "tok") -> None:
    """Cria um SQLite com a tabela de licenca; hwid=None cria a tabela vazia."""
    conn = sqlite3.connect(caminho)
    try:
        conn.execute(DDL_LICENCA)
        if hwid is not None:
            conn.execute(
                f"INSERT INTO {LICENSE_TABLE} "
                "(id, cliente_id, hwid, licenca_id, chave_ativacao, token) "
                "VALUES (1, 'cliente-abc', ?, 'lic-abc', ?, ?)",
                (hwid, encriptar_valor(CHAVE_DO_CLIENTE, hwid), token),
            )
        conn.commit()
    finally:
        conn.close()


def _ler_licenca(caminho: str) -> list[tuple]:
    conn = sqlite3.connect(caminho)
    try:
        return conn.execute(
            f"SELECT hwid, chave_ativacao FROM {LICENSE_TABLE}"
        ).fetchall()
    finally:
        conn.close()


@pytest.fixture
def bancos(tmp_path, monkeypatch):
    """
    Monta as duas pontas do restore:
      - producao: a maquina nova, ja logada (licenca com o HWID novo)
      - staging: o banco que veio do backup (licenca do servidor que queimou)
    """
    producao = str(tmp_path / "start_big.db")
    staging = str(tmp_path / "staging_start_big.db")

    _criar_banco(producao, HWID_MAQUINA_NOVA, token="token-novo")
    _criar_banco(staging, HWID_SERVIDOR_ANTIGO, token="token-antigo")

    # _preserve_local_license le o banco de producao por `database_path`.
    monkeypatch.setattr("app.services.backup.database_path", producao)

    return producao, staging


def test_licenca_do_backup_nao_entra_em_producao(bancos):
    """O caso central: a linha do servidor antigo nao pode sobreviver ao restore."""
    _, staging = bancos

    _preserve_local_license(staging)

    linhas = _ler_licenca(staging)
    assert len(linhas) == 1, "deve restar exatamente uma licenca"

    hwid, _ = linhas[0]
    assert hwid == HWID_MAQUINA_NOVA
    assert hwid != HWID_SERVIDOR_ANTIGO, "a licenca do backup vazou para producao"


def test_licenca_preservada_decifra_na_maquina_nova(bancos):
    """
    O que realmente importa: depois do restore, o boot consegue decifrar.
    E este o passo que levantava CLONAGEM_DETECTADA.
    """
    _, staging = bancos

    _preserve_local_license(staging)

    _, chave_cifrada = _ler_licenca(staging)[0]

    # Exatamente o que verificar_licenca_ativa faz no passo 3.
    assert decriptar_valor(chave_cifrada, HWID_MAQUINA_NOVA) == CHAVE_DO_CLIENTE


def test_sem_licenca_local_a_do_backup_e_descartada(tmp_path, monkeypatch):
    """
    Restaurar numa maquina ainda sem licenca deixa a tabela VAZIA (o sistema
    pede o login) em vez de subir bloqueado com a licenca de outra maquina.
    """
    producao = str(tmp_path / "start_big.db")
    staging = str(tmp_path / "staging_start_big.db")

    _criar_banco(producao, None)  # tabela existe, sem licenca
    _criar_banco(staging, HWID_SERVIDOR_ANTIGO)

    monkeypatch.setattr("app.services.backup.database_path", producao)

    resultado = _preserve_local_license(staging)

    assert _ler_licenca(staging) == []
    assert "descartada" in resultado


def test_banco_de_producao_inexistente_nao_quebra(tmp_path, monkeypatch):
    """Instalacao limpa, sem banco algum: descarta a do backup e segue."""
    staging = str(tmp_path / "staging_start_big.db")
    _criar_banco(staging, HWID_SERVIDOR_ANTIGO)

    monkeypatch.setattr(
        "app.services.backup.database_path", str(tmp_path / "nao_existe.db")
    )

    _preserve_local_license(staging)

    assert _ler_licenca(staging) == []


def test_backup_antigo_sem_a_tabela_nao_quebra(tmp_path, monkeypatch):
    """
    Backup feito antes da tabela existir: as migracoes a criam no proprio boot,
    entao a funcao so precisa nao explodir.
    """
    producao = str(tmp_path / "start_big.db")
    staging = str(tmp_path / "staging_start_big.db")

    _criar_banco(producao, HWID_MAQUINA_NOVA)

    conn = sqlite3.connect(staging)
    conn.execute("CREATE TABLE qualquer_outra (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

    monkeypatch.setattr("app.services.backup.database_path", producao)

    resultado = _preserve_local_license(staging)

    assert "nao tem a tabela" in resultado


def test_colunas_diferentes_entre_backup_e_local(tmp_path, monkeypatch):
    """
    Backup anterior a uma migracao que mexeu na tabela: preserva o que existe
    nos dois lados, sem estourar por causa da coluna que falta.
    """
    producao = str(tmp_path / "start_big.db")
    staging = str(tmp_path / "staging_start_big.db")

    _criar_banco(producao, HWID_MAQUINA_NOVA)

    # Staging sem as colunas `token` e `licenca_id`.
    conn = sqlite3.connect(staging)
    conn.execute(
        f"CREATE TABLE {LICENSE_TABLE} "
        "(id INTEGER PRIMARY KEY, cliente_id TEXT, hwid TEXT, chave_ativacao TEXT)"
    )
    conn.execute(
        f"INSERT INTO {LICENSE_TABLE} VALUES (1, 'cliente-abc', ?, ?)",
        (HWID_SERVIDOR_ANTIGO, encriptar_valor(CHAVE_DO_CLIENTE, HWID_SERVIDOR_ANTIGO)),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr("app.services.backup.database_path", producao)

    _preserve_local_license(staging)

    linhas = _ler_licenca(staging)
    assert len(linhas) == 1
    hwid, chave = linhas[0]
    assert hwid == HWID_MAQUINA_NOVA
    assert decriptar_valor(chave, HWID_MAQUINA_NOVA) == CHAVE_DO_CLIENTE
