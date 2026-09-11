# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/snapshot.py
# DESCRIÇÃO: Congela, na emissão, os itens que foram enviados à SEFAZ.
# ---------------------------------------------------------------------------
"""
Snapshot fiscal dos itens.

A fonte é o PAYLOAD, nunca o cadastro. É o payload que foi transmitido, e é
com ele que a nota autorizada tem que bater — ler do cadastro na hora de
exibir foi exatamente o defeito que este módulo existe para corrigir.

Módulo puro em relação a regra: recebe o dict do payload e devolve modelos.
Não decide nada tributário.
"""
import logging
from typing import Any, Optional

from app.db.models.documento_fiscal import DocumentoFiscal
from app.db.models.documento_fiscal_item import DocumentoFiscalItem

logger = logging.getLogger(__name__)


def _reais_para_centavos(valor: Any) -> int:
    """
    Converte o valor do payload (reais, float/Decimal/str) para centavos.

    Arredonda com `round()` de propósito: o payload já saiu do motor com duas
    casas, então não há decisão de arredondamento acontecendo aqui — só a
    correção do erro binário do float (2.30 virando 229 sem isso).
    """
    if valor is None:
        return 0
    try:
        return int(round(float(valor) * 100))
    except (TypeError, ValueError):
        return 0


def _para_milesimos(valor: Any) -> int:
    """Quantidade × 1000. A NF-e admite 4 casas; guardamos 3, que cobre o varejo."""
    if valor is None:
        return 0
    try:
        return int(round(float(valor) * 1000))
    except (TypeError, ValueError):
        return 0


def _texto(valor: Any, limite: int) -> Optional[str]:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto[:limite] if texto else None


def montar_itens_snapshot(payload: dict, venda=None) -> list[DocumentoFiscalItem]:
    """
    Traduz os itens do payload em linhas de snapshot.

    `venda` entra só para recuperar o `produto_id`: ele não viaja no payload
    (a SEFAZ não tem o que fazer com um id interno), mas serve para a tela de
    detalhes linkar de volta ao catálogo. O casamento é pela ORDEM, que é a
    mesma em que `_montar_itens` percorreu `venda.itens`.

    Tolerante por construção: um payload sem `items`, ou com um item torto,
    devolve o que der. Falhar aqui derrubaria uma emissão que já pode ter
    chegado à SEFAZ — o snapshot é registro, não pré-requisito da nota.
    """
    itens_payload = payload.get("items") or []
    itens_venda = list(getattr(venda, "itens", None) or [])
    snapshot: list[DocumentoFiscalItem] = []

    for idx, item in enumerate(itens_payload, start=1):
        if not isinstance(item, dict):
            continue
        numero_item = item.get("numero_item") or idx
        produto_id = None
        if 0 < numero_item <= len(itens_venda):
            produto_id = getattr(itens_venda[numero_item - 1], "produto_id", None)

        snapshot.append(
            DocumentoFiscalItem(
                numero_item=numero_item,
                produto_id=produto_id,
                descricao=_texto(item.get("descricao"), 255) or "Item",
                codigo_produto=_texto(item.get("codigo_produto"), 60),
                codigo_barras=_texto(item.get("codigo_barras_comercial"), 20),
                unidade=_texto(item.get("unidade_comercial"), 6),
                ncm=_texto(item.get("ncm"), 8),
                cfop=_texto(item.get("cfop"), 4),
                cest=_texto(item.get("cest"), 7),
                origem_mercadoria=_texto(item.get("icms_origem"), 1),
                situacao_tributaria=_texto(item.get("icms_situacao_tributaria"), 3),
                quantidade_milesimos=_para_milesimos(item.get("quantidade_comercial")),
                valor_unitario=_reais_para_centavos(item.get("valor_unitario_comercial")),
                valor_bruto=_reais_para_centavos(item.get("valor_bruto")),
                valor_desconto=_reais_para_centavos(item.get("valor_desconto")),
                base_icms=_reais_para_centavos(item.get("icms_base_calculo")),
                valor_icms=_reais_para_centavos(item.get("icms_valor")),
                aliquota_icms_centesimos=int(
                    round(float(item.get("icms_aliquota") or 0) * 100)
                ),
            )
        )

    return snapshot


def gravar_snapshot(documento: DocumentoFiscal, payload: dict, venda=None) -> None:
    """
    Anexa o snapshot ao documento. Nunca levanta.

    Chamado logo depois de criar o DocumentoFiscal e ANTES de transmitir: o que
    interessa registrar é o que saiu daqui, e registrar antes garante que exista
    snapshot mesmo se a resposta da SEFAZ se perder.
    """
    try:
        documento.itens = montar_itens_snapshot(payload, venda=venda)
        # O destinatário como FOI no payload -- e o que a SEFAZ vai citar numa
        # recusa. Congelado aqui pelo mesmo motivo dos itens.
        dest = payload.get("destinatario") or {}
        if isinstance(dest, dict):
            documento.destinatario_documento_enviado = (
                str(dest.get("cnpj") or dest.get("cpf") or "")[:14] or None
            )
            documento.destinatario_nome_enviado = (
                str(dest.get("nome") or dest.get("razao_social") or "")[:120] or None
            )
    except Exception as exc:  # pragma: no cover - rede de segurança
        # Um snapshot ausente degrada a tela de detalhes (que cai no
        # comportamento antigo); uma exceção aqui derrubaria a emissão.
        logger.error("[FISCAL] Falha ao montar snapshot dos itens: %s", exc)
