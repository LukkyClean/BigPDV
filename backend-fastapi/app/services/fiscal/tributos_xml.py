# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/tributos_xml.py
# DESCRIÇÃO: Extrai do XML autorizado o valor aproximado dos tributos.
#
# POR QUE ISTO EXISTE
# ===========================================================================
# O DANFE NFC-e é obrigado a imprimir o "valor aproximado dos tributos"
# (Lei 12.741/2012 — a Lei da Transparência). Esse valor é o `vTotTrib`.
#
# A Focus NFe CALCULA o vTotTrib sozinha, pela tabela IBPT e o NCM de cada
# item — e faz isso justamente no caso da NFC-e, porque o cálculo automático
# dela só é dispensado quando `consumidor_final = 0` ou a natureza da operação
# contém REMESSA/EXPORTACAO/DEVOLUCAO/LANCAMENTO. Nenhum dos dois acontece num
# cupom de balcão.
#
# O problema é que ela grava o valor no XML e NÃO o devolve no JSON da
# emissão. Como não queremos manter tabela IBPT própria (que precisaria de
# atualização trimestral), lemos de volta do XML que ela mesma produziu.
# ---------------------------------------------------------------------------

import logging
from typing import Optional
from xml.etree import ElementTree

logger = logging.getLogger(__name__)


def _nome_local(tag: str) -> str:
    """Tira o namespace: '{http://...}vTotTrib' -> 'vTotTrib'.

    O XML da NF-e vem namespaced (`http://www.portalfiscal.inf.br/nfe`).
    Comparar pelo nome local evita depender do prefixo declarado, que muda
    entre emissores.
    """
    return tag.rsplit("}", 1)[-1]


def extrair_valor_tributos(xml: Optional[str]) -> Optional[int]:
    """Valor total aproximado dos tributos, em CENTAVOS. None se não achar.

    ATENÇÃO — o `vTotTrib` aparece em DOIS lugares no XML:

      * uma vez por item, dentro de `<det><imposto>`;
      * uma vez no total, dentro de `<total><ICMSTot>`.

    Queremos o do TOTAL. Pegar o primeiro que aparecer traria o tributo de um
    item só, e o cupom sairia com um valor menor que o correto — pior que não
    imprimir, porque parece certo.

    Se o grupo do total não existir, somamos os dos itens: é o mesmo número
    pela definição do campo, e cobre o XML que venha sem o ICMSTot.
    """
    if not xml:
        return None

    try:
        raiz = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        logger.warning("[FISCAL] XML da nota não pôde ser lido: %s", exc)
        return None

    # 1) O caminho certo: o vTotTrib de dentro do ICMSTot.
    for elemento in raiz.iter():
        if _nome_local(elemento.tag) != "ICMSTot":
            continue
        for filho in elemento:
            if _nome_local(filho.tag) == "vTotTrib":
                return _para_centavos(filho.text)

    # 2) Sem ICMSTot: soma o dos itens.
    total = 0
    achou = False
    for elemento in raiz.iter():
        if _nome_local(elemento.tag) != "vTotTrib":
            continue
        centavos = _para_centavos(elemento.text)
        if centavos is not None:
            total += centavos
            achou = True

    if achou:
        logger.info(
            "[FISCAL] XML sem grupo ICMSTot; vTotTrib somado a partir dos itens."
        )
        return total

    logger.info("[FISCAL] XML da nota não traz vTotTrib.")
    return None


def _para_centavos(texto: Optional[str]) -> Optional[int]:
    """'12.34' -> 1234. O XML da SEFAZ usa ponto decimal, nunca vírgula."""
    if texto is None:
        return None
    try:
        return int(round(float(texto.strip()) * 100))
    except (TypeError, ValueError):
        return None
