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

import re
from typing import Optional

from app.db.models.cliente import Cliente, ClientePF, ClientePJ
from app.db.models.empresa import Empresa
from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings
from app.db.models.endereco import Endereco
from app.db.models.venda import Venda
from app.db.models.venda_nota_fiscal import VendaNotaFiscal

from .helpers import obter_crt, usa_csosn
from .tax_engine.types import ResultadoCalculo


def _sanitizar_texto_sefaz(texto: str, max_chars: int = 60) -> str:
    """Remove caracteres inválidos para XML da SEFAZ e trunca ao limite."""
    if not texto:
        return ""
    texto = re.sub(r"[&<>\"']", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto[:max_chars]


def _centavos_para_reais(centavos: int) -> float:
    """Converte centavos (int) para float com 2 decimais."""
    return round(centavos / 100, 2)


SEM_GTIN = "SEM GTIN"


def _sanitizar_ncm(ncm: Optional[str]) -> Optional[str]:
    """
    Remove pontuação do NCM. '8471.30.12' → '84713012'.

    O gate já recusa NCM fora do formato, mas quem cadastrou com pontos recebia
    uma pendência sem entender o motivo. Sanitizar aqui fecha o caminho para a
    SEFAZ mesmo que algum cadastro escape do gate.
    """
    if not ncm:
        return None
    return re.sub(r"\D", "", ncm) or None


def _gtin_valido(codigo: Optional[str]) -> bool:
    """
    Confere se o código é um GTIN GS1 legítimo (8, 12, 13 ou 14 dígitos com
    dígito verificador correto).

    Códigos internos de loja não são GTIN. Enviá-los em cEAN gera Rejeição 611.
    """
    if not codigo:
        return False

    digitos = codigo.strip()
    if not digitos.isdigit() or len(digitos) not in (8, 12, 13, 14):
        return False

    # Checksum GS1: pesos 3 e 1 alternados da direita para a esquerda,
    # ignorando o próprio dígito verificador.
    corpo, verificador = digitos[:-1], int(digitos[-1])
    soma = 0
    for posicao, caractere in enumerate(reversed(corpo)):
        soma += int(caractere) * (3 if posicao % 2 == 0 else 1)

    return (10 - soma % 10) % 10 == verificador


def _codigo_barras_para_sefaz(codigo: Optional[str]) -> str:
    """Devolve o GTIN quando válido; senão o literal exigido pela SEFAZ."""
    return codigo.strip() if _gtin_valido(codigo) else SEM_GTIN


def _montar_emitente(empresa: Empresa, endereco: Endereco, fiscal_settings: EmpresaFiscalSettings) -> dict:
    return {
        "cnpj": empresa.documento,
        "razao_social": _sanitizar_texto_sefaz(empresa.razao_social),
        "nome_fantasia": _sanitizar_texto_sefaz(empresa.nome_fantasia or empresa.razao_social),
        "inscricao_estadual": empresa.inscricao_estadual,
        "inscricao_municipal": empresa.inscricao_municipal,
        # A SEFAZ espera o CRT numérico (1..4). O texto vai junto só como
        # rótulo — nunca é ele que decide a tributação.
        "codigo_regime_tributario": obter_crt(empresa),
        "regime_tributario": empresa.regime_tributario,
        "endereco": {
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
        dest["cnpj"] = cliente.cnpj
        dest["razao_social"] = _sanitizar_texto_sefaz(cliente.razao_social)
        dest["nome"] = _sanitizar_texto_sefaz(cliente.razao_social)
        dest["inscricao_estadual"] = cliente.ie or ""
        # indicador_ie: 1=Contribuinte (tem IE), 9=Não contribuinte (sem IE)
        dest["indicador_ie"] = "1" if cliente.ie else "9"
    elif isinstance(cliente, ClientePF):
        dest["cpf"] = cliente.cpf
        dest["nome"] = _sanitizar_texto_sefaz(cliente.nome)
        dest["indicador_ie"] = "9"  # PF é sempre não contribuinte
    else:
        dest["nome"] = f"Cliente #{cliente.id}"
        dest["indicador_ie"] = "9"

    # Endereço do destinatário (primeiro endereço cadastrado).
    # Grupo incompleto é rejeitado pela SEFAZ; melhor omitir do que enviar com
    # campos vazios. O gate valida o endereço do emitente, nunca o do cliente.
    enderecos = getattr(cliente, "endereco", None)
    if enderecos and len(enderecos) > 0:
        endereco = _montar_endereco_destinatario(enderecos[0])
        if endereco:
            dest["endereco"] = endereco

    return dest


# Campos sem os quais o grupo enderDest não é aceito pela SEFAZ.
_CAMPOS_ENDERECO_OBRIGATORIOS = ("logradouro", "numero", "bairro", "cidade", "cep")


def _montar_endereco_destinatario(end: Endereco) -> Optional[dict]:
    """Monta o endereço do destinatário, ou None se estiver incompleto."""
    if any(not getattr(end, campo, None) for campo in _CAMPOS_ENDERECO_OBRIGATORIOS):
        return None

    uf = end.estado.value if hasattr(end.estado, "value") else str(end.estado or "")
    if not uf:
        return None

    return {
        "logradouro": end.logradouro,
        "numero": end.numero,
        "complemento": end.complemento or "",
        "bairro": end.bairro,
        "cidade": end.cidade,
        "uf": uf,
        "cep": end.cep,
    }


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
            raise ValueError(
                f"Item #{idx} é avulso (sem produto). "
                f"Todos os itens devem ter produto vinculado para gerar payload NF-e."
            )

        fiscal = produto.fiscal

        item_dict = {
            "numero_item": idx,
            "codigo_produto": produto.codigo_produto or str(produto.id),
            "descricao": produto.nome,
            "quantidade_comercial": float(item.quantidade),
            "valor_unitario_comercial": _centavos_para_reais(item.valor_unitario),
            "valor_bruto": _centavos_para_reais(item.subtotal),
            "unidade_comercial": produto.unidade_medida or "UN",
            "codigo_barras_comercial": _codigo_barras_para_sefaz(produto.codigo_barras),
        }

        if fiscal:
            item_dict["ncm"] = _sanitizar_ncm(fiscal.ncm)
            item_dict["cfop"] = fiscal.cfop_padrao
            item_dict["icms_origem"] = str(fiscal.origem_mercadoria or 0)
            item_dict["unidade_tributavel"] = fiscal.unidade_tributavel or produto.unidade_medida or "UN"
            item_dict["codigo_barras_tributavel"] = _codigo_barras_para_sefaz(
                fiscal.gtin_tributavel or produto.codigo_barras
            )
            if fiscal.cest:
                item_dict["cest"] = fiscal.cest

            if simples_nacional:
                item_dict["icms_situacao_tributaria"] = fiscal.csosn
            else:
                item_dict["icms_situacao_tributaria"] = fiscal.cst_icms

        # Enriquecer com dados tributários calculados pelo tax_engine
        imp = impostos_por_item.get(idx)
        if imp:
            item_dict.update({
                # Rateio
                "valor_frete": float(imp.valor_frete),
                "valor_seguro": float(imp.valor_seguro),
                "valor_outras_despesas_acessorias": float(imp.valor_outras_despesas),
                "valor_desconto": float(imp.valor_desconto),
                # ICMS
                "icms_origem": imp.icms_origem,
                "icms_situacao_tributaria": imp.icms_situacao_tributaria,
                "icms_modalidade_base_calculo": imp.icms_modalidade_base_calculo,
                "icms_base_calculo": float(imp.icms_base_calculo),
                "icms_aliquota": float(imp.icms_aliquota),
                "icms_valor": float(imp.icms_valor),
                # PIS
                "pis_situacao_tributaria": imp.pis_situacao_tributaria,
                "pis_base_calculo": float(imp.pis_base_calculo),
                "pis_aliquota_porcentual": float(imp.pis_aliquota),
                "pis_valor": float(imp.pis_valor),
                # COFINS
                "cofins_situacao_tributaria": imp.cofins_situacao_tributaria,
                "cofins_base_calculo": float(imp.cofins_base_calculo),
                "cofins_aliquota_porcentual": float(imp.cofins_aliquota),
                "cofins_valor": float(imp.cofins_valor),
                # IPI
                "ipi_situacao_tributaria": imp.ipi_situacao_tributaria,
                "ipi_codigo_enquadramento": imp.ipi_codigo_enquadramento,
            })
            # CST 20 — Redução de base + código benefício fiscal
            if imp.icms_reducao_base is not None:
                item_dict["icms_reducao_base_calculo"] = float(imp.icms_reducao_base)
            if imp.icms_codigo_beneficio_fiscal:
                item_dict["icms_codigo_beneficio_fiscal_reducao_base_calculo"] = imp.icms_codigo_beneficio_fiscal
            # CSOSN 101 — Crédito do Simples Nacional
            if imp.icms_aliquota_credito_simples is not None:
                item_dict["icms_aliquota_aplicavel_calculo_credito"] = float(imp.icms_aliquota_credito_simples)
                item_dict["icms_valor_credito_aproveitado"] = float(imp.icms_valor_credito_simples)
        else:
            # Fallback: sem tax_engine, mantém desconto do item
            if item.desconto and item.desconto > 0:
                item_dict["valor_desconto"] = _centavos_para_reais(item.desconto)

        itens.append(item_dict)

    # Validar alinhamento: se tax_engine rodou, cada item deve ter imposto calculado
    if resultado_calculo and len(impostos_por_item) != len(itens):
        raise ValueError(
            f"Desalinhamento: tax_engine calculou {len(impostos_por_item)} itens, "
            f"mas payload tem {len(itens)} itens."
        )

    return itens


def _montar_pagamentos(venda: Venda) -> list[dict]:
    pagamentos = []

    for pag in venda.pagamentos:
        forma = pag.forma_pagamento
        pag_dict = {
            "forma_pagamento": forma.codigo_sefaz or "99",
            "valor_pagamento": _centavos_para_reais(pag.valor),  # já retorna float
        }
        pagamentos.append(pag_dict)

    return pagamentos


def _validar_fechamento_pagamentos(
    pagamentos: list[dict], valor_troco: float, valor_total_nota: float
) -> None:
    """
    Confere a regra do grupo <pag>: soma dos pagamentos − troco == total da nota.

    A SEFAZ audita isso (Rejeição 767). Falhar aqui é barato; descobrir na
    transmissão custa o número da nota e uma inutilização.
    """
    soma_pagamentos = round(sum(p["valor_pagamento"] for p in pagamentos), 2)
    liquido = round(soma_pagamentos - valor_troco, 2)

    if liquido != round(valor_total_nota, 2):
        raise ValueError(
            f"Pagamentos não fecham com o total da nota: "
            f"soma dos pagamentos R$ {soma_pagamentos:.2f} − troco R$ {valor_troco:.2f} "
            f"= R$ {liquido:.2f}, mas o total da nota é R$ {valor_total_nota:.2f}."
        )


def montar_payload_nfe(
    empresa: Empresa,
    endereco_empresa: Endereco,
    fiscal_settings: EmpresaFiscalSettings,
    venda: Venda,
    nota_fiscal: Optional[VendaNotaFiscal],
    resultado_calculo: Optional[ResultadoCalculo] = None,
    numero: Optional[int] = None,
) -> dict:
    """
    Monta payload completo para emissão de NF-e a partir de uma venda.

    Quando resultado_calculo é fornecido, enriquece itens e header com
    dados tributários calculados pelo FiscalTaxEngine.

    `numero` é o número já reservado por `crud.reservar_proximo_numero_nfe`.
    Quando omitido (preview, testes), deriva de `ultimo_numero_nfe + 1` — que
    é só uma previsão, NÃO uma reserva: não use esse caminho para emitir.

    Retorna dict no formato esperado pela API (referência Focus NFe).
    """
    crt = obter_crt(empresa)
    simples = usa_csosn(crt)

    natureza = "Venda de Mercadoria"
    finalidade = 1
    consumidor_final = True
    indicador_presenca = 1

    if nota_fiscal:
        natureza = nota_fiscal.natureza_operacao or natureza
        finalidade = nota_fiscal.finalidade_emissao or finalidade
        consumidor_final = nota_fiscal.consumidor_final if nota_fiscal.consumidor_final is not None else consumidor_final
        indicador_presenca = nota_fiscal.indicador_presenca or indicador_presenca

    if numero is None:
        numero = fiscal_settings.ultimo_numero_nfe + 1
    serie = fiscal_settings.serie_nfe

    # --- Destinatário ---
    if venda.cliente:
        destinatario = _montar_destinatario(venda.cliente)
    else:
        destinatario = {"nome": "CONSUMIDOR FINAL"}

    # --- Totais ---
    if resultado_calculo:
        t = resultado_calculo.totais
        totais = {
            "valor_produtos": float(t.valor_total_produtos),
            "valor_frete": float(t.valor_frete),
            "valor_seguro": float(t.valor_seguro),
            "valor_outras_despesas": float(t.valor_outras_despesas),
            "valor_desconto": float(t.valor_desconto),
            "icms_base_calculo": float(t.base_calculo_icms),
            "icms_valor_total": float(t.valor_icms),
            "valor_total": float(t.valor_total_nota),
        }
    else:
        totais = {
            "valor_produtos": _centavos_para_reais(venda.total),
            "valor_desconto": 0.0,
            "valor_frete": 0.0,
            "valor_seguro": 0.0,
            "valor_outras_despesas": 0.0,
            "icms_base_calculo": 0.0,
            "icms_valor_total": 0.0,
            "valor_total": _centavos_para_reais(venda.total),
        }

    # --- Pagamentos e troco ---
    # O troco é derivado (soma dos pagamentos − total da venda). A SEFAZ exige
    # a tag explícita quando há pagamento em dinheiro acima do total (Rej. 391).
    formas_pagamento = _montar_pagamentos(venda)
    valor_troco = _centavos_para_reais(venda.troco or 0)

    _validar_fechamento_pagamentos(formas_pagamento, valor_troco, totais["valor_total"])

    payload = {
        # --- Parâmetros da nota ---
        # modelo 55 = NF-e. Sem este campo a API intermediária teria que
        # adivinhar; NFC-e (65) ainda não é emitida por este caminho.
        "modelo": 55,
        "natureza_operacao": natureza,
        "tipo_documento": 1,  # 1 = saída
        # idDest 1 = operação interna. O motor bloqueia operação interestadual
        # (DIFAL/FCP não implementado), então aqui é sempre interna.
        "local_destino": 1,
        # modFrete 9 = sem transporte. Obrigatório mesmo sem frete; quando há
        # valor de entrega ele é por conta do emitente (0).
        "modalidade_frete": 0 if venda.entrega else 9,
        "finalidade_emissao": finalidade,
        "consumidor_final": 1 if consumidor_final else 0,
        "presenca_comprador": indicador_presenca,
        "numero": numero,
        "serie": serie,
        # --- Emitente (objeto aninhado) ---
        "emitente": _montar_emitente(empresa, endereco_empresa, fiscal_settings),
        # --- Destinatário (objeto aninhado) ---
        "destinatario": destinatario,
        # --- Itens ---
        "items": _montar_itens(venda, simples, resultado_calculo),
        # --- Pagamentos ---
        "formas_pagamento": formas_pagamento,
        "valor_troco": valor_troco,
        # --- Totais (objeto aninhado) ---
        "totais": totais,
    }

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
        "emitente": _montar_emitente(empresa, endereco_empresa, fiscal_settings),
        "destinatario": {
            "cpf": "00000000000",
            "nome": "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL",
        },
        "items": [
            {
                "numero_item": 1,
                "codigo_produto": "TESTE001",
                "descricao": "NOTA FISCAL EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL",
                "ncm": "00000000",
                "cfop": "5102",
                "unidade_comercial": "UN",
                "quantidade_comercial": 1.0,
                "valor_unitario_comercial": 1.0,
                "valor_bruto": 1.0,
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
                "valor_pagamento": 1.0,
            }
        ],
        "totais": {
            "valor_produtos": 1.0,
            "valor_desconto": 0.0,
            "valor_frete": 0.0,
            "valor_seguro": 0.0,
            "valor_outras_despesas": 0.0,
            "icms_base_calculo": 0.0,
            "icms_valor_total": 0.0,
            "valor_total": 1.0,
        },
    }
