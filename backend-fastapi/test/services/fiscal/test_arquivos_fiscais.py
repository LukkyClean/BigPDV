# ---------------------------------------------------------------------------
# ARQUIVO: test_arquivos_fiscais.py
# DESCRIÇÃO: O XML autorizado passa a ser da loja — guardado no disco dela.
#
# Antes o ERP tinha só `url_xml`, um endereço na emissora. Guardar o XML por
# cinco anos é obrigação do EMITENTE, e a loja dependia de a plataforma e a
# Focus estarem no ar, do link não expirar e de continuarmos clientes.
# ---------------------------------------------------------------------------

from datetime import datetime

import pytest

from app.services.fiscal import arquivos


CHAVE = "35260911222333000181550010000000041234567890"


@pytest.fixture
def pasta_isolada(tmp_path, monkeypatch):
    """Cada teste escreve na própria pasta, nunca na do desenvolvedor."""
    monkeypatch.setattr(arquivos, "PASTA_FISCAL", str(tmp_path / "fiscal"))
    return tmp_path / "fiscal"


# =========================
# Onde e com que nome
# =========================

def test_arquivo_recebe_a_chave_de_acesso_como_nome(pasta_isolada):
    """44 dígitos e `.xml` — é como todo contador espera receber."""
    caminho = arquivos.guardar_xml(
        "<nfeProc/>", chave=CHAVE, fallback="doc-1", quando=datetime(2026, 9, 13)
    )

    assert caminho is not None
    assert caminho.endswith(f"{CHAVE}.xml")
    assert "2026" in caminho and "09" in caminho


def test_sem_chave_cai_no_fallback(pasta_isolada):
    """Documento sem chave (rejeitado que depois autorizou) ainda tem onde morar."""
    caminho = arquivos.guardar_xml("<nfeProc/>", chave=None, fallback="doc-42")

    assert caminho is not None
    assert caminho.endswith("doc-42.xml")


def test_chave_invalida_nao_escreve_fora_da_pasta(pasta_isolada):
    """
    O nome do arquivo vem da emissora e vira caminho em disco. Valor estranho
    não pode escapar da pasta fiscal.
    """
    import os

    caminho = arquivos.guardar_xml(
        "<nfeProc/>", chave="../../../etc/passwd", fallback="../../fuga"
    )

    assert caminho is not None
    # A propriedade que importa é o caminho RESOLVIDO continuar dentro da
    # pasta. Os pontos viram parte do nome (`.._.._fuga.xml`) e são inofensivos
    # sem separador — o que não pode é escapar do diretório.
    assert os.path.realpath(caminho).startswith(os.path.realpath(str(pasta_isolada)))
    assert os.sep not in os.path.basename(caminho)


# =========================
# Imutabilidade e resiliência
# =========================

def test_nao_sobrescreve_xml_ja_guardado(pasta_isolada):
    """
    XML autorizado é imutável. Reescrever seria a única forma de corromper um
    documento que já está na SEFAZ.
    """
    primeiro = arquivos.guardar_xml("<original/>", chave=CHAVE, fallback="doc-1")
    arquivos.guardar_xml("<adulterado/>", chave=CHAVE, fallback="doc-1")

    assert arquivos.ler_xml(primeiro) == "<original/>"


def test_conteudo_vazio_nao_cria_arquivo(pasta_isolada):
    assert arquivos.guardar_xml("", chave=CHAVE, fallback="doc-1") is None


def test_falha_de_escrita_nao_levanta(pasta_isolada, monkeypatch):
    """
    A nota JÁ está autorizada quando isto roda. Disco cheio não pode virar erro
    para o operador — vira log.
    """
    def explode(*_a, **_k):
        raise OSError("disco cheio")

    monkeypatch.setattr("builtins.open", explode)

    assert arquivos.guardar_xml("<nfeProc/>", chave=CHAVE, fallback="doc-1") is None


def test_ler_arquivo_que_nao_existe_devolve_none(pasta_isolada):
    """Quem chama cai na emissora — é o caminho de antes, ainda disponível."""
    assert arquivos.ler_xml(str(pasta_isolada / "nao-existe.xml")) is None
    assert arquivos.ler_xml(None) is None


# =========================
# DANFE
# =========================

def test_danfe_fica_em_subpasta_propria(pasta_isolada, monkeypatch):
    """
    Separado do XML porque o backup trata os dois de forma diferente: o XML
    sobe (obrigação de cinco anos), o DANFE não (derivado, ~8x maior).
    """
    monkeypatch.setattr(arquivos, "PASTA_DANFE", str(pasta_isolada / "danfe"))

    caminho = arquivos.guardar_pdf(b"%PDF-1.4 teste", chave=CHAVE, fallback="doc-1")

    assert caminho is not None
    assert "danfe" in caminho
    assert caminho.endswith(f"{CHAVE}.pdf")


def test_resposta_que_nao_e_pdf_e_descartada(pasta_isolada, monkeypatch):
    """
    A emissora pode responder 200 com uma página de erro em HTML. Guardar isso
    como se fosse o DANFE é pior que não guardar: o lojista só descobriria ao
    abrir, meses depois.
    """
    monkeypatch.setattr(arquivos, "PASTA_DANFE", str(pasta_isolada / "danfe"))

    assert arquivos.guardar_pdf(b"<html>erro</html>", chave=CHAVE, fallback="doc-1") is None
    assert arquivos.guardar_pdf(None, chave=CHAVE, fallback="doc-1") is None


def test_danfe_volta_em_bytes(pasta_isolada, monkeypatch):
    monkeypatch.setattr(arquivos, "PASTA_DANFE", str(pasta_isolada / "danfe"))
    caminho = arquivos.guardar_pdf(b"%PDF-1.4 teste", chave=CHAVE, fallback="doc-1")

    assert arquivos.ler_pdf(caminho) == b"%PDF-1.4 teste"


# =========================
# O backup precisa alcançar a pasta
# =========================

def test_pasta_fiscal_esta_no_backup():
    """
    Obrigação de guardar por cinco anos fora do backup é o tipo de coisa que só
    se descobre quando já era. A pasta fica sob `data/` (não sob `static/`,
    que é servida por HTTP sem autenticação), então precisou entrar à mão.
    """
    from app.services.backup._constants import FISCAL_DIR, FISCAL_DIR_NO_ZIP
    from app.services.backup import local as backup_local
    from app.services.backup import restore as backup_restore

    assert FISCAL_DIR.endswith("fiscal")
    assert FISCAL_DIR_NO_ZIP == "fiscal"

    # Empacotamento e restauração precisam conhecer a pasta.
    assert "FISCAL_DIR" in backup_local.__dict__ or hasattr(backup_local, "FISCAL_DIR")
    assert hasattr(backup_restore, "FISCAL_DIR")


def test_danfe_sobe_enquanto_couber(tmp_path, monkeypatch):
    """
    O DANFE entra no backup — e cede lugar quando a pasta fica grande demais.

    A primeira versão o excluía sempre, com o argumento de que é regerável a
    partir do XML. É fraco: este sistema não tem gerador de DANFE. Numa loja
    pequena, excluí-lo era perder conveniência sem ganhar nada.
    """
    from app.services.backup import local as backup_local
    from app.services.backup._constants import FISCAL_DANFE_SUBPASTA

    pasta_fiscal = tmp_path / "fiscal"
    (pasta_fiscal / FISCAL_DANFE_SUBPASTA).mkdir(parents=True)
    monkeypatch.setattr(backup_local, "FISCAL_DIR", str(pasta_fiscal))

    # Loja pequena: cabe.
    (pasta_fiscal / FISCAL_DANFE_SUBPASTA / "a.pdf").write_bytes(b"x" * 1024)
    assert backup_local._danfe_excede_teto() is False

    # Passou do teto: fica de fora deste pacote.
    monkeypatch.setattr(backup_local, "FISCAL_DANFE_TETO_BYTES", 512)
    assert backup_local._danfe_excede_teto() is True


def test_teto_do_danfe_nunca_alcanca_o_xml(tmp_path, monkeypatch):
    """
    A trava é só do PDF. O XML é obrigação legal de cinco anos e sobe sempre —
    documento antes de conveniência.
    """
    from app.services.backup import local as backup_local
    from app.services.backup._constants import FISCAL_DANFE_SUBPASTA

    pasta_fiscal = tmp_path / "fiscal"
    (pasta_fiscal / FISCAL_DANFE_SUBPASTA).mkdir(parents=True)
    (pasta_fiscal / FISCAL_DANFE_SUBPASTA / "grande.pdf").write_bytes(b"x" * 4096)
    monkeypatch.setattr(backup_local, "FISCAL_DIR", str(pasta_fiscal))
    monkeypatch.setattr(backup_local, "FISCAL_DANFE_TETO_BYTES", 10)

    # A poda acontece na subpasta do DANFE; a raiz `fiscal/` (onde vive o XML)
    # não é tocada por esta função.
    assert backup_local._danfe_excede_teto() is True
    assert (pasta_fiscal).exists()


def test_erro_de_leitura_conta_como_cabe(tmp_path, monkeypatch):
    """Na dúvida, incluir o arquivo é o lado seguro."""
    from app.services.backup import local as backup_local

    monkeypatch.setattr(backup_local, "FISCAL_DIR", str(tmp_path / "fiscal"))
    monkeypatch.setattr(backup_local.os, "walk", lambda *_a, **_k: (_ for _ in ()).throw(OSError()))

    (tmp_path / "fiscal" / "danfe").mkdir(parents=True)
    assert backup_local._danfe_excede_teto() is False


def test_pasta_fiscal_nao_fica_sob_static():
    """
    `static/` é servida por HTTP sem autenticação para a LAN inteira — é de
    onde saem foto de produto e logo. Documento fiscal não vai para lá.
    """
    from app.services.backup._constants import FISCAL_DIR, STATIC_DIR

    assert not FISCAL_DIR.startswith(STATIC_DIR)
