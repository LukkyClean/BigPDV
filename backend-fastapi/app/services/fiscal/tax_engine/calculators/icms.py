# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/tax_engine/calculators/icms.py
# DESCRIÇÃO: Calculador de ICMS por CST (Regime Normal) e CSOSN (Simples Nacional).
#
# CSTs suportados:  00, 20, 40, 41, 60
# CSOSNs suportados: 101, 102, 500
# ---------------------------------------------------------------------------

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from ..constants import (
    PRECISAO,
    ROUND_MODE,
    CST_ICMS_TRIBUTADO,
    CST_ICMS_REDUZIDA,
    CST_ICMS_ISENTO,
    CST_ICMS_ST,
    CSOSN_COM_CREDITO,
    CSOSN_SEM_CREDITO,
    CSOSN_ST,
)
from ..exceptions import CSTNaoSuportadoError
from ..types import ItemEntrada


ZERO = Decimal("0")
CEM = Decimal("100")


@dataclass
class ResultadoICMS:
    """Resultado intermediário do cálculo de ICMS para um item."""
    base_calculo: Decimal
    aliquota: Decimal
    valor: Decimal
    situacao_tributaria: str
    origem: int
    reducao_base: Optional[Decimal] = None
    codigo_beneficio_fiscal: Optional[str] = None
    # CSOSN 101 — crédito do Simples Nacional
    aliquota_credito_simples: Optional[Decimal] = None
    valor_credito_simples: Optional[Decimal] = None


def _base_calculo_padrao(
    item: ItemEntrada,
    valor_frete: Decimal,
    valor_seguro: Decimal,
    valor_outras_despesas: Decimal,
    valor_desconto: Decimal,
) -> Decimal:
    """Base de cálculo padrão: produto + frete + seguro + despesas - desconto."""
    return (
        item.valor_bruto + valor_frete + valor_seguro + valor_outras_despesas - valor_desconto
    ).quantize(PRECISAO, ROUND_MODE)


def calcular_icms(
    item: ItemEntrada,
    valor_frete: Decimal,
    valor_seguro: Decimal,
    valor_outras_despesas: Decimal,
    valor_desconto: Decimal,
    simples_nacional: bool,
) -> ResultadoICMS:
    """
    Calcula ICMS de um item conforme seu CST ou CSOSN.

    Args:
        item: Dados do item com alíquotas já resolvidas.
        valor_frete: Frete rateado para este item.
        valor_seguro: Seguro rateado para este item.
        valor_outras_despesas: Outras despesas rateadas.
        valor_desconto: Desconto total (item + rateio nota).
        simples_nacional: Se a empresa é do Simples Nacional.

    Returns:
        ResultadoICMS com base, alíquota e valor calculados.

    Raises:
        CSTNaoSuportadoError: se CST/CSOSN não está implementado.
    """
    if simples_nacional:
        return _calcular_csosn(item, valor_frete, valor_seguro,
                               valor_outras_despesas, valor_desconto)
    return _calcular_cst(item, valor_frete, valor_seguro,
                         valor_outras_despesas, valor_desconto)


def _calcular_cst(
    item: ItemEntrada,
    vf: Decimal, vs: Decimal, vod: Decimal, vd: Decimal,
) -> ResultadoICMS:
    """Calcula ICMS para regime normal por CST."""
    cst = item.cst_icms
    if not cst:
        raise CSTNaoSuportadoError(
            "CST ICMS não definido para o produto.",
            campo="cst_icms", item=item.numero_item,
        )

    base = _base_calculo_padrao(item, vf, vs, vod, vd)

    # CST 00 — Tributada integralmente
    if cst in CST_ICMS_TRIBUTADO:
        valor = (base * item.aliquota_icms / CEM).quantize(PRECISAO, ROUND_MODE)
        return ResultadoICMS(
            base_calculo=base,
            aliquota=item.aliquota_icms,
            valor=valor,
            situacao_tributaria=cst,
            origem=item.origem_mercadoria,
        )

    # CST 20 — Com redução de base de cálculo
    if cst in CST_ICMS_REDUZIDA:
        fator_reducao = (CEM - item.reducao_base_icms) / CEM
        base_reduzida = (base * fator_reducao).quantize(PRECISAO, ROUND_MODE)
        valor = (base_reduzida * item.aliquota_icms / CEM).quantize(PRECISAO, ROUND_MODE)
        return ResultadoICMS(
            base_calculo=base_reduzida,
            aliquota=item.aliquota_icms,
            valor=valor,
            situacao_tributaria=cst,
            origem=item.origem_mercadoria,
            reducao_base=item.reducao_base_icms,
            codigo_beneficio_fiscal=item.codigo_beneficio_fiscal,
        )

    # CST 40/41 — Isenta / Não tributada
    if cst in CST_ICMS_ISENTO:
        return ResultadoICMS(
            base_calculo=ZERO,
            aliquota=ZERO,
            valor=ZERO,
            situacao_tributaria=cst,
            origem=item.origem_mercadoria,
        )

    # CST 60 — ICMS cobrado anteriormente por Substituição Tributária
    if cst in CST_ICMS_ST:
        return ResultadoICMS(
            base_calculo=ZERO,
            aliquota=ZERO,
            valor=ZERO,
            situacao_tributaria=cst,
            origem=item.origem_mercadoria,
        )

    raise CSTNaoSuportadoError(
        f"CST ICMS '{cst}' não é suportado nesta versão do motor fiscal. "
        f"CSTs suportados: 00, 20, 40, 41, 60.",
        campo="cst_icms",
        item=item.numero_item,
    )


def _calcular_csosn(
    item: ItemEntrada,
    vf: Decimal, vs: Decimal, vod: Decimal, vd: Decimal,
) -> ResultadoICMS:
    """Calcula ICMS para Simples Nacional por CSOSN."""
    csosn = item.csosn
    if not csosn:
        raise CSTNaoSuportadoError(
            "CSOSN não definido para o produto.",
            campo="csosn", item=item.numero_item,
        )

    base = _base_calculo_padrao(item, vf, vs, vod, vd)

    # CSOSN 101 — Tributada com permissão de crédito
    if csosn in CSOSN_COM_CREDITO:
        valor_credito = (base * item.aliquota_icms / CEM).quantize(PRECISAO, ROUND_MODE)
        return ResultadoICMS(
            base_calculo=base,
            aliquota=ZERO,
            valor=ZERO,
            situacao_tributaria=csosn,
            origem=item.origem_mercadoria,
            aliquota_credito_simples=item.aliquota_icms,
            valor_credito_simples=valor_credito,
        )

    # CSOSN 102 — Tributada sem permissão de crédito
    if csosn in CSOSN_SEM_CREDITO:
        return ResultadoICMS(
            base_calculo=ZERO,
            aliquota=ZERO,
            valor=ZERO,
            situacao_tributaria=csosn,
            origem=item.origem_mercadoria,
        )

    # CSOSN 500 — ICMS cobrado anteriormente por ST
    if csosn in CSOSN_ST:
        return ResultadoICMS(
            base_calculo=ZERO,
            aliquota=ZERO,
            valor=ZERO,
            situacao_tributaria=csosn,
            origem=item.origem_mercadoria,
        )

    raise CSTNaoSuportadoError(
        f"CSOSN '{csosn}' não é suportado nesta versão do motor fiscal. "
        f"CSOSNs suportados: 101, 102, 500.",
        campo="csosn",
        item=item.numero_item,
    )
