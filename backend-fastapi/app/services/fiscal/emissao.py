# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/emissao.py
# DESCRIÇÃO: Serviço de emissão de NF-e (venda e teste).
#
# Orquestra o fluxo: verificar → montar payload → chamar client → atualizar.
# Cada tentativa de emissão cria uma NOVA linha em documento_fiscal.
# Reemissões (reemissao.py) chamam os mesmos emitir_* com tentativa_anterior_id.
# ---------------------------------------------------------------------------

import logging
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.documento_fiscal import DocumentoFiscal
from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings
from app.schemas.documento_fiscal import DocumentoFiscalRead

from app.db.crud import fiscal as crud
from .core import verificar_completude_venda
from .helpers import obter_crt, obter_csc_token, regime_apuracao, usa_csosn
from .http import get_fiscal_client, EmissaoResultado
from .http.client import (
    CODIGO_NOTA_INEXISTENTE,
    RESULTADO_AUTORIZADO,
    RESULTADO_CANCELADO,
    RESULTADO_NAO_ENCONTRADO,
    RESULTADO_NAO_TRANSMITIDO,
    RESULTADO_PROCESSANDO,
)
from .payload_builder import (
    montar_payload_nfce,
    montar_payload_nfe,
    montar_payload_teste_nfe,
)
from .tax_engine import calcular_impostos
from .tax_engine.resolver import resolver_aliquotas_venda
from .snapshot import gravar_snapshot
from .tributos_xml import extrair_valor_tributos

logger = logging.getLogger(__name__)


# Status que significam "esta nota FOI transmitida e o desfecho ainda está em
# aberto". São os únicos que vale consultar na emissora.
#
# PENDENTE ficou de fora de propósito: a emissão cria o documento já como
# PROCESSANDO, e `salvar_documento` só dá flush dentro da transação da request —
# um processo que morre no meio do HTTP não deixa linha nenhuma. PENDENTE só
# nascia da reemissão antiga, que NÃO transmitia (hoje ela emite de verdade, ver
# reemissao.py); as linhas que sobraram foram convertidas pela migration
# 89eb6b730bb3. Consultar uma dessas dava 404 eterno, e o 404 virava REJEITADA:
# nota que nunca saiu do prédio aparecia na tela como recusada pela SEFAZ.
STATUS_CONSULTAVEIS = ("PROCESSANDO", "INDETERMINADA")

# A nota não chegou à SEFAZ. Não é rejeição — não há protocolo, não há código de
# rejeição, e o número reservado não foi queimado.
STATUS_NAO_TRANSMITIDA = "NAO_TRANSMITIDA"


def _aplicar_resultado(doc: DocumentoFiscal, resultado: EmissaoResultado) -> None:
    """Atualiza DocumentoFiscal com o resultado da API.

    Três desfechos que antes viravam um só, e é por isso que uma lista de
    "rejeitadas" não dizia quais tinham chegado na SEFAZ:

      nunca transmitida (404 na consulta)     -> status intocado + mensagem
      recusada antes da SEFAZ (4xx na emissão) -> NAO_TRANSMITIDA
      rejeitada PELA SEFAZ                     -> REJEITADA, com o código
    """
    status_api = resultado.get("status", "")

    if status_api == RESULTADO_NAO_ENCONTRADO:
        # 404. Quem decide o que ele significa é o CÓDIGO do corpo, não o status
        # HTTP: a plataforma responde 404 tanto para "a nota não está na
        # emissora" quanto para os pré-voos dela (licença não encontrada,
        # empresa sem configuração fiscal), e os pré-voos não afirmam nada sobre
        # a nota.
        #
        # Só `NOTA_NAO_ENCONTRADA_NA_EMISSORA` conclui. Sem ele — pré-voo, ou
        # plataforma antiga que ainda não manda código — o status fica INTOCADO.
        #
        # Errar para o lado de mexer seria o pior desfecho possível: uma
        # INDETERMINADA que na verdade está autorizada na SEFAZ deixaria de
        # trancar a venda, e a próxima emissão viraria nota duplicada, as duas
        # válidas, no mesmo CNPJ. É o que o `EmissaoIncertaError` impede na
        # emissão — e que entrava por esta porta.
        #
        # Nada além da mensagem é sobrescrito: os campos lá embaixo apagariam
        # chave de acesso e protocolo de um documento que já os tinha.
        doc.mensagem_sefaz = resultado.get("mensagem_sefaz")
        if resultado.get("codigo") == CODIGO_NOTA_INEXISTENTE:
            doc.status = STATUS_NAO_TRANSMITIDA
        return

    if status_api == RESULTADO_AUTORIZADO:
        doc.status = "AUTORIZADA"
        doc.data_autorizacao = datetime.now(timezone.utc)
    elif status_api == RESULTADO_PROCESSANDO:
        doc.status = "PROCESSANDO"
    elif status_api == RESULTADO_CANCELADO:
        doc.status = "CANCELADA"
    elif status_api == RESULTADO_NAO_TRANSMITIDO:
        # A plataforma ou a emissora recusaram o payload. A SEFAZ não viu nada.
        doc.status = STATUS_NAO_TRANSMITIDA
    elif resultado.get("status_focus") == "denegado":
        # Denegada é decisão da SEFAZ sobre o CONTRIBUINTE, não sobre a nota:
        # reenviar não adianta, e o lojista precisa saber que a diferença existe.
        # Caía no balde `erro` -> REJEITADA, que convida a reemitir para sempre.
        doc.status = "DENEGADA"
    else:
        # A SEFAZ respondeu "não". Isso é diferente de não sabermos a resposta
        # — falha de comunicação vira INDETERMINADA, nunca REJEITADA.
        doc.status = "REJEITADA"

    doc.chave_acesso = resultado.get("chave_acesso")
    doc.protocolo_autorizacao = resultado.get("protocolo")
    doc.url_pdf = resultado.get("url_pdf")
    doc.url_xml = resultado.get("url_xml")
    # O número é o que não engana. O texto da SEFAZ já chegou dizendo
    # "destinatário" enquanto citava o CNPJ do emitente — meia hora perdida
    # atrás do campo errado. Os dois são gravados: o código para decidir, o
    # texto para ler.
    doc.codigo_status_sefaz = resultado.get("codigo_sefaz")
    doc.mensagem_sefaz = resultado.get("mensagem_sefaz")
    if resultado.get("status_focus"):
        doc.status_focus = resultado["status_focus"]

    if resultado.get("numero"):
        doc.numero_documento = resultado["numero"]
    if resultado.get("serie"):
        doc.serie = resultado["serie"]

    # Campos de NFC-e. A NF-e não os devolve; o `if` evita apagar o que já
    # estava gravado numa reconsulta que venha sem eles.
    if resultado.get("qrcode"):
        doc.qrcode = resultado["qrcode"]
    if resultado.get("url_consulta"):
        doc.url_consulta = resultado["url_consulta"]
    if resultado.get("valor_tributos") is not None:
        doc.valor_tributos = int(round(float(resultado["valor_tributos"]) * 100))


def _obter_fiscal_settings(db: Session, empresa_id: int) -> EmpresaFiscalSettings:
    fs = crud.get_fiscal_settings(db, empresa_id)
    if not fs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Configurações fiscais não cadastradas para esta empresa.",
        )
    return fs


def _preparar_dados_emissao(
    db: Session, venda_id: int, empresa_id: int, tipo_documento: str = "nfe",
):
    """
    Setup compartilhado entre preview e emissão.
    Verifica completude, carrega dados e calcula tributos.

    `tipo_documento` decide se o endereço do destinatário é exigido: a NF-e não
    sai sem ele, a NFC-e não o quer. Quem chama daqui de dentro precisa dizer
    qual está emitindo — o padrão "nfe" é o caminho mais restritivo, então
    esquecer de passar reprova em vez de deixar passar.

    Returns:
        Tupla (empresa, endereco, venda, simples, resultado_calculo).

    Raises:
        HTTPException 422 se dados incompletos ou cálculo falhar.
        HTTPException 404 se venda não encontrada.
    """
    verificacao = verificar_completude_venda(db, venda_id, empresa_id, tipo_documento)
    if not verificacao.completo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "mensagem": "Dados fiscais incompletos para emissão.",
                "pendencias": [p.model_dump() for p in verificacao.pendencias],
            },
        )

    empresa = crud.get_empresa(db, empresa_id)
    endereco = crud.get_endereco_empresa(db, empresa_id)
    venda = crud.get_venda_completa(db, venda_id)
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada.")

    uf_emitente = endereco.estado.value if hasattr(endereco.estado, "value") else str(endereco.estado)
    simples = usa_csosn(obter_crt(empresa))

    try:
        itens_entrada, dados_nota = resolver_aliquotas_venda(
            db, venda, uf_emitente, simples,
            regime_apuracao=regime_apuracao(empresa),
        )
        resultado_calculo = calcular_impostos(itens_entrada, dados_nota)
    except Exception as e:
        logger.error("[FISCAL] Erro no cálculo tributário: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erro no cálculo tributário: {str(e)}",
        )

    return empresa, endereco, venda, simples, resultado_calculo


def preview_nfe_venda(db: Session, venda_id: int, empresa_id: int) -> dict:
    """Retorna os dados de pré-visualização da NF-e sem emiti-la."""
    empresa, endereco, venda, simples, resultado_calculo = _preparar_dados_emissao(
        db, venda_id, empresa_id,
    )

    # Montar resposta de preview
    # Tax engine retorna Decimal em reais — converter para centavos (int)
    # para manter consistência com os demais valores monetários da resposta.
    total_tributos_centavos = int(sum(
        (i.icms_valor + i.pis_valor + i.cofins_valor)
        for i in resultado_calculo.itens
    ) * 100) if resultado_calculo else 0

    itens_preview = []
    for num, item_venda in enumerate(venda.itens, start=1):
        if not item_venda.produto:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Item #{num} é avulso (sem produto cadastrado). "
                       f"Emissão de NF-e requer todos os itens vinculados a produtos.",
            )
        fiscal_prod = item_venda.produto.fiscal
        itens_preview.append({
            "numero_item": num,
            "produto_id": item_venda.produto.id,
            "nome": item_venda.produto.nome,
            "quantidade": float(item_venda.quantidade),
            "valor_unitario": float(item_venda.valor_unitario),
            "valor_total": float(item_venda.total),
            "cfop": fiscal_prod.cfop_padrao if fiscal_prod else "",
            "ncm": fiscal_prod.ncm if fiscal_prod else "",
            "cst_csosn": (
                fiscal_prod.csosn if simples else fiscal_prod.cst_icms
            ) if fiscal_prod else "",
        })

    # Resolver nome/documento do destinatário (herança polimórfica)
    dest_nome = "NÃO INFORMADO"
    dest_documento = ""
    if venda.cliente:
        from app.db.models.cliente import ClientePF, ClientePJ
        if isinstance(venda.cliente, ClientePF):
            dest_nome = venda.cliente.nome or "NÃO INFORMADO"
            dest_documento = venda.cliente.cpf or ""
        elif isinstance(venda.cliente, ClientePJ):
            dest_nome = venda.cliente.razao_social or "NÃO INFORMADO"
            dest_documento = venda.cliente.cnpj or ""

    # Formas de pagamento
    formas_preview = []
    if hasattr(venda, "pagamentos") and venda.pagamentos:
        for pag in venda.pagamentos:
            forma = pag.forma_pagamento if hasattr(pag, "forma_pagamento") else None
            formas_preview.append({
                "nome": forma.nome if forma else "Outros",
                "codigo_sefaz": forma.codigo_sefaz if forma and forma.codigo_sefaz else "99",
                "valor": int(pag.valor),
            })

    return {
        "destinatario": {
            "nome": dest_nome,
            "documento": dest_documento,
        },
        "totais": {
            "valor_produtos": float(sum(i.total for i in venda.itens)),
            "descontos": float(venda.descontos or 0),
            "frete": float(venda.entrega or 0),
            "valor_nota": float(venda.total),
            "total_tributos": total_tributos_centavos
        },
        "itens": itens_preview,
        "formas_pagamento": formas_preview,
    }


def preview_nfce_venda(db: Session, venda_id: int, empresa_id: int) -> dict:
    """Pré-visualização da NFC-e, sem emitir.

    Aproveita o preview da NF-e — itens, totais e tributos são os mesmos — e
    corrige só o que o modelo 65 vê diferente: o destinatário, que pode ser o
    CPF digitado no caixa ou simplesmente não existir.

    Roda as mesmas recusas da emissão (CSC e teto do consumidor anônimo) de
    propósito: é aqui que o operador descobre o impedimento com a venda ainda
    aberta, em vez de no botão de emitir com o cliente esperando.
    """
    preview = preview_nfe_venda(db, venda_id, empresa_id)

    fiscal_settings = _obter_fiscal_settings(db, empresa_id)
    venda = crud.get_venda_completa(db, venda_id)

    # Aqui a consulta à plataforma cai bem: o preview existe justamente para o
    # problema aparecer com a tela aberta, e não no botão de emitir com o
    # cliente esperando no balcão.
    _assert_csc_configurado(
        get_fiscal_client(fiscal_settings.ambiente_emissao, crud.get_licenca_token(db))
    )
    _assert_consumidor_identificado(venda, fiscal_settings)

    documento = _documento_do_consumidor(venda)
    if venda.cliente is not None:
        pass  # o nome do cadastro já veio do preview da NF-e
    elif documento:
        preview["destinatario"] = {"nome": "CONSUMIDOR", "documento": documento}
    else:
        preview["destinatario"] = {
            "nome": "CONSUMIDOR NÃO IDENTIFICADO",
            "documento": "",
        }

    return preview


def emitir_nfe_venda(
    db: Session, venda_id: int, empresa_id: int,
    tentativa_anterior_id: Optional[int] = None,
) -> DocumentoFiscal:
    """
    Emite NF-e para uma venda.

    1. Verifica completude fiscal + calcula tributos (via _preparar_dados_emissao)
    2. Valida status da venda e bloqueio de duplicata
    3. Monta payload e cria DocumentoFiscal
    4. Chama client fiscal e atualiza resultado

    `tentativa_anterior_id` é o elo da reemissão (ver `reemissao.py`): o
    documento novo aponta para o rejeitado e o histórico mostra a cadeia. Fora
    isso a reemissão é IGUAL a uma emissão -- mesmo gate, número novo, mesma
    transmissão.
    """
    empresa, endereco, venda, simples, resultado_calculo = _preparar_dados_emissao(
        db, venda_id, empresa_id,
    )

    fiscal_settings = _obter_fiscal_settings(db, empresa_id)

    from app.core.enum import VendaStatus
    if venda.status != VendaStatus.FINALIZADA:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Apenas vendas finalizadas podem gerar NF-e.",
        )

    nota_fiscal = venda.nota_fiscal

    # Verificar emissão ativa existente (bloqueio de duplicata)
    doc_ativo = crud.get_documento_ativo_por_venda(db, venda.numero_venda)
    if doc_ativo:
        if doc_ativo.status == "AUTORIZADA":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "codigo": "NF_JA_AUTORIZADA",
                    "mensagem": f"Esta venda já possui NF-e autorizada (Nº {doc_ativo.numero_documento}, Série {doc_ativo.serie}).",
                    "documento_id": doc_ativo.id,
                    "chave_acesso": doc_ativo.chave_acesso,
                },
            )
        elif doc_ativo.status == "INDETERMINADA":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "codigo": "NF_INDETERMINADA",
                    "mensagem": (
                        "A emissão anterior desta venda não teve retorno confirmado da "
                        "SEFAZ. A nota pode estar autorizada. Consulte o documento antes "
                        "de emitir novamente para não gerar nota duplicada."
                    ),
                    "documento_id": doc_ativo.id,
                },
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "codigo": "NF_EM_PROCESSAMENTO",
                    "mensagem": "Esta venda já possui uma emissão em andamento. Aguarde o retorno da SEFAZ.",
                    "documento_id": doc_ativo.id,
                },
            )

    # 3. Reservar o número de forma atômica.
    #    Feito só agora, depois de todas as validações que podem recusar a
    #    emissão, para não queimar número à toa. A partir daqui o número é
    #    definitivo — ver passo 7.
    numero_venda = venda.numero_venda
    numero = crud.reservar_proximo_numero_nfe(db, empresa_id)

    # 4. Montar payload (com tributos calculados e o número já reservado)
    payload = montar_payload_nfe(
        empresa, endereco, fiscal_settings, venda, nota_fiscal,
        resultado_calculo=resultado_calculo,
        numero=numero,
    )

    # 5. Criar documento fiscal (ref e chave de idempotência únicas por tentativa)
    tentativas_existentes = crud.contar_documentos_por_venda(db, numero_venda)
    ref = f"venda-{numero_venda}" if tentativas_existentes == 0 else f"venda-{numero_venda}-{tentativas_existentes + 1}"

    doc = DocumentoFiscal(
        tipo_documento="NFE",
        origem_tipo="VENDA",
        origem_id=numero_venda,
        status="PROCESSANDO",
        numero_documento=numero,
        serie=fiscal_settings.serie_nfe,
        ref_api=ref,
        idempotency_key=str(uuid.uuid4()),
        ambiente_emissao=fiscal_settings.ambiente_emissao,
        valor_total=venda.total,
        data_emissao=datetime.now(timezone.utc),
        tentativa_anterior_id=tentativa_anterior_id,
    )
    # Congela o que vai ser transmitido, ANTES de transmitir: assim existe
    # registro mesmo se a resposta da SEFAZ se perder no caminho.
    gravar_snapshot(doc, payload, venda=venda)
    crud.salvar_documento(db, doc)

    # 6. Chamar client fiscal
    token = crud.get_licenca_token(db)
    client = get_fiscal_client(fiscal_settings.ambiente_emissao, token)

    try:
        resultado = client.emitir_nfe(ref, payload, idempotency_key=doc.idempotency_key)
        _aplicar_resultado(doc, resultado)
    except NotImplementedError as e:
        # Client sem implementação: nada foi transmitido, é recusa local.
        doc.status = "REJEITADA"
        doc.mensagem_sefaz = str(e)
    except Exception as e:
        # Falha de comunicação NÃO é rejeição: a nota pode estar autorizada na
        # SEFAZ. Marcar REJEITADA aqui libera a venda para nova emissão e gera
        # nota duplicada. O documento fica INDETERMINADA até ser reconciliado.
        logger.error("[FISCAL] Falha de comunicação ao emitir NF-e ref=%s: %s", ref, e)
        doc.status = "INDETERMINADA"
        doc.mensagem_sefaz = (
            f"Não foi possível confirmar o resultado junto à SEFAZ: {str(e)[:300]}. "
            f"O documento será reconsultado automaticamente."
        )

    # 7. O contador NÃO é revertido.
    #    Reverter parecia evitar buracos na sequência, mas depois que o payload
    #    já foi transmitido o número pode estar consumido na SEFAZ — reusá-lo
    #    causa Rejeição 204 e trava a sequência de vez. Buraco se resolve com
    #    inutilização; duplicidade, não.

    return doc


def _reais(centavos: int) -> str:
    """Centavos -> 'R$ 10.000,00'. Só para mensagem lida por gente."""
    inteiro, resto = divmod(int(centavos), 100)
    return f"R$ {inteiro:,.0f}".replace(",", ".") + f",{resto:02d}"


def _documento_do_consumidor(venda) -> Optional[str]:
    """CPF/CNPJ que identifica o comprador nesta venda, ou None.

    Precedência: o cadastro do cliente vence o digitado no caixa, porque foi
    conferido uma vez. O do caixa cobre o consumidor de passagem.
    """
    cliente = venda.cliente
    if cliente is not None:
        documento = getattr(cliente, "cpf", None) or getattr(cliente, "cnpj", None)
        if documento:
            return re.sub(r"\D", "", documento)

    nota = venda.nota_fiscal
    if nota is not None and nota.documento_consumidor:
        return re.sub(r"\D", "", nota.documento_consumidor)

    return None


def _assert_consumidor_identificado(venda, fiscal_settings: EmpresaFiscalSettings) -> None:
    """Regra 3: acima do teto estadual, a NFC-e exige CPF/CNPJ do comprador.

    A conferência é feita ANTES de reservar número — recusa depois queimaria
    um número da sequência e obrigaria a inutilizá-lo por um erro de digitação.
    """
    limite = fiscal_settings.limite_consumidor_anonimo or 0
    if limite <= 0 or (venda.total or 0) < limite:
        return

    if _documento_do_consumidor(venda):
        return

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "codigo": "CONSUMIDOR_NAO_IDENTIFICADO",
            "mensagem": (
                f"Vendas a partir de {_reais(limite)} exigem o CPF ou CNPJ do "
                f"comprador na NFC-e. Informe o documento no fechamento ou "
                f"emita uma NF-e."
            ),
            "limite_centavos": limite,
        },
    )


def _assert_csc_configurado(client) -> None:
    """
    Sem CSC não há QR Code, e sem QR Code o cupom não tem validade.

    QUEM RESPONDE É A PLATAFORMA, não um campo daqui. O CSC é cadastrado uma
    única vez na ficha da empresa dentro da Focus, junto do certificado A1 --
    nunca viajou no payload da nota. Perguntar ao nosso banco barraria uma loja
    corretamente configurada só porque o lojista não redigitou o segredo aqui.

    "Não sei" LIBERA. Se a consulta falhar, `consultar_config` devolve {} e a
    emissão segue: derrubar um cupom no balcão por causa de um diagnóstico
    indisponível troca a venda por um detalhe. O preço de errar para "tem" é um
    cupom sem QR Code, e esse a plataforma sinaliza em `pendencias`.

    Lembre que o CSC é POR AMBIENTE: o de homologação não vale em produção.
    """
    config = client.consultar_config()
    if config.get("cscConfigurado") is not False:
        return

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "codigo": "CSC_NAO_CONFIGURADO",
            "mensagem": (
                "O CSC (Código de Segurança do Contribuinte) não está "
                "cadastrado para esta empresa na emissora. Sem ele o cupom sai "
                "sem QR Code e não tem validade. Fale com o suporte para "
                "cadastrá-lo — e confirme o ambiente, porque o CSC de "
                "homologação não vale em produção."
            ),
        },
    )


def _completar_tributos_pelo_xml(doc: DocumentoFiscal, client) -> None:
    """Busca no XML autorizado o valor aproximado dos tributos (Lei 12.741).

    A Focus calcula o `vTotTrib` pela tabela IBPT, mas só o grava no XML — o
    JSON da emissão não o traz, e o cupom é obrigado a imprimi-lo. Este é o
    único jeito de ter o número sem manter tabela IBPT própria.

    É BEST-EFFORT de propósito. A nota já está autorizada quando chegamos
    aqui; falhar em baixar um arquivo não pode desfazer isso nem impedir a
    impressão. Sem o valor, o cupom sai sem a linha de tributos e o documento
    continua válido — e a reimpressão pode buscar de novo.
    """
    if doc.status != "AUTORIZADA" or doc.valor_tributos is not None:
        return
    if not doc.url_xml:
        return

    try:
        xml = client.baixar_xml(doc.url_xml)
    except Exception as exc:  # client sem o método, rede, o que for
        logger.warning("[FISCAL] Não foi possível baixar o XML da nota: %s", exc)
        return

    valor = extrair_valor_tributos(xml)
    if valor is None:
        logger.info(
            "[FISCAL] Documento %s sem vTotTrib no XML; cupom sai sem a linha "
            "de tributos aproximados.", doc.id,
        )
        return

    doc.valor_tributos = valor


def emitir_nfce_venda(
    db: Session, venda_id: int, empresa_id: int,
    tentativa_anterior_id: Optional[int] = None,
) -> DocumentoFiscal:
    """
    Emite NFC-e (modelo 65) para uma venda do PDV.

    Espelha `emitir_nfe_venda`, com quatro diferenças que importam:

    1. Exige CSC configurado e consumidor identificado acima do teto — as duas
       conferências acontecem ANTES de reservar número.
    2. Usa o contador de NFC-e, independente do de NF-e.
    3. É SÍNCRONA: não há polling. O caixa está com o cliente na frente.
    4. Bloqueia duplicata pelo documento ativo da venda, igual à NF-e — uma
       venda não pode ter NF-e e NFC-e ao mesmo tempo.

    O gate roda como "nfce", e isso é a quinta diferença: o modelo 65 omite o
    endereço do destinatário, então exigi-lo aqui reprovaria o cupom de todo
    consumidor de balcão — que é o caso normal do PDV.
    """
    empresa, endereco, venda, simples, resultado_calculo = _preparar_dados_emissao(
        db, venda_id, empresa_id, tipo_documento="nfce",
    )

    fiscal_settings = _obter_fiscal_settings(db, empresa_id)

    from app.core.enum import VendaStatus
    if venda.status != VendaStatus.FINALIZADA:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Apenas vendas finalizadas podem gerar NFC-e.",
        )

    # O client nasce AQUI, e não junto da emissão lá embaixo: a trava do CSC
    # pergunta à plataforma, e descobrir o problema depois de reservar o número
    # queimaria uma numeração à toa.
    token = crud.get_licenca_token(db)
    client = get_fiscal_client(fiscal_settings.ambiente_emissao, token)

    _assert_csc_configurado(client)
    _assert_consumidor_identificado(venda, fiscal_settings)

    # Bloqueio de duplicata — mesma regra e mesmas mensagens da NF-e.
    doc_ativo = crud.get_documento_ativo_por_venda(db, venda.numero_venda)
    if doc_ativo:
        if doc_ativo.status == "AUTORIZADA":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "codigo": "NF_JA_AUTORIZADA",
                    "mensagem": (
                        f"Esta venda já possui documento fiscal autorizado "
                        f"(Nº {doc_ativo.numero_documento}, Série {doc_ativo.serie})."
                    ),
                    "documento_id": doc_ativo.id,
                    "chave_acesso": doc_ativo.chave_acesso,
                },
            )
        if doc_ativo.status == "INDETERMINADA":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "codigo": "NF_INDETERMINADA",
                    "mensagem": (
                        "A emissão anterior desta venda não teve retorno confirmado da "
                        "SEFAZ. O documento pode estar autorizado. Consulte antes de "
                        "emitir novamente para não gerar cupom duplicado."
                    ),
                    "documento_id": doc_ativo.id,
                },
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "codigo": "NF_EM_PROCESSAMENTO",
                "mensagem": "Esta venda já possui uma emissão em andamento.",
                "documento_id": doc_ativo.id,
            },
        )

    # Número reservado só depois de todas as recusas possíveis.
    numero_venda = venda.numero_venda
    numero = crud.reservar_proximo_numero_nfce(db, empresa_id)

    payload = montar_payload_nfce(
        empresa, endereco, fiscal_settings, venda, venda.nota_fiscal,
        resultado_calculo=resultado_calculo,
        numero=numero,
    )

    tentativas_existentes = crud.contar_documentos_por_venda(db, numero_venda)
    ref = (
        f"nfce-{numero_venda}"
        if tentativas_existentes == 0
        else f"nfce-{numero_venda}-{tentativas_existentes + 1}"
    )

    doc = DocumentoFiscal(
        tipo_documento="NFCE",
        origem_tipo="VENDA",
        origem_id=numero_venda,
        status="PROCESSANDO",
        numero_documento=numero,
        serie=fiscal_settings.serie_nfce,
        ref_api=ref,
        idempotency_key=str(uuid.uuid4()),
        ambiente_emissao=fiscal_settings.ambiente_emissao,
        valor_total=venda.total,
        data_emissao=datetime.now(timezone.utc),
        tentativa_anterior_id=tentativa_anterior_id,
    )
    # Congela o que vai ser transmitido, ANTES de transmitir: assim existe
    # registro mesmo se a resposta da SEFAZ se perder no caminho.
    gravar_snapshot(doc, payload, venda=venda)
    crud.salvar_documento(db, doc)

    try:
        resultado = client.emitir_nfce(ref, payload, idempotency_key=doc.idempotency_key)
        _aplicar_resultado(doc, resultado)
    except NotImplementedError as e:
        doc.status = "REJEITADA"
        doc.mensagem_sefaz = str(e)
    except Exception as e:
        # Mesma razão da NF-e: falha de comunicação NÃO é rejeição. Marcar
        # REJEITADA liberaria a venda para nova emissão e geraria cupom
        # duplicado. Fica INDETERMINADA até a reconciliação resolver.
        logger.error("[FISCAL] Falha de comunicação ao emitir NFC-e ref=%s: %s", ref, e)
        doc.status = "INDETERMINADA"
        doc.mensagem_sefaz = (
            f"Não foi possível confirmar o resultado junto à SEFAZ: {str(e)[:300]}. "
            f"O documento será reconsultado automaticamente."
        )

    _completar_tributos_pelo_xml(doc, client)

    # Espelha na nota da venda o que a tela do PDV lê para imprimir o cupom.
    nota = venda.nota_fiscal
    if nota is not None:
        nota.status_nota = doc.status
        nota.chave_acesso = doc.chave_acesso
        nota.numero_nota = doc.numero_documento
        nota.serie = doc.serie
        nota.protocolo_autorizacao = doc.protocolo_autorizacao
        nota.data_autorizacao = doc.data_autorizacao
        nota.qrcode = doc.qrcode
        nota.mensagem_sefaz = doc.mensagem_sefaz

    # O contador NÃO é revertido — ver a nota em `emitir_nfe_venda`.
    return doc


def consultar_documento(db: Session, documento_id: int, empresa_id: int) -> DocumentoFiscal:
    """Polling: consulta status do documento na API e atualiza."""
    doc = crud.get_documento_fiscal(db, documento_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento fiscal não encontrado.")

    if not doc.ref_api:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Documento não possui referência de API para consulta.",
        )

    # Documento não transmitido não tem o que consultar. Ver STATUS_CONSULTAVEIS.
    if doc.status not in STATUS_CONSULTAVEIS:
        return doc

    fiscal_settings = _obter_fiscal_settings(db, empresa_id)
    token = crud.get_licenca_token(db)
    client = get_fiscal_client(fiscal_settings.ambiente_emissao, token)

    try:
        resultado = client.consultar_nfe(doc.ref_api, doc.tipo_documento)
        _aplicar_resultado(doc, resultado)
    except NotImplementedError:
        pass
    except Exception as e:
        logger.error("[FISCAL] Erro ao consultar doc=%d: %s", documento_id, e)

    return doc


import asyncio
from app.db.session import SessionLocal

async def poll_nfe_status_async(documento_id: int, empresa_id: int):
    """
    Realiza o polling assíncrono para a API StartBig.
    Tempo máximo: ~3 minutos.
    """
    intervals = [3, 5, 8, 12, 15, 20, 20, 20, 25, 25, 30]
    for wait_time in intervals:
        await asyncio.sleep(wait_time)

        db = SessionLocal()
        try:
            doc = consultar_documento(db, documento_id, empresa_id)
            db.commit()
            if doc.status not in STATUS_CONSULTAVEIS:
                break
        except Exception as e:
            db.rollback()
            logger.error("[FISCAL] Erro no polling background: %s", e)
        finally:
            db.close()


# Prazo legal para cancelamento, contado da autorização. O prazo é do MODELO,
# não do sistema: a NFC-e é muito mais curta porque o cliente sai da loja com a
# mercadoria — passado o prazo, a via é a nota de devolução.
JANELA_CANCELAMENTO_NFE = timedelta(hours=24)   # modelo 55
JANELA_CANCELAMENTO_NFCE = timedelta(minutes=30)  # modelo 65

JANELA_CANCELAMENTO_POR_TIPO = {
    "NFE": JANELA_CANCELAMENTO_NFE,
    "NFCE": JANELA_CANCELAMENTO_NFCE,
}


def _descrever_janela(janela: timedelta) -> str:
    """'24 horas' / '30 minutos' — para a mensagem que o operador lê."""
    if janela >= timedelta(hours=1):
        return f"{int(janela.total_seconds() // 3600)} horas"
    return f"{int(janela.total_seconds() // 60)} minutos"


def _descrever_decorrido(decorrido: timedelta) -> str:
    minutos = int(decorrido.total_seconds() // 60)
    if minutos < 60:
        return f"{minutos} minutos"
    return f"{minutos // 60} horas"


def _assert_dentro_da_janela_de_cancelamento(doc: DocumentoFiscal) -> None:
    """
    Barra cancelamento fora do prazo da SEFAZ.

    Sem isso o operador tenta cancelar, a SEFAZ recusa — e ele já devolveu o
    dinheiro ao cliente. Melhor recusar aqui e orientar a emitir devolução.
    """
    if not doc.data_autorizacao:
        return

    autorizacao = doc.data_autorizacao
    if autorizacao.tzinfo is None:
        autorizacao = autorizacao.replace(tzinfo=timezone.utc)

    # Tipo desconhecido cai no prazo mais CURTO: recusar um cancelamento que
    # ainda daria tempo é um aborrecimento; liberar um fora do prazo faz a
    # SEFAZ recusar depois de o caixa já ter devolvido o dinheiro.
    janela = JANELA_CANCELAMENTO_POR_TIPO.get(
        doc.tipo_documento, JANELA_CANCELAMENTO_NFCE,
    )

    decorrido = datetime.now(timezone.utc) - autorizacao
    if decorrido <= janela:
        return

    documento = "NFC-e" if doc.tipo_documento == "NFCE" else "NF-e"
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "codigo": "PRAZO_CANCELAMENTO_EXPIRADO",
            "mensagem": (
                f"O prazo de {_descrever_janela(janela)} para cancelar esta "
                f"{documento} expirou (autorizada há "
                f"{_descrever_decorrido(decorrido)}). Emita uma NF-e de "
                f"devolução para reverter a operação."
            ),
            "documento_id": doc.id,
        },
    )


def cancelar_documento(
    db: Session, documento_id: int, empresa_id: int, justificativa: str
) -> DocumentoFiscal:
    """Cancela documento fiscal autorizado, dentro do prazo legal."""
    doc = crud.get_documento_fiscal(db, documento_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento fiscal não encontrado.")

    if doc.status != "AUTORIZADA":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Apenas documentos autorizados podem ser cancelados.",
        )

    _assert_dentro_da_janela_de_cancelamento(doc)

    if not doc.ref_api:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Documento não possui referência de API para cancelamento.",
        )

    fiscal_settings = _obter_fiscal_settings(db, empresa_id)
    token = crud.get_licenca_token(db)
    client = get_fiscal_client(fiscal_settings.ambiente_emissao, token)

    try:
        resultado = client.cancelar_nfe(
            doc.ref_api, justificativa, doc.tipo_documento
        )
        _aplicar_resultado(doc, resultado)
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e),
        )
    except Exception as e:
        logger.error("[FISCAL] Erro ao cancelar doc=%d: %s", documento_id, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro de comunicação ao cancelar: {str(e)[:400]}",
        )

    return doc


def emitir_teste_nfe(db: Session, empresa_id: int) -> DocumentoFiscal:
    """
    Emissão de teste com dados fictícios. Apenas em homologação.
    Não precisa de venda ou OS real.
    """
    fiscal_settings = _obter_fiscal_settings(db, empresa_id)

    if fiscal_settings.ambiente_emissao != 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Emissão de teste só é permitida em ambiente de homologação.",
        )

    empresa = crud.get_empresa(db, empresa_id)
    endereco = crud.get_endereco_empresa(db, empresa_id)

    if not empresa or not endereco:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Empresa ou endereço não cadastrados.",
        )

    # O emitente precisa estar completo ANTES de reservar numeração.
    #
    # A emissão real passa por `_preparar_dados_emissao`, que já verifica isto.
    # A de teste não passava por nada: com CNPJ, IE ou regime tributário em
    # branco ela reservava o número, montava a nota, e a plataforma recusava com
    # 4xx antes de chegar na Focus. Como o corpo do 4xx vira `mensagem_sefaz`, o
    # lojista lia "CNPJ do emitente não autorizado" achando que era a SEFAZ
    # falando -- quando o dado faltava aqui e a nota nunca saiu da nossa rede.
    #
    # Verificar antes do `ultimo_numero_nfe + 1` também evita queimar numeração
    # à toa: a reversão existe, mas depende de o fluxo chegar até ela.
    from . import validators

    pendencias = validators.verificar_emitente(db, empresa_id)
    if pendencias:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "codigo": "EMITENTE_INCOMPLETO",
                "mensagem": (
                    "Os dados da empresa ainda não permitem emitir. "
                    "Complete-os em Dados da Empresa e tente de novo."
                ),
                "pendencias": [p.mensagem for p in pendencias],
            },
        )

    payload = montar_payload_teste_nfe(empresa, endereco, fiscal_settings)

    ref = f"teste-{uuid.uuid4().hex[:12]}"
    numero = fiscal_settings.ultimo_numero_nfe + 1

    doc = DocumentoFiscal(
        tipo_documento="NFE",
        origem_tipo="VENDA",
        status="PROCESSANDO",
        numero_documento=numero,
        serie=fiscal_settings.serie_nfe,
        ref_api=ref,
        ambiente_emissao=2,
        valor_total=100,  # R$ 1,00 em centavos
        data_emissao=datetime.now(timezone.utc),
    )
    
    fiscal_settings.ultimo_numero_nfe = numero
    crud.salvar_documento(db, doc)

    token = crud.get_licenca_token(db)
    client = get_fiscal_client(2, token)

    try:
        resultado = client.emitir_nfe(ref, payload)
        _aplicar_resultado(doc, resultado)
    except Exception as e:
        logger.error("[FISCAL] Erro ao emitir teste NF-e: %s", e)
        doc.status = "REJEITADA"
        doc.mensagem_sefaz = f"Erro no teste: {str(e)[:400]}"

    # Reverter numeração se emissão falhou
    if doc.status == "REJEITADA":
        fiscal_settings.ultimo_numero_nfe = numero - 1

    return doc


# ===========================================================================
# NF-e A PARTIR DE ORDEM DE SERVIÇO
#
# Só os itens de PRODUTO entram. Mão de obra é serviço e pede NFS-e municipal,
# que este sistema ainda não emite -- então a NF-e de uma OS cobre as peças, e
# quem precisa de documento da mão de obra continua dependendo da prefeitura.
#
# Todo o miolo (alíquotas, rateio, montagem, fechamento de pagamentos) é o
# MESMO da venda: a OS é apresentada com a forma de uma venda em
# `adaptador_os.py`. Ver lá o porquê de adaptar em vez de duplicar.
# ===========================================================================

def _preparar_dados_emissao_os(db: Session, numero_os: str, empresa_id: int):
    """Espelho de `_preparar_dados_emissao`, para OS.

    Returns:
        (empresa, endereco, os_obj, os_como_venda, simples, resultado_calculo)
    """
    from .adaptador_os import adaptar, itens_de_produto
    from .core import verificar_completude_os

    verificacao = verificar_completude_os(db, numero_os, empresa_id, tipo_documento="nfe")
    if not verificacao.completo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "mensagem": "Dados fiscais incompletos para emissão.",
                "pendencias": [p.model_dump() for p in verificacao.pendencias],
            },
        )

    empresa = crud.get_empresa(db, empresa_id)
    endereco = crud.get_endereco_empresa(db, empresa_id)
    os_obj = crud.get_os_completa(db, numero_os)
    if not os_obj:
        raise HTTPException(status_code=404, detail="Ordem de Serviço não encontrada.")

    if not itens_de_produto(os_obj):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Esta OS não tem peça aprovada para faturar. A NF-e cobre os "
                "produtos; a mão de obra é nota de serviço (NFS-e)."
            ),
        )

    os_como_venda = adaptar(os_obj)

    uf_emitente = endereco.estado.value if hasattr(endereco.estado, "value") else str(endereco.estado)
    simples = usa_csosn(obter_crt(empresa))

    try:
        itens_entrada, dados_nota = resolver_aliquotas_venda(
            db, os_como_venda, uf_emitente, simples,
            regime_apuracao=regime_apuracao(empresa),
        )
        resultado_calculo = calcular_impostos(itens_entrada, dados_nota)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[FISCAL] Erro no cálculo tributário da OS %s: %s", numero_os, e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erro no cálculo tributário: {str(e)}",
        )

    return empresa, endereco, os_obj, os_como_venda, simples, resultado_calculo


def preview_nfe_os(db: Session, numero_os: str, empresa_id: int) -> dict:
    """Pré-visualização da NF-e de uma OS. Não emite e NÃO reserva número."""
    empresa, endereco, os_obj, os_como_venda, _simples, resultado_calculo = (
        _preparar_dados_emissao_os(db, numero_os, empresa_id)
    )
    fiscal_settings = _obter_fiscal_settings(db, empresa_id)

    payload = montar_payload_nfe(
        empresa, endereco, fiscal_settings, os_como_venda, os_obj.nota_fiscal,
        resultado_calculo=resultado_calculo,
    )

    return {
        "numero_os": numero_os,
        "itens": payload.get("items", []),
        "totais": payload.get("totais", {}),
        "formas_pagamento": payload.get("formas_pagamento", []),
        "destinatario": payload.get("destinatario", {}),
    }


def emitir_nfe_os(
    db: Session, numero_os: str, empresa_id: int,
    tentativa_anterior_id: Optional[int] = None,
) -> DocumentoFiscal:
    """
    Emite NF-e para as peças de uma Ordem de Serviço.

    Segue passo a passo o `emitir_nfe_venda` -- inclusive na ordem: primeiro
    tudo que pode recusar, e só depois a reserva do número. Descobrir problema
    com o número já reservado queima numeração à toa, e buraco na sequência
    obriga inutilização junto à SEFAZ.
    """
    from app.core.enum import OrdemServicoStatus

    empresa, endereco, os_obj, os_como_venda, _simples, resultado_calculo = (
        _preparar_dados_emissao_os(db, numero_os, empresa_id)
    )
    fiscal_settings = _obter_fiscal_settings(db, empresa_id)

    if os_obj.status != OrdemServicoStatus.FINALIZADA:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Apenas ordens de serviço finalizadas podem gerar NF-e.",
        )

    doc_ativo = crud.get_documento_ativo_por_os(db, numero_os)
    if doc_ativo:
        if doc_ativo.status == "AUTORIZADA":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "codigo": "NF_JA_AUTORIZADA",
                    "mensagem": (
                        f"Esta OS já possui NF-e autorizada "
                        f"(Nº {doc_ativo.numero_documento}, Série {doc_ativo.serie})."
                    ),
                    "documento_id": doc_ativo.id,
                    "chave_acesso": doc_ativo.chave_acesso,
                },
            )
        if doc_ativo.status == "INDETERMINADA":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "codigo": "NF_INDETERMINADA",
                    "mensagem": (
                        "A emissão anterior desta OS não teve retorno confirmado da "
                        "SEFAZ. A nota pode estar autorizada. Consulte o documento "
                        "antes de emitir novamente para não gerar nota duplicada."
                    ),
                    "documento_id": doc_ativo.id,
                },
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "codigo": "NF_EM_PROCESSAMENTO",
                "mensagem": (
                    "Esta OS já possui uma emissão em andamento. "
                    "Aguarde o retorno da SEFAZ."
                ),
                "documento_id": doc_ativo.id,
            },
        )

    numero = crud.reservar_proximo_numero_nfe(db, empresa_id)

    payload = montar_payload_nfe(
        empresa, endereco, fiscal_settings, os_como_venda, os_obj.nota_fiscal,
        resultado_calculo=resultado_calculo,
        numero=numero,
    )

    tentativas = crud.contar_documentos_por_os(db, numero_os)
    ref_bruta = f"os-{numero_os}" if tentativas == 0 else f"os-{numero_os}-{tentativas + 1}"
    # A `ref` é a proteção contra duplicidade na plataforma, e o contrato aceita
    # só `A-Za-z0-9._-`. O número da OS vem formatado ("OS-2026-000001"), então
    # qualquer outro caractere é normalizado aqui em vez de virar 4xx lá.
    ref = re.sub(r"[^A-Za-z0-9._-]", "-", ref_bruta)[:50]

    doc = DocumentoFiscal(
        tipo_documento="NFE",
        origem_tipo="OS",
        origem_id=os_obj.id,
        origem_numero_os=numero_os,
        status="PROCESSANDO",
        numero_documento=numero,
        serie=fiscal_settings.serie_nfe,
        ref_api=ref,
        idempotency_key=str(uuid.uuid4()),
        ambiente_emissao=fiscal_settings.ambiente_emissao,
        # O valor do DOCUMENTO é o das peças, não o da OS: é ele que a SEFAZ
        # autoriza e o que o relatório fiscal soma.
        valor_total=os_como_venda.total,
        data_emissao=datetime.now(timezone.utc),
        tentativa_anterior_id=tentativa_anterior_id,
    )
    gravar_snapshot(doc, payload, venda=os_como_venda)
    crud.salvar_documento(db, doc)

    client = get_fiscal_client(
        fiscal_settings.ambiente_emissao, crud.get_licenca_token(db),
    )

    try:
        resultado = client.emitir_nfe(ref, payload, idempotency_key=doc.idempotency_key)
        _aplicar_resultado(doc, resultado)
    except NotImplementedError as e:
        doc.status = "REJEITADA"
        doc.mensagem_sefaz = str(e)
    except Exception as e:
        # Falha de comunicação NÃO é rejeição -- ver o mesmo trecho em
        # `emitir_nfe_venda`. REJEITADA seria reemitível e geraria duplicata.
        logger.error(
            "[FISCAL] Falha de comunicação ao emitir NF-e da OS ref=%s: %s", ref, e,
        )
        doc.status = "INDETERMINADA"
        doc.mensagem_sefaz = (
            f"Não foi possível confirmar o resultado junto à SEFAZ: {str(e)[:300]}. "
            f"O documento será reconsultado automaticamente."
        )

    return doc


def emitir_nfe_batch(
    db: Session, venda_ids: list[int], empresa_id: int
) -> list[dict]:
    """
    Emite NF-e para múltiplas vendas sequencialmente.
    Cada venda é atômica — falhas individuais não interrompem o lote.
    Commit-per-sale para preservar numeração fiscal.
    """
    resultados = []
    for venda_id in venda_ids:
        try:
            doc = emitir_nfe_venda(db, venda_id, empresa_id)
            db.commit()
            resultados.append({
                "venda_id": venda_id,
                "documento_id": doc.id,
                "status": doc.status,
                "mensagem": doc.mensagem_sefaz or f"NF-e {doc.status.lower()}.",
            })
        except HTTPException as e:
            db.rollback()
            mensagem = e.detail if isinstance(e.detail, str) else (
                e.detail.get("mensagem", str(e.detail))
                if isinstance(e.detail, dict) else str(e.detail)
            )
            resultados.append({
                "venda_id": venda_id,
                "documento_id": None,
                "status": "ERRO",
                "mensagem": mensagem,
            })
        except Exception as e:
            db.rollback()
            logger.error("[FISCAL] Erro batch venda_id=%d: %s", venda_id, e)
            resultados.append({
                "venda_id": venda_id,
                "documento_id": None,
                "status": "ERRO",
                "mensagem": f"Erro inesperado: {str(e)[:200]}",
            })
    return resultados


def obter_historico_tentativas(db: Session, documento_id: int) -> list[DocumentoFiscal]:
    """
    Retorna a cadeia completa de tentativas (do mais recente ao mais antigo).
    Segue a linked list via tentativa_anterior_id.
    """
    tentativas = []
    doc = crud.get_documento_fiscal(db, documento_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Documento fiscal não encontrado.")

    # Subir na cadeia: encontrar o documento mais recente que aponta para este
    doc_mais_recente = crud.get_documento_by_tentativa_anterior(db, documento_id)

    while doc_mais_recente:
        proximo = crud.get_documento_by_tentativa_anterior(db, doc_mais_recente.id)
        if proximo:
            doc_mais_recente = proximo
        else:
            break

    # Começar do mais recente (ou do documento pedido se não há mais recente)
    atual = doc_mais_recente or doc
    while atual:
        tentativas.append(atual)
        if atual.tentativa_anterior_id:
            atual = crud.get_documento_fiscal(db, atual.tentativa_anterior_id)
        else:
            break

    return tentativas
