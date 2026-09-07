# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/test_tributos_xml.py
# DESCRIÇÃO: Leitura do vTotTrib no XML autorizado e a tolerância de nomes
#            entre a Focus NFe e a API intermediária.
#
# O valor aproximado dos tributos (Lei 12.741/2012) é obrigatório no DANFE
# NFC-e. A Focus o calcula pela tabela IBPT mas só o grava no XML — estes
# testes cobrem o caminho que o traz de volta.
# ---------------------------------------------------------------------------

import pytest

from app.services.fiscal.http.client_mock import FiscalClientMock
from app.services.fiscal.http.client_startbig import FiscalClientStartBig
from app.services.fiscal.tributos_xml import extrair_valor_tributos


NS = 'xmlns="http://www.portalfiscal.inf.br/nfe"'


def _xml(itens: str = "", total: str = "") -> str:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f"<nfeProc {NS}><NFe><infNFe>{itens}{total}</infNFe></NFe></nfeProc>"
    )


def _item(valor: str) -> str:
    return f"<det><imposto><vTotTrib>{valor}</vTotTrib></imposto></det>"


def _total(valor: str) -> str:
    return f"<total><ICMSTot><vTotTrib>{valor}</vTotTrib></ICMSTot></total>"


# =========================
# 1. O caso que importa: pegar o TOTAL, não o item
# =========================

def test_pega_o_vtottrib_do_total_e_nao_o_do_primeiro_item():
    """
    A armadilha central: o vTotTrib aparece uma vez por item E uma vez no
    total. Pegar o primeiro que aparece traria o tributo de um item só, e o
    cupom sairia com um valor MENOR que o correto — pior que não imprimir,
    porque parece certo.
    """
    xml = _xml(itens=_item("3.50") + _item("8.50"), total=_total("12.00"))

    assert extrair_valor_tributos(xml) == 1200  # e não 350


def test_ordem_dos_elementos_nao_muda_o_resultado():
    """O total antes dos itens continua sendo o total."""
    xml = _xml(itens=_total("12.00") + _item("3.50"))

    assert extrair_valor_tributos(xml) == 1200


# =========================
# 2. Fallback: XML sem o grupo do total
# =========================

def test_sem_icmstot_soma_os_itens():
    xml = _xml(itens=_item("3.50") + _item("8.50"))

    assert extrair_valor_tributos(xml) == 1200


def test_soma_de_varios_itens_fecha_em_centavos():
    """
    O vTotTrib da SEFAZ sempre vem com 2 casas decimais, então somar item a
    item fecha exato. O que este teste protege é o erro de ponto flutuante:
    `float("0.07") * 100` dá 7.000000000000001, e sem arredondar a soma
    escorregaria um centavo.
    """
    xml = _xml(itens=_item("0.07") + _item("0.07") + _item("0.07"))

    assert extrair_valor_tributos(xml) == 21


# =========================
# 3. Conversão e formato
# =========================

@pytest.mark.parametrize("texto, centavos", [
    ("12.00", 1200),
    ("0.01", 1),
    ("1234.56", 123456),
    ("0.00", 0),
    ("  12.00  ", 1200),   # com espaço, como alguns emissores geram
])
def test_converte_reais_para_centavos(texto, centavos):
    assert extrair_valor_tributos(_xml(total=_total(texto))) == centavos


def test_zero_e_um_valor_e_nao_ausencia():
    """`vTotTrib` zerado é resposta legítima — não pode virar None."""
    assert extrair_valor_tributos(_xml(total=_total("0.00"))) == 0


# =========================
# 4. Nada disso pode derrubar a emissão
# =========================

@pytest.mark.parametrize("entrada", [
    None,
    "",
    "isto não é xml",
    "<nfeProc><NFe></NFe></nfeProc>",           # bem formado, sem vTotTrib
])
def test_entrada_ruim_devolve_none_sem_estourar(entrada):
    """
    A nota já está autorizada quando isto roda. Uma exceção aqui perderia o
    cupom por causa de um detalhe de impressão.
    """
    assert extrair_valor_tributos(entrada) is None


def test_valor_nao_numerico_e_ignorado():
    assert extrair_valor_tributos(_xml(total=_total("abc"))) is None


def test_xml_sem_namespace_tambem_funciona():
    """Nem todo emissor declara o namespace do jeito esperado."""
    xml = "<nfeProc><total><ICMSTot><vTotTrib>7.00</vTotTrib></ICMSTot></total></nfeProc>"

    assert extrair_valor_tributos(xml) == 700


# =========================
# 5. O mock produz XML com a forma real
# =========================

def test_mock_devolve_xml_com_a_armadilha_dos_dois_niveis():
    xml = FiscalClientMock(delay=0).baixar_xml("/x.xml")

    assert xml is not None
    assert xml.count("<vTotTrib>") == 3   # dois itens + o total
    assert extrair_valor_tributos(xml) == 1200


def test_mock_nao_devolve_tributos_no_json_da_emissao():
    """Espelha a Focus: o vTotTrib só existe no XML."""
    resultado = FiscalClientMock(delay=0).emitir_nfce("nfce-1", {"numero": 1})

    assert resultado.get("valor_tributos") is None
    assert resultado["qrcode"]        # mas o QR Code vem
    assert resultado["url_consulta"]


# =========================
# 6. Tolerância aos dois vocabulários (Focus x intermediária)
# =========================

def _parse(dados: dict) -> dict:
    return FiscalClientStartBig(ambiente=2, token="t")._parse_response(dados)


def test_aceita_o_vocabulario_da_focus():
    """
    A Focus devolve `qrcode_url`, `chave_nfe`, `numero_protocolo`,
    `caminho_xml_nota_fiscal` e `url_consulta_nf`.
    """
    resultado = _parse({
        "status": "autorizado",
        "chave_nfe": "NFe4119...",
        "numero_protocolo": "135260001234567",
        "caminho_xml_nota_fiscal": "/arquivos/nota-nfe.xml",
        "caminho_danfe": "/notas/nota.html",
        "qrcode_url": "http://sefaz.pr.gov.br/nfce/qrcode?p=x",
        "url_consulta_nf": "http://sefaz.pr.gov.br/nfce/consulta",
        "status_sefaz": "100",
        "mensagem_sefaz": "Autorizado",
    })

    assert resultado["chave_acesso"] == "NFe4119..."
    assert resultado["protocolo"] == "135260001234567"
    assert resultado["url_xml"] == "/arquivos/nota-nfe.xml"
    assert resultado["url_pdf"] == "/notas/nota.html"
    assert resultado["qrcode"] == "http://sefaz.pr.gov.br/nfce/qrcode?p=x"
    assert resultado["url_consulta"] == "http://sefaz.pr.gov.br/nfce/consulta"
    assert resultado["codigo_sefaz"] == "100"


def test_aceita_o_vocabulario_da_intermediaria():
    resultado = _parse({
        "status": "autorizado",
        "chave_acesso": "NFe4119...",
        "protocolo": "135260001234567",
        "url_xml": "https://api.startbig.com.br/x.xml",
        "url_pdf": "https://api.startbig.com.br/x.pdf",
        "qrcode": "http://sefaz/qr",
        "url_consulta": "http://sefaz/consulta",
        "codigo_sefaz": 100,
        "mensagem_sefaz": "Autorizado",
    })

    assert resultado["chave_acesso"] == "NFe4119..."
    assert resultado["protocolo"] == "135260001234567"
    assert resultado["url_xml"] == "https://api.startbig.com.br/x.xml"
    assert resultado["qrcode"] == "http://sefaz/qr"
    assert resultado["url_consulta"] == "http://sefaz/consulta"


def test_o_nome_da_intermediaria_tem_precedencia():
    """
    Se os dois vierem, vale o da intermediária: é ela quem fala com o ERP, e
    quem normaliza é ela.
    """
    resultado = _parse({
        "status": "autorizado",
        "qrcode": "PREFERIDO",
        "qrcode_url": "DA_FOCUS",
    })

    assert resultado["qrcode"] == "PREFERIDO"


def test_campo_vazio_nao_vence_o_preenchido():
    """String vazia é ausência, não valor — senão o QR Code sumiria."""
    resultado = _parse({
        "status": "autorizado",
        "qrcode": "",
        "qrcode_url": "http://sefaz/qr",
    })

    assert resultado["qrcode"] == "http://sefaz/qr"


def test_ausencia_total_devolve_none():
    resultado = _parse({"status": "autorizado"})

    assert resultado["qrcode"] is None
    assert resultado["url_consulta"] is None
    assert resultado["valor_tributos"] is None


# =========================
# 7. O caminho completo, como roda na emissão
# =========================

def test_completar_tributos_busca_o_xml_e_grava_em_centavos():
    from app.db.models.documento_fiscal import DocumentoFiscal
    from app.services.fiscal.emissao import _completar_tributos_pelo_xml

    doc = DocumentoFiscal(
        id=1, tipo_documento="NFCE", origem_tipo="VENDA",
        status="AUTORIZADA", url_xml="/arquivos/nota-nfe.xml",
    )

    _completar_tributos_pelo_xml(doc, FiscalClientMock(delay=0))

    assert doc.valor_tributos == 1200


@pytest.mark.parametrize("status", ["REJEITADA", "INDETERMINADA", "PROCESSANDO"])
def test_so_busca_o_xml_de_nota_autorizada(status):
    """Nota não autorizada não tem XML — a busca seria um 404 garantido."""
    from app.db.models.documento_fiscal import DocumentoFiscal
    from app.services.fiscal.emissao import _completar_tributos_pelo_xml

    doc = DocumentoFiscal(
        id=1, tipo_documento="NFCE", origem_tipo="VENDA",
        status=status, url_xml="/arquivos/nota-nfe.xml",
    )

    _completar_tributos_pelo_xml(doc, FiscalClientMock(delay=0))

    assert doc.valor_tributos is None


def test_nao_rebusca_o_que_a_api_ja_devolveu():
    """Se a intermediária passar a repassar o vTotTrib, o GET extra some."""
    from app.db.models.documento_fiscal import DocumentoFiscal
    from app.services.fiscal.emissao import _completar_tributos_pelo_xml

    doc = DocumentoFiscal(
        id=1, tipo_documento="NFCE", origem_tipo="VENDA",
        status="AUTORIZADA", url_xml="/x.xml", valor_tributos=999,
    )

    _completar_tributos_pelo_xml(doc, _ClientQueExplode())

    assert doc.valor_tributos == 999  # e o client nem foi chamado


def test_falha_ao_baixar_o_xml_nao_derruba_a_emissao():
    """
    A nota já está autorizada quando isto roda. Perder o cupom porque um
    arquivo não baixou seria trocar um problema pequeno por um grande.
    """
    from app.db.models.documento_fiscal import DocumentoFiscal
    from app.services.fiscal.emissao import _completar_tributos_pelo_xml

    doc = DocumentoFiscal(
        id=1, tipo_documento="NFCE", origem_tipo="VENDA",
        status="AUTORIZADA", url_xml="/x.xml",
    )

    _completar_tributos_pelo_xml(doc, _ClientQueExplode())

    assert doc.valor_tributos is None  # sem exceção


def test_client_sem_o_metodo_nao_quebra():
    """Um client antigo (ou de teste) sem `baixar_xml` não pode derrubar nada."""
    from app.db.models.documento_fiscal import DocumentoFiscal
    from app.services.fiscal.emissao import _completar_tributos_pelo_xml

    doc = DocumentoFiscal(
        id=1, tipo_documento="NFCE", origem_tipo="VENDA",
        status="AUTORIZADA", url_xml="/x.xml",
    )

    _completar_tributos_pelo_xml(doc, object())

    assert doc.valor_tributos is None


class _ClientQueExplode:
    def baixar_xml(self, caminho):
        raise RuntimeError("rede caiu")


# =========================
# 8. Resumo por tipo de documento
# =========================

def test_resumo_por_tipo_nao_mistura_modelos():
    """
    A tela da NFC-e mostra os contadores dela. Sem o filtro, o lojista leria
    '3 rejeitadas' achando que são cupons quando são NF-e de outro modelo.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.db.base import Base
    from app.db.models.documento_fiscal import DocumentoFiscal
    from app.services.documento_fiscal import obter_resumo

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    def doc(tipo, status):
        return DocumentoFiscal(
            tipo_documento=tipo, origem_tipo="VENDA", status=status,
        )

    db.add_all([
        doc("NFCE", "AUTORIZADA"), doc("NFCE", "AUTORIZADA"),
        doc("NFCE", "REJEITADA"),
        doc("NFE", "AUTORIZADA"), doc("NFE", "REJEITADA"), doc("NFE", "CANCELADA"),
    ])
    db.commit()

    nfce = obter_resumo(db, tipo="NFCE")
    assert (nfce.autorizadas, nfce.rejeitadas, nfce.canceladas) == (2, 1, 0)

    nfe = obter_resumo(db, tipo="NFE")
    assert (nfe.autorizadas, nfe.rejeitadas, nfe.canceladas) == (1, 1, 1)

    # Sem tipo continua somando tudo — é o que a visão geral do Centro usa.
    geral = obter_resumo(db)
    assert (geral.autorizadas, geral.rejeitadas, geral.canceladas) == (3, 2, 1)

    db.close()
