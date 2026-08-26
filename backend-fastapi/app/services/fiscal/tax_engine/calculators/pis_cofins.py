# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/tax_engine/calculators/pis_cofins.py
# DESCRIÇÃO: Calculador de PIS e COFINS.
#            Suporta exclusão do ICMS da base de cálculo (STF Tema 69).
# ---------------------------------------------------------------------------

from dataclasses import dataclass
from decimal import Decimal

from ..constants import (
    PRECISAO,
    ROUND_MODE,
    CST_PIS_COFINS_TRIBUTADO,
    CST_PIS_COFINS_ISENTO,
)


ZERO = Decimal("0")
CEM = Decimal("100")


@dataclass
class ResultadoPISCOFINS:
    """Resultado intermediário do cálculo de PIS e COFINS para um item."""
    pis_base: Decimal
    pis_aliquota: Decimal
    pis_valor: Decimal
    pis_cst: str

    cofins_base: Decimal
    cofins_aliquota: Decimal
    cofins_valor: Decimal
    cofins_cst: str


def calcular_pis_cofins(
    valor_bruto: Decimal,
    valor_frete: Decimal,
    valor_seguro: Decimal,
    valor_outras_despesas: Decimal,
    valor_desconto: Decimal,
    aliquota_pis: Decimal,
    aliquota_cofins: Decimal,
    cst_pis: str,
    cst_cofins: str,
    icms_valor: Decimal,
    excluir_icms_base: bool,
) -> ResultadoPISCOFINS:
    """
    Calcula PIS e COFINS de um item.

    Base = valor_bruto + frete + seguro + despesas - desconto
    Se excluir_icms_base=True (STF Tema 69): base -= icms_valor

    Args:
        valor_bruto: Valor bruto do item (reais).
        valor_frete: Frete rateado para este item.
        valor_seguro: Seguro rateado para este item.
        valor_outras_despesas: Outras despesas rateadas.
        valor_desconto: Desconto total (item + rateio nota).
        aliquota_pis: Alíquota PIS (percentual, ex: 1.65).
        aliquota_cofins: Alíquota COFINS (percentual, ex: 7.60).
        cst_pis: Situação tributária PIS.
        cst_cofins: Situação tributária COFINS.
        icms_valor: Valor do ICMS calculado (para exclusão da base).
        excluir_icms_base: Se True, exclui ICMS da base PIS/COFINS.

    Returns:
        ResultadoPISCOFINS com bases, alíquotas e valores calculados.
    """
    base_bruta = (
        valor_bruto + valor_frete + valor_seguro + valor_outras_despesas - valor_desconto
    ).quantize(PRECISAO, ROUND_MODE)

    # Exclusão do ICMS da base (STF Tema 69)
    if excluir_icms_base and icms_valor > ZERO:
        base_bruta = (base_bruta - icms_valor).quantize(PRECISAO, ROUND_MODE)
        if base_bruta < ZERO:
            base_bruta = ZERO

    # --- PIS ---
    if cst_pis in CST_PIS_COFINS_TRIBUTADO:
        pis_base = base_bruta
        pis_aliquota = aliquota_pis
        pis_valor = (pis_base * pis_aliquota / CEM).quantize(PRECISAO, ROUND_MODE)
    elif cst_pis in CST_PIS_COFINS_ISENTO:
        pis_base = ZERO
        pis_aliquota = ZERO
        pis_valor = ZERO
    else:
        # CST não reconhecido → zera (não lança erro, mantém campo preenchido)
        pis_base = ZERO
        pis_aliquota = ZERO
        pis_valor = ZERO

    # --- COFINS ---
    if cst_cofins in CST_PIS_COFINS_TRIBUTADO:
        cofins_base = base_bruta
        cofins_aliquota = aliquota_cofins
        cofins_valor = (cofins_base * cofins_aliquota / CEM).quantize(PRECISAO, ROUND_MODE)
    elif cst_cofins in CST_PIS_COFINS_ISENTO:
        cofins_base = ZERO
        cofins_aliquota = ZERO
        cofins_valor = ZERO
    else:
        cofins_base = ZERO
        cofins_aliquota = ZERO
        cofins_valor = ZERO

    return ResultadoPISCOFINS(
        pis_base=pis_base,
        pis_aliquota=pis_aliquota,
        pis_valor=pis_valor,
        pis_cst=cst_pis,
        cofins_base=cofins_base,
        cofins_aliquota=cofins_aliquota,
        cofins_valor=cofins_valor,
        cofins_cst=cst_cofins,
    )
