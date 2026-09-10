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


def expurgar_nulos(valor):
    """Remove recursivamente chaves nulas/vazias do payload.

    A integradora e a SEFAZ recusam nós vazios — uma tag de desconto sem valor
    derruba a nota inteira. Como o payload é montado a partir de colunas
    opcionais do banco, sobra `None` em vários pontos; limpar na saída é mais
    seguro do que lembrar de cada `if` na montagem.

    O que É descartado: `None`, string vazia (ou só espaços), dict/lista que
    ficou vazia depois da limpeza.

    O que NÃO é descartado: `0`, `0.0` e `False`. São valores legítimos —
    `valor_desconto: 0.0` e `consumidor_final: 0` mudam de significado se
    sumirem, e o total deixa de fechar.
    """
    if isinstance(valor, dict):
        limpo = {}
        for chave, item in valor.items():
            item_limpo = expurgar_nulos(item)
            if item_limpo is None:
                continue
            limpo[chave] = item_limpo
        return limpo or None

    if isinstance(valor, list):
        limpa = [i for i in (expurgar_nulos(v) for v in valor) if i is not None]
        return limpa or None

    if valor is None:
        return None

    if isinstance(valor, str) and not valor.strip():
        return None

    return valor


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


def _so_digitos(valor) -> Optional[str]:
    """Remove tudo que não for dígito. Usado só na SAÍDA, nunca no banco.

    CNPJ, CPF e CEP viajam sem pontuação para a SEFAZ. Hoje o cadastro guarda
    esses campos limpos, então isto é rede de proteção e não conserto: se um dia
    entrar um documento mascarado -- por importação, por colagem, por um campo
    novo sem máscara na borda --, a nota é recusada longe daqui, com uma
    mensagem que não aponta para o cadastro.

    Normalizar na borda e não no banco é deliberado: o que o lojista digitou
    continua sendo o que ele vê na tela.
    """
    if valor is None:
        return None
    limpo = re.sub(r"\D", "", str(valor))
    return limpo or None


def _montar_emitente(empresa: Empresa, endereco: Endereco, fiscal_settings: EmpresaFiscalSettings) -> dict:
    return {
        "cnpj": _so_digitos(empresa.documento),
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
            "cep": _so_digitos(endereco.cep),
        },
    }


def _montar_destinatario(cliente: Cliente) -> dict:
    dest: dict = {}

    if isinstance(cliente, ClientePJ):
        dest["cnpj"] = _so_digitos(cliente.cnpj)
        dest["razao_social"] = _sanitizar_texto_sefaz(cliente.razao_social)
        dest["nome"] = _sanitizar_texto_sefaz(cliente.razao_social)
        dest["inscricao_estadual"] = cliente.ie or ""
        # indicador_ie: 1=Contribuinte (tem IE), 9=Não contribuinte (sem IE)
        dest["indicador_ie"] = "1" if cliente.ie else "9"
    elif isinstance(cliente, ClientePF):
        dest["cpf"] = _so_digitos(cliente.cpf)
        dest["nome"] = _sanitizar_texto_sefaz(cliente.nome)
        dest["indicador_ie"] = "9"  # PF é sempre não contribuinte
    else:
        dest["nome"] = f"Cliente #{cliente.id}"
        dest["indicador_ie"] = "9"

    # Endereço do destinatário (primeiro endereço cadastrado).
    #
    # Grupo incompleto é rejeitado pela SEFAZ, e OMITIR TAMBÉM É — o comentário
    # anterior dizia que omitir era o mal menor, e a nota de teste provou o
    # contrário: 422 nomeando logradouro, número, bairro e município do
    # destinatário. Na NF-e o enderDest é obrigatório.
    #
    # A omissão continua aqui porque este mesmo construtor serve à NFC-e com
    # entrega a domicílio, e porque quem impede uma NF-e de chegar até aqui sem
    # endereço agora é o gate (`verificar_endereco_destinatario`), que recusa
    # ANTES de montar payload e reservar número, nomeando os campos que faltam
    # no cadastro do cliente. Este ponto é o último recurso, não a defesa.
    enderecos = getattr(cliente, "endereco", None)
    if enderecos and len(enderecos) > 0:
        endereco = _montar_endereco_destinatario(enderecos[0])
        if endereco:
            dest["endereco"] = endereco

    return dest


def _montar_destinatario_nfce(
    cliente: Optional[Cliente],
    documento_consumidor: Optional[str],
    entrega_domicilio: bool = False,
) -> Optional[dict]:
    """Destinatário da NFC-e — ou None para consumidor não identificado.

    Difere da NF-e em dois pontos, e os dois são exigência do modelo 65:

    1. **Pode não existir.** Na NF-e, sem cliente mandamos
       `{"nome": "CONSUMIDOR FINAL"}`. Na NFC-e o grupo `dest` inteiro é
       OMITIDO — mandá-lo só com um nome genérico, sem documento, é rejeitado.
    2. **Só o documento.** No varejo presencial não há endereço nem nome do
       comprador a informar; enviar o grupo de endereço incompleto derruba a
       autorização.

    Precedência: o cadastro do cliente vence, porque foi conferido; o CPF
    digitado no caixa é o caminho do consumidor de passagem.

    EXCEÇÃO — `entrega_domicilio` (indPres 4): aí as duas regras acima se
    invertem. A SEFAZ exige o grupo `dest` completo (rejeição 787) COM
    endereço (rejeição 788), porque a mercadoria vai circular até a casa do
    comprador. Nesse caso reusamos o destinatário da NF-e, que já monta nome
    e endereço.
    """
    if entrega_domicilio:
        if cliente is None:
            raise ValueError(
                "Entrega a domicílio exige um cliente identificado na venda: a "
                "NFC-e com indPres 4 é recusada sem os dados do destinatário "
                "(rejeição 787)."
            )
        destinatario = _montar_destinatario(cliente)
        if not destinatario.get("endereco"):
            raise ValueError(
                "Entrega a domicílio exige o endereço do cliente: a NFC-e com "
                "indPres 4 é recusada sem ele (rejeição 788)."
            )
        return destinatario

    if cliente is not None:
        if isinstance(cliente, ClientePJ) and cliente.cnpj:
            return {"cnpj": cliente.cnpj, "indicador_ie": "1" if cliente.ie else "9"}
        if isinstance(cliente, ClientePF) and cliente.cpf:
            return {"cpf": cliente.cpf, "indicador_ie": "9"}

    documento = re.sub(r"\D", "", documento_consumidor or "")
    if len(documento) == 11:
        return {"cpf": documento, "indicador_ie": "9"}
    if len(documento) == 14:
        return {"cnpj": documento, "indicador_ie": "9"}

    # Consumidor não identificado: a venda de balcão sem CPF é o caso normal.
    return None


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
        "cep": _so_digitos(end.cep),
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


# Códigos SEFAZ que representam cartão. Só neles o grupo `card` faz sentido —
# dizer "não integrado" num pagamento em dinheiro é ruído no XML.
_CODIGOS_SEFAZ_CARTAO = {"03", "04"}  # 03 = crédito, 04 = débito

# tpIntegra da SEFAZ: 1 = integrado ao sistema (TEF), 2 = não integrado (POS).
_TP_INTEGRA = {"TEF": 1, "POS": 2}


def _montar_pagamentos(venda: Venda) -> list[dict]:
    pagamentos = []

    for pag in venda.pagamentos:
        forma = pag.forma_pagamento
        codigo = forma.codigo_sefaz or "99"
        pag_dict = {
            "forma_pagamento": codigo,
            "valor_pagamento": _centavos_para_reais(pag.valor),  # já retorna float
        }

        if codigo in _CODIGOS_SEFAZ_CARTAO:
            # Sem classificação cadastrada, assume POS (não integrado). É o
            # arranjo da maioria das lojas pequenas, e afirmar integração que
            # não existe descreveria mal a operação num documento fiscal.
            integracao = getattr(forma, "tipo_integracao", None) or "POS"
            if integracao != "NAO_SE_APLICA":
                pag_dict["tipo_integracao"] = _TP_INTEGRA.get(integracao, 2)

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


def _montar_totais_pagamentos(
    venda: Venda, resultado_calculo: Optional[ResultadoCalculo]
) -> tuple[dict, list[dict], float]:
    """Totais, formas de pagamento e troco — comuns a NF-e e NFC-e.

    Já deixa a equação de fechamento conferida: a SEFAZ audita
    `Σ pagamentos − troco == total` nos dois modelos (Rejeição 767), e na NFC-e
    o troco em dinheiro é a regra, não a exceção.
    """
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

    formas_pagamento = _montar_pagamentos(venda)
    valor_troco = _centavos_para_reais(venda.troco or 0)

    _validar_fechamento_pagamentos(formas_pagamento, valor_troco, totais["valor_total"])

    return totais, formas_pagamento, valor_troco


# indPres aceitos pela NFC-e (modelo 65). A regra de validacao da SEFAZ e
# literalmente `indPres <> 1 e 4` -> rejeicao 717 ("NFC-e em operacao nao
# presencial"). Internet (2), teleatendimento (3) e outros (9) NAO valem em
# NFC-e: essas operacoes pedem NF-e.
#
# O 4 (entrega a domicilio) so existe para NFC-e, e arrasta tres exigencias:
#   787 -> grupo `dest` obrigatorio
#   788 -> `enderDest` obrigatorio
#   786 -> grupo `transporta` obrigatorio
# Alem disso a UF precisa PERMITIR entrega a domicilio em NFC-e (rejeicao
# 785, parametrizavel por estado) -- confirmar no ambiente de homologacao.
INDPRES_BALCAO = 1
INDPRES_ENTREGA_DOMICILIO = 4
INDPRES_NFCE_ACEITOS = (INDPRES_BALCAO, INDPRES_ENTREGA_DOMICILIO)


def montar_payload_nfce(
    empresa: Empresa,
    endereco_empresa: Endereco,
    fiscal_settings: EmpresaFiscalSettings,
    venda: Venda,
    nota_fiscal: Optional[VendaNotaFiscal],
    resultado_calculo: Optional[ResultadoCalculo] = None,
    numero: Optional[int] = None,
) -> dict:
    """Monta o payload da NFC-e (modelo 65) a partir de uma venda.

    Diferenças em relação à NF-e que NÃO são cosméticas:

    * `modelo` 65 — NFC-e.
    * `presenca_comprador` vem do que o caixa escolheu no fechamento; cai em 1
      (balcão) quando não informado. Estava CHUMBADO em 1, com a justificativa
      de que "a NFC-e só existe para operação presencial" — o que é falso: o
      indPres 4 (entrega a domicílio) existe justamente e apenas para NFC-e.
      Toda entrega saía com o indicador errado.
    * `consumidor_final` sempre 1: é venda a consumidor, por definição.
    * Destinatário OPCIONAL (ver `_montar_destinatario_nfce`).
    * O CSC NÃO viaja no payload: fica cadastrado na empresa dentro da Focus,
      que monta o QR Code sozinha. Ver o comentário no corpo da função.
    * Saída passa por `expurgar_nulos` — nó vazio é rejeição na hora.

    `numero` é o número já reservado por `crud.reservar_proximo_numero_nfce`.
    Quando omitido (preview), deriva de `ultimo_numero_nfce + 1`, que é uma
    PREVISÃO e não uma reserva: não use esse caminho para emitir.
    """
    crt = obter_crt(empresa)
    simples = usa_csosn(crt)

    natureza = "Venda de Mercadoria"
    if nota_fiscal and nota_fiscal.natureza_operacao:
        natureza = nota_fiscal.natureza_operacao

    if numero is None:
        numero = fiscal_settings.ultimo_numero_nfce + 1

    totais, formas_pagamento, valor_troco = _montar_totais_pagamentos(
        venda, resultado_calculo,
    )

    # Balcão é o default: cobre a esmagadora maioria das vendas e é o que o
    # PDV grava sozinho. `or` em vez de `is not None` é seguro aqui porque 0
    # não é indPres válido (o schema aceita só 1, 2, 3, 4 e 9).
    presenca_comprador = (
        getattr(nota_fiscal, "indicador_presenca", None) or INDPRES_BALCAO
    )
    if presenca_comprador not in INDPRES_NFCE_ACEITOS:
        raise ValueError(
            f"Indicador de presenca {presenca_comprador} nao vale para NFC-e: a "
            f"SEFAZ aceita apenas 1 (presencial) e 4 (entrega a domicilio), e "
            f"recusa o resto com a rejeicao 717. Operacao nao presencial exige "
            f"NF-e."
        )
    entrega_domicilio = presenca_comprador == INDPRES_ENTREGA_DOMICILIO

    documento_consumidor = getattr(nota_fiscal, "documento_consumidor", None)
    destinatario = _montar_destinatario_nfce(
        venda.cliente, documento_consumidor, entrega_domicilio=entrega_domicilio,
    )

    # Quem entrega e a propria loja (motoboy). Sem este grupo a NFC-e com
    # indPres 4 volta com a rejeicao 786.
    transportador = None
    if entrega_domicilio:
        transportador = {
            # Mesma normalização do emitente: documento vai sem pontuação.
            # Ficou de fora quando `_so_digitos` entrou (5e4f934) porque este
            # bloco só existe na NFC-e com entrega a domicílio -- e meio payload
            # normalizado é pior do que nenhum, porque esconde o caso que falta.
            "cnpj": _so_digitos(empresa.documento) if empresa.is_cnpj else None,
            "cpf": None if empresa.is_cnpj else _so_digitos(empresa.documento),
            "razao_social": _sanitizar_texto_sefaz(
                empresa.razao_social or empresa.nome_fantasia
            ),
            "inscricao_estadual": empresa.inscricao_estadual,
            "endereco": _sanitizar_texto_sefaz(endereco_empresa.logradouro),
            "municipio": _sanitizar_texto_sefaz(endereco_empresa.cidade),
            "uf": (
                endereco_empresa.estado.value
                if hasattr(endereco_empresa.estado, "value")
                else str(endereco_empresa.estado)
            ),
        }

    payload = {
        "modelo": 65,
        "natureza_operacao": natureza,
        "tipo_documento": 1,  # saída
        "local_destino": 1,   # operação interna (o motor bloqueia interestadual)
        # 9 = sem transporte (o cliente leva a mercadoria). Na entrega a
        # domicilio quem transporta e a propria loja: 3 = proprio por conta do
        # remetente, e o grupo `transporta` vira obrigatorio (rejeicao 786).
        "modalidade_frete": 3 if entrega_domicilio else 9,
        "finalidade_emissao": 1,
        "consumidor_final": 1,
        "presenca_comprador": presenca_comprador,
        "transportador": transportador,
        "numero": numero,
        "serie": fiscal_settings.serie_nfce,
        "emitente": _montar_emitente(empresa, endereco_empresa, fiscal_settings),
        "items": _montar_itens(venda, simples, resultado_calculo),
        "formas_pagamento": formas_pagamento,
        "valor_troco": valor_troco,
        "totais": totais,
        # O CSC NÃO vai aqui, e isso é deliberado.
        #
        # Ele é cadastrado UMA VEZ na ficha da empresa dentro da Focus, junto do
        # certificado A1, e é ela quem monta o hash do QR Code e a URL de
        # consulta. Nunca foi campo de nota.
        #
        # Enquanto a plataforma validava o payload com schema estrito, mandá-lo
        # era inofensivo: o campo era descartado no caminho. Agora que o payload
        # é repassado inteiro, ele atravessaria até a Focus -- segredo em
        # trânsito sem ganho nenhum. Vazado, permite forjar QR Code em nome da
        # loja.
        #
        # Se o cupom sair sem QR Code, o CSC não está na Focus: veja
        # `cscConfigurado` em GET /erp/fiscal/config. E lembre que ele é POR
        # AMBIENTE -- o de homologação não vale em produção.
    }

    if destinatario is not None:
        payload["destinatario"] = destinatario

    return expurgar_nulos(payload) or {}


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

    # --- Totais, pagamentos e troco ---
    # O troco é derivado (soma dos pagamentos − total da venda). A SEFAZ exige
    # a tag explícita quando há pagamento em dinheiro acima do total (Rej. 391).
    totais, formas_pagamento, valor_troco = _montar_totais_pagamentos(
        venda, resultado_calculo,
    )

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
        # modFrete 9 = sem transporte. Obrigatorio na NF-e 4.0 mesmo quando nao
        # ha frete: a Focus recusou a nota de teste por "modalidade_frete nao
        # pode ser vazio" antes mesmo de chegar na SEFAZ.
        "modalidade_frete": 9,
        "numero": numero,
        "serie": serie,
        "emitente": _montar_emitente(empresa, endereco_empresa, fiscal_settings),
        "destinatario": {
            # CNPJ ficticio padrao de homologacao. Era "00000000000", que a
            # SEFAZ recusa: homologacao dispensa a EXISTENCIA do destinatario,
            # nunca o digito verificador -- e onze zeros nao fecha o modulo 11.
            #
            # Nao inventamos um CPF valido no lugar. Qualquer CPF que passe no
            # digito verificador PODE ser de uma pessoa real, e este numero fica
            # gravado no XML de teste de toda loja. A raiz 99999999 nunca e
            # atribuida pela Receita, entao este CNPJ e valido no calculo e
            # impossivel de colidir com contribuinte de verdade.
            "cnpj": "99999999000191",
            "indicador_ie": "9",  # indIEDest 9 = nao contribuinte
            "nome": "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL",
            # O enderDest e OBRIGATORIO na NF-e (modelo 55). Este destinatario
            # ficticio saia so com CPF e nome, e a nota de teste era recusada
            # com 422 nomeando os cinco campos de endereco.
            #
            # O endereco e o DO PROPRIO EMITENTE de proposito, e nao um endereco
            # inventado: a Focus resolve o par municipio/UF para codigo IBGE, e
            # um municipio que nao existe naquela UF derruba a nota por um
            # motivo que nada tem a ver com o teste. O endereco da loja ja foi
            # aceito no cadastro, entao o par e valido por construcao.
            "endereco": {
                "logradouro": endereco_empresa.logradouro,
                "numero": endereco_empresa.numero,
                "bairro": endereco_empresa.bairro,
                "cidade": endereco_empresa.cidade,
                "uf": (
                    endereco_empresa.estado.value
                    if hasattr(endereco_empresa.estado, "value")
                    else str(endereco_empresa.estado)
                ),
                "cep": _so_digitos(endereco_empresa.cep),
            },
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
