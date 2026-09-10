# ---------------------------------------------------------------------------
# ARQUIVO: test/services/fiscal/test_tres_desfechos.py
# DESCRIÇÃO: Três desfechos que viravam um só — e por isso uma lista de
#            "rejeitadas" não dizia quais notas chegaram na SEFAZ.
#
#   nunca transmitida (404 na consulta)      -> status INTOCADO + mensagem
#   recusada antes da SEFAZ (4xx na emissão) -> NAO_TRANSMITIDA
#   rejeitada PELA SEFAZ                     -> REJEITADA, com o código
#
# O caminho que criou o problema: a reemissão cria uma linha PENDENTE com
# `ref_api` nova e NÃO transmite. Algo consultava essa linha, a emissora dizia
# 404, o 404 virava "erro", e "erro" virava REJEITADA.
# ---------------------------------------------------------------------------

import pytest

from app.db.models.documento_fiscal import DocumentoFiscal
from app.services.fiscal.emissao import (
    STATUS_CONSULTAVEIS,
    STATUS_NAO_TRANSMITIDA,
    _aplicar_resultado,
)
from app.services.fiscal.http.client import (
    CODIGO_NOTA_INEXISTENTE,
    RESULTADO_NAO_ENCONTRADO,
)


def _doc(status: str, **campos) -> DocumentoFiscal:
    doc = DocumentoFiscal(
        tipo_documento="NFE", origem_tipo="VENDA", origem_id=1, status=status,
    )
    for k, v in campos.items():
        setattr(doc, k, v)
    return doc


# ---------------------------------------------------------------------------
# 1. 404 na consulta — o desfecho que virava "erro desconhecido"
# ---------------------------------------------------------------------------

def test_404_nao_marca_rejeitada():
    """O 404 dizia 'erro', e 'erro' virava REJEITADA.

    REJEITADA é o status que AUTORIZA reemissão. Uma nota que nunca saiu do
    prédio virava candidata a ser 'reemitida' — e uma que saiu, também.
    """
    doc = _doc("INDETERMINADA")

    _aplicar_resultado(
        doc,
        {"status": RESULTADO_NAO_ENCONTRADO, "mensagem_sefaz": "nao consta"},
    )

    assert doc.status == "INDETERMINADA"
    assert doc.mensagem_sefaz == "nao consta"


def test_so_o_codigo_da_emissora_conclui_que_a_nota_nao_saiu():
    """O único 404 que afirma algo sobre a NOTA."""
    doc = _doc("INDETERMINADA")

    _aplicar_resultado(doc, {
        "status": RESULTADO_NAO_ENCONTRADO,
        "codigo": CODIGO_NOTA_INEXISTENTE,
        "mensagem_sefaz": "nao consta na emissora",
    })

    assert doc.status == STATUS_NAO_TRANSMITIDA


@pytest.mark.parametrize("codigo", [
    "LICENCA_NAO_ENCONTRADA",
    "SEM_CONFIGURACAO_FISCAL",
    None,  # plataforma antiga, que ainda não manda código
])
def test_pre_voo_da_plataforma_nao_decide_nada_sobre_a_nota(codigo):
    """Estes 404 são da PLATAFORMA, não da emissora.

    A plataforma responde 404 tanto para "a nota não está na emissora" quanto
    para os pré-voos dela. Ler os dois igual é o que produz nota duplicada: uma
    INDETERMINADA que na verdade está autorizada na SEFAZ deixaria de trancar a
    venda, e a próxima emissão sairia por cima.

    `None` está na lista de propósito — durante a janela de atualização a loja
    fala com uma plataforma que ainda não manda código, e o padrão seguro é não
    concluir nada.
    """
    doc = _doc("INDETERMINADA")

    _aplicar_resultado(doc, {
        "status": RESULTADO_NAO_ENCONTRADO,
        "codigo": codigo,
        "mensagem_sefaz": "licenca nao encontrada",
    })

    assert doc.status == "INDETERMINADA"


def test_404_nao_apaga_o_que_o_documento_ja_tinha():
    """O 404 não pode levar junto a chave e o protocolo.

    `_aplicar_resultado` sobrescreve esses campos com o que veio na resposta —
    e numa resposta de 404 não vem nada. Um documento que já tinha chave de
    acesso a perderia por causa de uma consulta que falhou.
    """
    doc = _doc("INDETERMINADA", chave_acesso="35250912345678000199550010000000011000000017",
               protocolo_autorizacao="135250000012345")

    _aplicar_resultado(doc, {"status": RESULTADO_NAO_ENCONTRADO, "mensagem_sefaz": "nao consta"})

    assert doc.chave_acesso is not None
    assert doc.protocolo_autorizacao == "135250000012345"


# ---------------------------------------------------------------------------
# 2. Recusa antes da SEFAZ
# ---------------------------------------------------------------------------

def test_recusa_antes_da_sefaz_nao_e_rejeicao():
    doc = _doc("PROCESSANDO")

    _aplicar_resultado(doc, {
        "status": "nao_transmitido",
        "mensagem_sefaz": "payload invalido",
    })

    assert doc.status == STATUS_NAO_TRANSMITIDA
    assert doc.status != "REJEITADA"


# ---------------------------------------------------------------------------
# 3. Rejeição de verdade — com o número, que é o que não engana
# ---------------------------------------------------------------------------

def test_rejeicao_da_sefaz_guarda_o_codigo():
    """O texto da SEFAZ já chegou dizendo 'destinatário' e citando o CNPJ do
    emitente. O número é o que resolve."""
    doc = _doc("PROCESSANDO")

    _aplicar_resultado(doc, {
        "status": "erro",
        "status_focus": "erro_autorizacao",
        "codigo_sefaz": 539,
        "mensagem_sefaz": "Rejeicao: Duplicidade de NF-e",
    })

    assert doc.status == "REJEITADA"
    assert doc.codigo_status_sefaz == 539
    assert doc.status_focus == "erro_autorizacao"


def test_denegada_nao_cai_no_balde_de_rejeitada():
    """Denegada é decisão da SEFAZ sobre o CONTRIBUINTE: reenviar não adianta.

    Caía em REJEITADA, que é reemitível — o sistema convidava o lojista a
    repetir para sempre uma operação que nunca vai passar.
    """
    doc = _doc("PROCESSANDO")

    _aplicar_resultado(doc, {
        "status": "erro",
        "status_focus": "denegado",
        "codigo_sefaz": 302,
        "mensagem_sefaz": "Rejeicao: Uso Denegado",
    })

    assert doc.status == "DENEGADA"
    assert doc.codigo_status_sefaz == 302


# ---------------------------------------------------------------------------
# 4. Quem pode ser consultado
# ---------------------------------------------------------------------------

def test_pendente_nao_e_consultavel():
    """PENDENTE só nasce da reemissão, que não transmite. Consultar dava 404
    eterno — e era esse 404 que virava REJEITADA."""
    assert "PENDENTE" not in STATUS_CONSULTAVEIS
    assert STATUS_NAO_TRANSMITIDA not in STATUS_CONSULTAVEIS


def test_transmitidos_continuam_consultaveis():
    """A correção não pode calar o polling do que de fato foi transmitido:
    INDETERMINADA depende dele para ser reconciliada."""
    assert "PROCESSANDO" in STATUS_CONSULTAVEIS
    assert "INDETERMINADA" in STATUS_CONSULTAVEIS


# ---------------------------------------------------------------------------
# 5. O fantasma não pode trancar a venda
# ---------------------------------------------------------------------------

def test_status_nao_transmitido_nao_tranca_nova_emissao():
    """PENDENTE contava como documento VIVO. Cada reemissão trancava a venda em
    'já possui uma emissão em andamento' — por uma nota que nunca existiu."""
    from app.db.crud.fiscal import STATUS_DOCUMENTO_VIVO

    assert "PENDENTE" not in STATUS_DOCUMENTO_VIVO
    assert STATUS_NAO_TRANSMITIDA not in STATUS_DOCUMENTO_VIVO
    # INDETERMINADA CONTINUA trancando: pode estar autorizada na SEFAZ.
    assert "INDETERMINADA" in STATUS_DOCUMENTO_VIVO
