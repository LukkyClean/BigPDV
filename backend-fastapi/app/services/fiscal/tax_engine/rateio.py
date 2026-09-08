# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/tax_engine/rateio.py
# DESCRIÇÃO: Rateio proporcional de valores globais da nota entre itens.
#            Distribui frete, seguro, outras despesas e desconto da nota
#            proporcionalmente ao valor bruto de cada item.
# ---------------------------------------------------------------------------

from decimal import Decimal

from .constants import PRECISAO, ROUND_MODE
from .exceptions import RateioError
from .types import ItemEntrada


def ratear_valor(valor_total: Decimal, itens: list[ItemEntrada]) -> list[Decimal]:
    """
    Distribui valor_total proporcionalmente entre itens pelo peso de valor_bruto.

    Ajusta diferença de centavos no item de maior valor_bruto para garantir
    que a soma dos rateados == valor_total (exigência SEFAZ).

    Retorna lista de Decimals na mesma ordem dos itens.
    """
    if not itens:
        raise RateioError("Não há itens para rateio.", campo="itens")

    if valor_total == Decimal("0"):
        return [Decimal("0")] * len(itens)

    total_bruto = sum(item.valor_bruto for item in itens)

    if total_bruto <= Decimal("0"):
        raise RateioError(
            "Valor bruto total dos itens é zero ou negativo — impossível ratear.",
            campo="valor_bruto",
        )

    rateados: list[Decimal] = []
    for item in itens:
        peso = item.valor_bruto / total_bruto
        parcela = (valor_total * peso).quantize(PRECISAO, rounding=ROUND_MODE)
        rateados.append(parcela)

    # Ajustar diferença de centavos no item de maior valor_bruto
    diferenca = valor_total - sum(rateados)
    if diferenca != Decimal("0"):
        idx_maior = max(range(len(itens)), key=lambda i: itens[i].valor_bruto)
        rateados[idx_maior] += diferenca

    return rateados


def aplicar_rateio(
    itens: list[ItemEntrada],
    frete: Decimal,
    seguro: Decimal,
    outras_despesas: Decimal,
    desconto_nota: Decimal,
) -> list[dict]:
    """
    Aplica rateio proporcional de todos os valores globais da nota.

    Valida que desconto_nota não exceda o total dos produtos.

    Retorna lista de dicts com:
        valor_frete, valor_seguro, valor_outras_despesas, valor_desconto_nota
    """
    total_bruto = sum(item.valor_bruto for item in itens)

    if desconto_nota > Decimal("0") and desconto_nota >= total_bruto:
        raise RateioError(
            f"Desconto da nota (R$ {desconto_nota}) é maior ou igual ao valor "
            f"total dos produtos (R$ {total_bruto}) — base ficaria negativa.",
            campo="desconto_nota",
        )

    frete_rateado = ratear_valor(frete, itens)
    seguro_rateado = ratear_valor(seguro, itens)
    despesas_rateado = ratear_valor(outras_despesas, itens)
    desconto_rateado = ratear_valor(desconto_nota, itens)

    resultado: list[dict] = []
    for i in range(len(itens)):
        resultado.append({
            "valor_frete": frete_rateado[i],
            "valor_seguro": seguro_rateado[i],
            "valor_outras_despesas": despesas_rateado[i],
            "valor_desconto_nota": desconto_rateado[i],
        })

    return resultado
