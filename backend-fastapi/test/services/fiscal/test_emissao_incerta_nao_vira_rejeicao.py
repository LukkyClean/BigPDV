"""
Falha de comunicação na emissão NÃO pode virar rejeição.

O CENÁRIO QUE ISTO IMPEDE, na ordem em que acontece:

  1. A SEFAZ demora mais que o timeout de 30 s (acontece, sobretudo em
     horário de pico).
  2. O client devolvia {"status": "erro"} para QUALQUER exceção -- inclusive
     timeout -- e `_aplicar_resultado` mapeia "erro" para REJEITADA.
  3. REJEITADA é um estado REEMITÍVEL.
  4. O operador reemite. A reemissão monta uma ref NOVA
     (`venda-123-retry-45`, ver `reemitir_documento`).
  5. A idempotência da plataforma é POR REF -- ela consulta a ref na Focus
     antes de emitir. Ref nova = não encontra nada = emite de novo.
  6. Resultado: DUAS notas autorizadas para a mesma venda, no mesmo CNPJ.

A proteção contra isso já existia em `emissao.py` (status INDETERMINADA,
que NÃO é reemitível), mas era código morto: o client capturava a exceção
antes e ela nunca subia até lá.

Estes testes existem para que a captura larga não volte.
"""

import httpx
import pytest

from app.db.models.documento_fiscal import DocumentoFiscal
from app.services.fiscal.emissao import STATUS_NAO_TRANSMITIDA, _aplicar_resultado
from app.services.fiscal.http.client_startbig import (
    EmissaoIncertaError,
    FiscalClientStartBig,
)

PAYLOAD = {"emitente": {"cnpj": "12345678000199"}, "items": []}


def _client():
    return FiscalClientStartBig(ambiente=2, token="token-de-teste")


# --- Sem resposta: INCERTO, tem que levantar --------------------------------

@pytest.mark.parametrize(
    "falha",
    [
        httpx.TimeoutException("tempo esgotado"),
        httpx.ConnectError("sem rota para o host"),
        httpx.ReadError("conexão caiu no meio"),
    ],
    ids=["timeout", "sem_conexao", "conexao_caiu"],
)
def test_falha_de_rede_levanta_em_vez_de_dizer_rejeitada(monkeypatch, falha):
    """Nenhuma delas pode virar um resultado 'erro' silencioso."""

    def _explode(*_a, **_k):
        raise falha

    monkeypatch.setattr(httpx.Client, "post", _explode)

    with pytest.raises(EmissaoIncertaError):
        _client().emitir_nfe("venda-1", PAYLOAD)


def test_nfce_tambem_levanta(monkeypatch):
    """NFC-e consome numeração igual à NF-e; a mesma regra vale."""

    def _explode(*_a, **_k):
        raise httpx.TimeoutException("tempo esgotado")

    monkeypatch.setattr(httpx.Client, "post", _explode)

    with pytest.raises(EmissaoIncertaError):
        _client().emitir_nfce("nfce-1", PAYLOAD)


def test_erro_5xx_e_incerto(monkeypatch):
    """500 pode ter processado antes de falhar -- não dá para afirmar recusa."""

    def _resposta_500(*_a, **_k):
        return httpx.Response(
            500, json={"message": "boom"}, request=httpx.Request("POST", "http://x")
        )

    monkeypatch.setattr(httpx.Client, "post", _resposta_500)

    with pytest.raises(EmissaoIncertaError):
        _client().emitir_nfe("venda-1", PAYLOAD)


# --- Com resposta: a API falou, e falou NÃO ---------------------------------

def test_4xx_e_recusa_e_nao_incerteza(monkeypatch):
    """4xx é recusa ANTES de transmitir: CNPJ divergente, sem config, rota
    inexistente. Nada foi para a SEFAZ, então NÃO é incerteza -- e o texto
    precisa dizer isso, senão o lojista vai procurar o erro na SEFAZ.

    O status era `erro`, e `erro` vira REJEITADA em `_aplicar_resultado`. A
    intenção deste teste sempre foi "nada chegou na SEFAZ" — mas o valor que ele
    conferia dizia o contrário na tela: a nota aparecia na lista de rejeitadas,
    ao lado das que de fato foram recusadas lá, e ninguém conseguia separar as
    duas. `nao_transmitido` é a mesma intenção, agora dita por inteiro.
    """

    def _resposta_404(*_a, **_k):
        return httpx.Response(
            404, text="Not Found", request=httpx.Request("POST", "http://x")
        )

    monkeypatch.setattr(httpx.Client, "post", _resposta_404)

    # Metade da invariante: com resposta, NUNCA é incerteza. Se um dia isto
    # virar EmissaoIncertaError, o documento fica INDETERMINADA e tranca a
    # venda por uma nota que nem saiu.
    resultado = _client().emitir_nfe("venda-1", PAYLOAD)

    # A outra metade, afirmada pela CONSEQUÊNCIA e não pelo valor da string.
    #
    # A versão anterior conferia o literal `"erro"` embaixo de uma docstring que
    # dizia "nada foi para a SEFAZ": documentava a intenção e travava a
    # codificação. O que precisa valer é o que acontece com o DOCUMENTO — e é
    # isso que a renomeação seguinte não pode quebrar sem quebrar a regra junto.
    doc = DocumentoFiscal(tipo_documento="NFE", origem_tipo="VENDA", status="PROCESSANDO")
    _aplicar_resultado(doc, resultado)

    assert doc.status == STATUS_NAO_TRANSMITIDA
    assert doc.status != "REJEITADA"          # não foi a SEFAZ que recusou
    assert doc.codigo_status_sefaz is None    # e por isso não existe código
    assert "antes de enviar" in doc.mensagem_sefaz


def test_resposta_boa_continua_passando(monkeypatch):
    """A correção não pode ter quebrado o caminho feliz."""

    def _resposta_ok(*_a, **_k):
        return httpx.Response(
            200,
            json={
                "status": "autorizado",
                "chave_acesso": "3524" + "0" * 40,
                "protocolo": "135240000000001",
                "numero": 7,
                "serie": 1,
            },
            request=httpx.Request("POST", "http://x"),
        )

    monkeypatch.setattr(httpx.Client, "post", _resposta_ok)

    resultado = _client().emitir_nfe("venda-1", PAYLOAD)

    assert resultado["status"] == "autorizado"
    assert resultado["numero"] == 7
