# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/tax_engine/engine.py
# DESCRIÇÃO: Orquestrador principal do motor de cálculo tributário.
#            Função pura — sem dependência de DB ou HTTP.
#
# Fluxo:
#   1. Rateio proporcional de frete/seguro/despesas/desconto
#   2. Cálculo de ICMS por item (CST ou CSOSN)
#   3. Cálculo de PIS/COFINS por item (com exclusão opcional de ICMS)
#   4. Consolidação dos totais do cabeçalho
# ---------------------------------------------------------------------------

from decimal import Decimal

from .calculators.icms import calcular_icms
from .calculators.pis_cofins import calcular_pis_cofins
from .consolidador import consolidar_totais
from .constants import (
    CST_IPI_NAO_TRIBUTADO,
    IPI_CODIGO_ENQUADRAMENTO,
    PRECISAO,
    ROUND_MODE,
)
from .rateio import aplicar_rateio
from .types import DadosNota, ImpostosItem, ItemEntrada, ResultadoCalculo


def calcular_impostos(
    itens: list[ItemEntrada],
    dados_nota: DadosNota,
) -> ResultadoCalculo:
    """
    Calcula todos os tributos para uma lista de itens de venda.

    Função pura: recebe DTOs, retorna DTOs. Sem efeitos colaterais.

    Args:
        itens: Lista de ItemEntrada com dados e alíquotas já resolvidas.
        dados_nota: Dados globais da nota (frete, seguro, flags).

    Returns:
        ResultadoCalculo com tributos por item e totais consolidados.

    Raises:
        RateioError: se dados de rateio forem inválidos.
        CSTNaoSuportadoError: se CST/CSOSN não for suportado.
    """
    # 1. Rateio proporcional
    rateios = aplicar_rateio(
        itens,
        frete=dados_nota.frete,
        seguro=dados_nota.seguro,
        outras_despesas=dados_nota.outras_despesas,
        desconto_nota=dados_nota.desconto_nota,
    )

    # 2 & 3. Cálculo por item
    itens_impostos: list[ImpostosItem] = []

    for i, item in enumerate(itens):
        r = rateios[i]

        # Desconto total = desconto do item + desconto rateado da nota
        desconto_total = (
            item.desconto_item + r["valor_desconto_nota"]
        ).quantize(PRECISAO, ROUND_MODE)

        # ICMS
        icms = calcular_icms(
            item=item,
            valor_frete=r["valor_frete"],
            valor_seguro=r["valor_seguro"],
            valor_outras_despesas=r["valor_outras_despesas"],
            valor_desconto=desconto_total,
            simples_nacional=dados_nota.simples_nacional,
        )

        # PIS/COFINS (usa ICMS calculado para possível exclusão da base)
        piscofins = calcular_pis_cofins(
            valor_bruto=item.valor_bruto,
            valor_frete=r["valor_frete"],
            valor_seguro=r["valor_seguro"],
            valor_outras_despesas=r["valor_outras_despesas"],
            valor_desconto=desconto_total,
            aliquota_pis=item.aliquota_pis,
            aliquota_cofins=item.aliquota_cofins,
            cst_pis=item.cst_pis,
            cst_cofins=item.cst_cofins,
            icms_valor=icms.valor,
            excluir_icms_base=dados_nota.excluir_icms_base_pis_cofins,
        )

        itens_impostos.append(ImpostosItem(
            numero_item=item.numero_item,
            # Rateio
            valor_frete=r["valor_frete"],
            valor_seguro=r["valor_seguro"],
            valor_outras_despesas=r["valor_outras_despesas"],
            valor_desconto=desconto_total,
            # ICMS
            icms_origem=icms.origem,
            icms_situacao_tributaria=icms.situacao_tributaria,
            icms_base_calculo=icms.base_calculo,
            icms_aliquota=icms.aliquota,
            icms_valor=icms.valor,
            icms_reducao_base=icms.reducao_base,
            icms_codigo_beneficio_fiscal=icms.codigo_beneficio_fiscal,
            icms_aliquota_credito_simples=icms.aliquota_credito_simples,
            icms_valor_credito_simples=icms.valor_credito_simples,
            # PIS
            pis_situacao_tributaria=piscofins.pis_cst,
            pis_base_calculo=piscofins.pis_base,
            pis_aliquota=piscofins.pis_aliquota,
            pis_valor=piscofins.pis_valor,
            # COFINS
            cofins_situacao_tributaria=piscofins.cofins_cst,
            cofins_base_calculo=piscofins.cofins_base,
            cofins_aliquota=piscofins.cofins_aliquota,
            cofins_valor=piscofins.cofins_valor,
            # IPI (não calculado — comércio/serviços)
            ipi_situacao_tributaria=CST_IPI_NAO_TRIBUTADO,
            ipi_codigo_enquadramento=IPI_CODIGO_ENQUADRAMENTO,
        ))

    # 4. Consolidação
    totais = consolidar_totais(itens, itens_impostos)

    return ResultadoCalculo(itens=itens_impostos, totais=totais)
