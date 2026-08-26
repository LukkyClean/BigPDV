# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/payload_builder.py
# DESCRIÇÃO: Montagem de payloads para emissão de NF-e.
#
# O payload segue o formato Focus NFe como referência (será ajustado
# quando os endpoints da API Online StartBig forem definidos).
#
# Valores monetários: o backend armazena em centavos (int).
# O payload converte para reais (str com 2 decimais).
# ---------------------------------------------------------------------------

from typing import Optional

from app.db.models.cliente import Cliente, ClientePF, ClientePJ
from app.db.models.empresa import Empresa
from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings
from app.db.models.endereco import Endereco
from app.db.models.venda import Venda
from app.db.models.venda_nota_fiscal import VendaNotaFiscal

from .helpers import is_simples_nacional
from .tax_engine.types import ResultadoCalculo


def _centavos_para_reais(centavos: int) -> str:
    """Converte centavos (int) para string com 2 decimais."""
    return f"{centavos / 100:.2f}"


def _montar_emitente(empresa: Empresa, endereco: Endereco, fiscal_settings: EmpresaFiscalSettings) -> dict:
    return {
        "cnpj_emitente": empresa.documento,
        "razao_social_emitente": empresa.razao_social,
        "nome_fantasia_emitente": empresa.nome_fantasia or empresa.razao_social,
        "inscricao_estadual_emitente": empresa.inscricao_estadual,
        "inscricao_municipal_emitente": empresa.inscricao_municipal,
        "regime_tributario_emitente": empresa.regime_tributario,
        "endereco_emitente": {
            "logradouro": endereco.logradouro,
            "numero": endereco.numero,
            "complemento": endereco.complemento or "",
            "bairro": endereco.bairro,
            "cidade": endereco.cidade,
            "uf": endereco.estado.value if hasattr(endereco.estado, "value") else str(endereco.estado),
            "cep": endereco.cep,
        },
    }


def _montar_destinatario(cliente: Cliente) -> dict:
    dest: dict = {}

    if isinstance(cliente, ClientePJ):
        dest["cnpj_destinatario"] = cliente.cnpj
        dest["razao_social_destinatario"] = cliente.razao_social
        dest["inscricao_estadual_destinatario"] = cliente.ie or ""
    elif isinstance(cliente, ClientePF):
        dest["cpf_destinatario"] = cliente.cpf
        dest["nome_destinatario"] = cliente.nome
    else:
        dest["nome_destinatario"] = f"Cliente #{cliente.id}"

    return dest


def _montar_itens(
    venda: Venda,
    simples_nacional: bool,
    resultado_calculo: Optional[ResultadoCalculo] = None,
) -> list[dict]:
    itens = []

    # Indexar impostos por numero_item para lookup rápido
    impostos_por_item: dict = {}
    if resultado_calculo:
        for imp in resultado_calculo.itens:
            impostos_por_item[imp.numero_item] = imp

    for idx, item in enumerate(venda.itens, start=1):
        produto = item.produto
        if not produto:
            continue

        fiscal = produto.fiscal

        item_dict = {
            "numero_item": idx,
            "codigo_produto": produto.codigo_produto or str(produto.id),
            "descricao": produto.nome,
            "quantidade_comercial": str(item.quantidade),
            "valor_unitario_comercial": _centavos_para_reais(item.valor_unitario),
            "valor_bruto": _centavos_para_reais(item.subtotal),
            "unidade_comercial": produto.unidade_medida or "UN",
            "codigo_barras_comercial": produto.codigo_barras or "SEM GTIN",
        }

        if fiscal:
            item_dict["ncm"] = fiscal.ncm
            item_dict["cfop"] = fiscal.cfop_padrao
            item_dict["icms_origem"] = str(fiscal.origem_mercadoria or 0)
            item_dict["unidade_tributavel"] = fiscal.unidade_tributavel or produto.unidade_medida or "UN"
            item_dict["codigo_barras_tributavel"] = fiscal.gtin_tributavel or produto.codigo_barras or "SEM GTIN"

            if simples_nacional:
                item_dict["icms_situacao_tributaria"] = fiscal.csosn
            else:
                item_dict["icms_situacao_tributaria"] = fiscal.cst_icms

        # Enriquecer com dados tributários calculados pelo tax_engine
        imp = impostos_por_item.get(idx)
        if imp:
            item_dict.update({
                # Rateio
                "valor_frete": str(imp.valor_frete),
                "valor_seguro": str(imp.valor_seguro),
                "valor_outras_despesas_acessorias": str(imp.valor_outras_despesas),
                "valor_desconto": str(imp.valor_desconto),
                # ICMS
                "icms_origem": str(imp.icms_origem),
                "icms_situacao_tributaria": imp.icms_situacao_tributaria,
                "icms_modalidade_base_calculo": imp.icms_modalidade_base_calculo,
                "icms_base_calculo": str(imp.icms_base_calculo),
                "icms_aliquota": str(imp.icms_aliquota),
                "icms_valor": str(imp.icms_valor),
                # PIS
                "pis_situacao_tributaria": imp.pis_situacao_tributaria,
                "pis_base_calculo": str(imp.pis_base_calculo),
                "pis_aliquota_porcentual": str(imp.pis_aliquota),
                "pis_valor": str(imp.pis_valor),
                # COFINS
                "cofins_situacao_tributaria": imp.cofins_situacao_tributaria,
                "cofins_base_calculo": str(imp.cofins_base_calculo),
                "cofins_aliquota_porcentual": str(imp.cofins_aliquota),
                "cofins_valor": str(imp.cofins_valor),
                # IPI
                "ipi_situacao_tributaria": imp.ipi_situacao_tributaria,
                "ipi_codigo_enquadramento": imp.ipi_codigo_enquadramento,
            })
            # CST 20 — Redução de base + código benefício fiscal
            if imp.icms_reducao_base is not None:
                item_dict["icms_reducao_base_calculo"] = str(imp.icms_reducao_base)
            if imp.icms_codigo_beneficio_fiscal:
                item_dict["icms_codigo_beneficio_fiscal_reducao_base_calculo"] = imp.icms_codigo_beneficio_fiscal
            # CSOSN 101 — Crédito do Simples Nacional
            if imp.icms_aliquota_credito_simples is not None:
                item_dict["icms_aliquota_aplicavel_calculo_credito"] = str(imp.icms_aliquota_credito_simples)
                item_dict["icms_valor_credito_aproveitado"] = str(imp.icms_valor_credito_simples)
        else:
            # Fallback: sem tax_engine, mantém desconto do item
            if item.desconto and item.desconto > 0:
                item_dict["valor_desconto"] = _centavos_para_reais(item.desconto)

        itens.append(item_dict)

    return itens


def _montar_pagamentos(venda: Venda) -> list[dict]:
    pagamentos = []

    for pag in venda.pagamentos:
        forma = pag.forma_pagamento
        pag_dict = {
            "forma_pagamento": forma.codigo_sefaz or "99",
            "valor_pagamento": _centavos_para_reais(pag.valor),
        }
        pagamentos.append(pag_dict)

    return pagamentos


def montar_payload_nfe(
    empresa: Empresa,
    endereco_empresa: Endereco,
    fiscal_settings: EmpresaFiscalSettings,
    venda: Venda,
    nota_fiscal: Optional[VendaNotaFiscal],
    resultado_calculo: Optional[ResultadoCalculo] = None,
) -> dict:
    """
    Monta payload completo para emissão de NF-e a partir de uma venda.

    Quando resultado_calculo é fornecido, enriquece itens e header com
    dados tributários calculados pelo FiscalTaxEngine.

    Retorna dict no formato esperado pela API (referência Focus NFe).
    """
    simples = is_simples_nacional(empresa.regime_tributario)

    natureza = "Venda de Mercadoria"
    finalidade = 1
    consumidor_final = True
    indicador_presenca = 1

    if nota_fiscal:
        natureza = nota_fiscal.natureza_operacao or natureza
        finalidade = nota_fiscal.finalidade_emissao or finalidade
        consumidor_final = nota_fiscal.consumidor_final if nota_fiscal.consumidor_final is not None else consumidor_final
        indicador_presenca = nota_fiscal.indicador_presenca or indicador_presenca

    numero = fiscal_settings.ultimo_numero_nfe + 1
    serie = fiscal_settings.serie_nfe

    payload = {
        # --- Parâmetros da nota ---
        "natureza_operacao": natureza,
        "tipo_documento": 1,  # 1 = saída
        "finalidade_emissao": finalidade,
        "consumidor_final": 1 if consumidor_final else 0,
        "presenca_comprador": indicador_presenca,
        "numero": numero,
        "serie": serie,
        # --- Emitente ---
        **_montar_emitente(empresa, endereco_empresa, fiscal_settings),
        # --- Destinatário ---
        **(_montar_destinatario(venda.cliente) if venda.cliente else {}),
        # --- Itens ---
        "items": _montar_itens(venda, simples, resultado_calculo),
        # --- Pagamentos ---
        "formas_pagamento": _montar_pagamentos(venda),
    }

    # --- Totais ---
    if resultado_calculo:
        totais = resultado_calculo.totais
        payload.update({
            "valor_produtos": str(totais.valor_total_produtos),
            "valor_frete": str(totais.valor_frete),
            "valor_seguro": str(totais.valor_seguro),
            "valor_outras_despesas": str(totais.valor_outras_despesas),
            "valor_desconto": str(totais.valor_desconto),
            "icms_base_calculo": str(totais.base_calculo_icms),
            "icms_valor_total": str(totais.valor_icms),
            "valor_total": str(totais.valor_total_nota),
        })
    else:
        payload["valor_total"] = _centavos_para_reais(venda.total)

    return payload


def montar_payload_teste_nfe(
    empresa: Empresa,
    endereco_empresa: Endereco,
    fiscal_settings: EmpresaFiscalSettings,
) -> dict:
    """
    Monta payload fictício para emissão de teste em homologação.
    Usa dados mínimos válidos para a SEFAZ aceitar.
    """
    numero = fiscal_settings.ultimo_numero_nfe + 1
    serie = fiscal_settings.serie_nfe

    return {
        "natureza_operacao": "VENDA DE MERCADORIA",
        "tipo_documento": 1,
        "finalidade_emissao": 1,
        "consumidor_final": 1,
        "presenca_comprador": 1,
        "numero": numero,
        "serie": serie,
        **_montar_emitente(empresa, endereco_empresa, fiscal_settings),
        "cpf_destinatario": "00000000000",
        "nome_destinatario": "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL",
        "items": [
            {
                "numero_item": 1,
                "codigo_produto": "TESTE001",
                "descricao": "NOTA FISCAL EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL",
                "ncm": "00000000",
                "cfop": "5102",
                "unidade_comercial": "UN",
                "quantidade_comercial": "1.00",
                "valor_unitario_comercial": "1.00",
                "valor_bruto": "1.00",
                "icms_origem": "0",
                "icms_situacao_tributaria": "102",
                "codigo_barras_comercial": "SEM GTIN",
                "unidade_tributavel": "UN",
                "codigo_barras_tributavel": "SEM GTIN",
            }
        ],
        "formas_pagamento": [
            {
                "forma_pagamento": "01",
                "valor_pagamento": "1.00",
            }
        ],
        "valor_total": "1.00",
    }
