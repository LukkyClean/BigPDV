# ---------------------------------------------------------------------------
# ARQUIVO: test/api/v1/test_emissao_ponta_a_ponta.py
# DESCRIÇÃO: A costura inteira da NF-e de venda, com a plataforma falsa.
#
# Até 11/09/2026 nenhum teste percorria o caminho completo
#   gate → reserva de número → payload → client → _aplicar_resultado
# de uma venda REAL: a reserva e o `_aplicar_resultado` tinham testes
# separados, e a costura só tinha sido provada em homologação -- onde cada
# rodada achou um campo novo. Este arquivo é a primeira prova em casa.
#
# A reemissão vive aqui porque ela É essa costura de novo: `reemissao.py`
# valida o que só ela sabe e despacha para o mesmo `emitir_nfe_venda`.
# ---------------------------------------------------------------------------
import pytest
from fastapi.testclient import TestClient

from app.db.models.contador_venda import ContadorVenda
from app.db.models.documento_fiscal import DocumentoFiscal
from app.db.models.empresa import Empresa
from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings
from app.db.models.forma_pagamento import FormaPagamento
from app.db.models.produto_fiscal import ProdutoFiscal

from test_venda_correcao_fiscal import (  # noqa: F401 -- fixtures reutilizadas
    _cliente,
    _forma_pagamento,
    _funcionario,
    _licenca_com_nfe,
    _produto,
    header_with_token,
)

CNPJ_VALIDO = "11222333000181"


# =========================
# A plataforma falsa
# =========================

class PlataformaFalsa:
    """Responde o que o teste mandar e guarda o que recebeu."""

    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def emitir_nfe(self, ref, payload, idempotency_key=None):
        self.chamadas.append({"ref": ref, "payload": payload, "idempotency_key": idempotency_key})
        return self.respostas.pop(0)

    # A NFC-e não é exercitada aqui, mas o factory exige a interface inteira.
    def emitir_nfce(self, *a, **k):
        raise AssertionError("NFC-e não deveria ser chamada neste teste")

    def consultar_config(self):
        return {"configurado": True, "cscConfigurado": True}


def AUTORIZADA(numero):
    return {
        "status": "autorizado",
        "chave_acesso": f"3526091122233300018155001000000{numero:03d}1000000015",
        "protocolo": f"135260000{numero:06d}",
        "numero": numero,
        "serie": 1,
        "url_pdf": f"https://plataforma/danfe/{numero}.pdf",
        "url_xml": f"https://plataforma/xml/{numero}.xml",
        "codigo_sefaz": 100,
        "mensagem_sefaz": "Autorizado o uso da NF-e",
    }


REJEITADA_539 = {
    "status": "erro",
    "codigo_sefaz": 539,
    "mensagem_sefaz": "Rejeição 539: Duplicidade de NF-e com diferença na chave de acesso",
}


@pytest.fixture
def plataforma(monkeypatch):
    """Instala a plataforma falsa onde `emissao.py` a procura."""
    from app.services.fiscal import emissao as emissao_mod

    caixa = {}

    def instalar(*respostas):
        caixa["falsa"] = PlataformaFalsa(respostas)
        monkeypatch.setattr(emissao_mod, "get_fiscal_client", lambda *a, **k: caixa["falsa"])
        return caixa["falsa"]

    return instalar


# =========================
# A venda que passa no gate
# =========================

@pytest.fixture
def venda_pronta(client: TestClient, db_session, header_with_token):
    """Empresa, produto, forma de pagamento e venda FINALIZADA com tudo que o
    gate da NF-e exige. Devolve (venda_id, numero_venda)."""
    header = header_with_token

    if not db_session.query(ContadorVenda).first():
        db_session.add(ContadorVenda(id=1, proximo_numero=1))
        db_session.commit()

    # Emitente: o payload padrão de teste tem CNPJ com dígito inválido e não
    # tem IE nem configuração fiscal.
    empresa = db_session.query(Empresa).first()
    empresa.documento = CNPJ_VALIDO
    empresa.indicador_ie = "1"
    empresa.inscricao_estadual = "123456789"
    db_session.add(EmpresaFiscalSettings(
        empresa_id=empresa.id, serie_nfe=1, ultimo_numero_nfe=10, ambiente_emissao=2,
    ))
    db_session.commit()

    func_id = _funcionario(client, header)
    prod_id = _produto(client, header, codigo="E2E01", varejo=10000, quantidade=10)
    fp_id = _forma_pagamento(client, header)
    cliente_id = _cliente(client, header, nome="Destinatária Completa", doc="52998224725")

    # Produto com dados fiscais (Simples Nacional → CSOSN) e forma com código SEFAZ.
    db_session.add(ProdutoFiscal(
        produto_id=prod_id, ncm="85171231", cfop_padrao="5102",
        origem_mercadoria=0, csosn="102", unidade_tributavel="UN",
    ))
    db_session.query(FormaPagamento).filter(FormaPagamento.id == fp_id).update(
        {"codigo_sefaz": "01"}
    )
    db_session.commit()

    cv = client.post("/api/v1/vendas/", json={"funcionario_id": func_id}, headers=header)
    assert cv.status_code == 201, cv.text
    venda_id = cv.json()["id"]
    r = client.post(
        f"/api/v1/vendas/{venda_id}/itens",
        json={"tipo_produto": "CADASTRADO", "produto_id": prod_id, "quantidade": 2},
        headers=header,
    )
    assert r.status_code in (200, 201), r.text
    fin = client.post(
        f"/api/v1/vendas/{venda_id}/finalizar",
        json={
            "acrescimo": 0,
            "pagamentos": [{
                "forma_pagamento_id": fp_id, "valor": 20000, "juros_valor": 0,
                "juros_responsavel": "LOJA", "parcelado": False, "qtd_parcelas": None,
            }],
        },
        headers=header,
    )
    assert fin.status_code == 200, fin.text
    numero_venda = fin.json()["numero_venda"]

    corr = client.patch(
        f"/api/v1/vendas/{venda_id}/correcao-fiscal",
        json={
            "cliente_id": cliente_id,
            "natureza_operacao": "Venda de Mercadoria",
            "consumidor_final": True,
            "indicador_presenca": 1,
        },
        headers=header,
    )
    assert corr.status_code == 200, corr.text

    return venda_id, numero_venda


def _emitir(client, header, venda_id):
    return client.post("/api/v1/fiscal/emitir/nfe", json={"venda_id": venda_id}, headers=header)


def _reemitir(client, header, doc_id):
    return client.post(f"/api/v1/fiscal/documentos/{doc_id}/reemitir", headers=header)


def _doc(db_session, doc_id) -> DocumentoFiscal:
    db_session.expire_all()
    return db_session.get(DocumentoFiscal, doc_id)


# =========================
# 1. A emissão inteira
# =========================

def test_gate_aprova_a_venda_pronta(client, header_with_token, venda_pronta):
    """Se isto falhar, o resto do arquivo falha por cadastro, não por emissão."""
    venda_id, _ = venda_pronta
    r = client.get(f"/api/v1/vendas/{venda_id}/verificar-fiscal", headers=header_with_token)
    assert r.status_code == 200, r.text
    assert r.json()["completo"] is True, r.json()["pendencias"]


def test_nfe_de_venda_autorizada_ponta_a_ponta(client, db_session, header_with_token, venda_pronta, plataforma):
    venda_id, numero_venda = venda_pronta
    falsa = plataforma(AUTORIZADA(11))

    r = _emitir(client, header_with_token, venda_id)
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["status"] == "AUTORIZADA"

    doc = _doc(db_session, corpo["documento_id"])
    assert doc.numero_documento == 11            # reservado do contador (10 → 11)
    assert doc.ref_api == f"venda-{numero_venda}"
    assert doc.tentativa_anterior_id is None
    assert doc.protocolo_autorizacao == "135260000000011"
    assert doc.itens, "o snapshot precisa existir antes da transmissão"

    # O que saiu para a plataforma é o que a SEFAZ vai ler.
    assert len(falsa.chamadas) == 1
    chamada = falsa.chamadas[0]
    assert chamada["ref"] == doc.ref_api
    assert chamada["idempotency_key"] == doc.idempotency_key
    payload = chamada["payload"]
    assert payload["emitente"]["cnpj"] == CNPJ_VALIDO
    assert payload["destinatario"]["cpf"] == "52998224725"
    assert payload["destinatario"]["endereco"]["cidade"] == "Campinas"
    assert payload["numero"] == 11


def test_rejeicao_da_sefaz_grava_rejeitada_e_nao_devolve_o_numero(
    client, db_session, header_with_token, venda_pronta, plataforma,
):
    venda_id, _ = venda_pronta
    plataforma(REJEITADA_539)

    r = _emitir(client, header_with_token, venda_id)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "REJEITADA"

    fs = db_session.query(EmpresaFiscalSettings).first()
    db_session.refresh(fs)
    assert fs.ultimo_numero_nfe == 11, "o número não volta para o contador depois do disparo"


# =========================
# 2. A reemissão transmite
# =========================

def test_reemitir_transmite_e_encadeia(client, db_session, header_with_token, venda_pronta, plataforma):
    venda_id, numero_venda = venda_pronta
    falsa = plataforma(REJEITADA_539, AUTORIZADA(12))

    rejeitado_id = _emitir(client, header_with_token, venda_id).json()["documento_id"]

    r = _reemitir(client, header_with_token, rejeitado_id)
    assert r.status_code == 200, r.text
    novo = r.json()

    assert novo["status"] == "AUTORIZADA", "a reemissão tem que ir à plataforma, não criar linha"
    assert novo["tentativa_anterior_id"] == rejeitado_id
    assert novo["numero_documento"] == 12, "número NOVO -- o 11 pode ter sido consumido na SEFAZ"
    assert novo["ref_api"] == f"venda-{numero_venda}-2"
    assert len(falsa.chamadas) == 2
    assert falsa.chamadas[1]["idempotency_key"] != falsa.chamadas[0]["idempotency_key"]

    # O rejeitado fica como estava; o histórico mostra a cadeia inteira.
    assert _doc(db_session, rejeitado_id).status == "REJEITADA"
    hist = client.get(f"/api/v1/fiscal/documentos/{rejeitado_id}/historico", headers=header_with_token)
    assert hist.status_code == 200
    assert [t["id"] for t in hist.json()["tentativas"]] == [novo["id"], rejeitado_id]

    # Nenhum PENDENTE nasceu.
    assert db_session.query(DocumentoFiscal).filter(DocumentoFiscal.status == "PENDENTE").count() == 0


def test_reemitir_rejeitada_de_novo_continua_reemitivel(client, header_with_token, venda_pronta, plataforma):
    venda_id, _ = venda_pronta
    plataforma(REJEITADA_539, REJEITADA_539, AUTORIZADA(13))

    d1 = _emitir(client, header_with_token, venda_id).json()["documento_id"]
    d2 = _reemitir(client, header_with_token, d1).json()
    assert d2["status"] == "REJEITADA"
    d3 = _reemitir(client, header_with_token, d2["id"]).json()
    assert d3["status"] == "AUTORIZADA"
    assert d3["tentativa_anterior_id"] == d2["id"]
    assert d3["numero_documento"] == 13


def test_reemitir_o_que_nao_e_rejeitada_e_recusado(client, db_session, header_with_token, venda_pronta, plataforma):
    venda_id, _ = venda_pronta
    plataforma(AUTORIZADA(11))
    autorizado_id = _emitir(client, header_with_token, venda_id).json()["documento_id"]

    r = _reemitir(client, header_with_token, autorizado_id)
    assert r.status_code == 422, r.text
    assert "rejeitados" in r.json()["detail"]


def test_denegada_nao_e_reemitivel(client, db_session, header_with_token, venda_pronta, plataforma):
    """Denegada é sobre o contribuinte: reenviar volta denegada e queima número."""
    venda_id, _ = venda_pronta
    plataforma(REJEITADA_539)
    doc_id = _emitir(client, header_with_token, venda_id).json()["documento_id"]
    doc = _doc(db_session, doc_id)
    doc.status = "DENEGADA"
    db_session.commit()

    r = _reemitir(client, header_with_token, doc_id)
    assert r.status_code == 422, r.text
    assert "denegado" in r.json()["detail"].lower()


def test_limite_de_tentativas(client, db_session, header_with_token, venda_pronta, plataforma):
    venda_id, _ = venda_pronta
    falsa = plataforma(*([REJEITADA_539] * 5))

    doc_id = _emitir(client, header_with_token, venda_id).json()["documento_id"]
    for _ in range(4):
        r = _reemitir(client, header_with_token, doc_id)
        assert r.status_code == 200, r.text
        doc_id = r.json()["id"]
    assert len(falsa.chamadas) == 5

    r = _reemitir(client, header_with_token, doc_id)
    assert r.status_code == 422, r.text
    assert "5 vezes" in r.json()["detail"]
    assert len(falsa.chamadas) == 5, "a sexta não pode ir à plataforma"


def test_reemitir_com_cadastro_quebrado_recusa_antes_de_reservar_numero(
    client, db_session, header_with_token, venda_pronta, plataforma,
):
    """O gate roda de novo na reemissão -- é o que dá sentido a 'corrigir e reemitir'."""
    venda_id, _ = venda_pronta
    falsa = plataforma(REJEITADA_539)
    doc_id = _emitir(client, header_with_token, venda_id).json()["documento_id"]

    empresa = db_session.query(Empresa).first()
    empresa.inscricao_estadual = None
    db_session.commit()

    r = _reemitir(client, header_with_token, doc_id)
    assert r.status_code == 422, r.text
    assert len(falsa.chamadas) == 1
    fs = db_session.query(EmpresaFiscalSettings).first()
    db_session.refresh(fs)
    assert fs.ultimo_numero_nfe == 11, "recusa do gate não pode queimar número"
