# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/emissao.py
# DESCRIÇÃO: Serviço de emissão de NF-e (venda e teste).
#
# Orquestra o fluxo: verificar → montar payload → chamar client → atualizar.
# Cada tentativa de emissão cria uma NOVA linha em documento_fiscal.
# Reemissões apontam para a tentativa anterior via tentativa_anterior_id.
# ---------------------------------------------------------------------------

import logging
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
from .helpers import is_simples_nacional
from .http import get_fiscal_client, EmissaoResultado
from .payload_builder import montar_payload_nfe, montar_payload_teste_nfe
from .tax_engine import calcular_impostos
from .tax_engine.resolver import resolver_aliquotas_venda

logger = logging.getLogger(__name__)


def _aplicar_resultado(doc: DocumentoFiscal, resultado: EmissaoResultado) -> None:
    """Atualiza DocumentoFiscal com o resultado da API."""
    status_api = resultado.get("status", "")

    if status_api == "autorizado":
        doc.status = "AUTORIZADA"
        doc.data_autorizacao = datetime.now(timezone.utc)
    elif status_api == "processando":
        doc.status = "PROCESSANDO"
    elif status_api == "cancelado":
        doc.status = "CANCELADA"
    else:
        doc.status = "REJEITADA"

    doc.chave_acesso = resultado.get("chave_acesso")
    doc.protocolo_autorizacao = resultado.get("protocolo")
    doc.url_pdf = resultado.get("url_pdf")
    doc.url_xml = resultado.get("url_xml")
    doc.codigo_status_sefaz = resultado.get("codigo_sefaz")
    doc.mensagem_sefaz = resultado.get("mensagem_sefaz")

    if resultado.get("numero"):
        doc.numero_documento = resultado["numero"]
    if resultado.get("serie"):
        doc.serie = resultado["serie"]


def _obter_fiscal_settings(db: Session, empresa_id: int) -> EmpresaFiscalSettings:
    fs = crud.get_fiscal_settings(db, empresa_id)
    if not fs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Configurações fiscais não cadastradas para esta empresa.",
        )
    return fs


def _preparar_dados_emissao(db: Session, venda_id: int, empresa_id: int):
    """
    Setup compartilhado entre preview e emissão.
    Verifica completude, carrega dados e calcula tributos.

    Returns:
        Tupla (empresa, endereco, venda, simples, resultado_calculo).

    Raises:
        HTTPException 422 se dados incompletos ou cálculo falhar.
        HTTPException 404 se venda não encontrada.
    """
    verificacao = verificar_completude_venda(db, venda_id, empresa_id)
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
    simples = is_simples_nacional(empresa.regime_tributario)

    try:
        itens_entrada, dados_nota = resolver_aliquotas_venda(
            db, venda, uf_emitente, simples,
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


def emitir_nfe_venda(db: Session, venda_id: int, empresa_id: int) -> DocumentoFiscal:
    """
    Emite NF-e para uma venda.

    1. Verifica completude fiscal + calcula tributos (via _preparar_dados_emissao)
    2. Valida status da venda e bloqueio de duplicata
    3. Monta payload e cria DocumentoFiscal
    4. Chama client fiscal e atualiza resultado
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
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "codigo": "NF_EM_PROCESSAMENTO",
                    "mensagem": "Esta venda já possui uma emissão em andamento. Aguarde o retorno da SEFAZ.",
                    "documento_id": doc_ativo.id,
                },
            )

    # 3. Montar payload (com tributos calculados)
    payload = montar_payload_nfe(
        empresa, endereco, fiscal_settings, venda, nota_fiscal,
        resultado_calculo=resultado_calculo,
    )

    # 4. Criar documento fiscal (ref única por tentativa)
    numero_venda = venda.numero_venda
    tentativas_existentes = crud.contar_documentos_por_venda(db, numero_venda)
    ref = f"venda-{numero_venda}" if tentativas_existentes == 0 else f"venda-{numero_venda}-{tentativas_existentes + 1}"
    numero = fiscal_settings.ultimo_numero_nfe + 1

    doc = DocumentoFiscal(
        tipo_documento="NFE",
        origem_tipo="VENDA",
        origem_id=numero_venda,
        status="PROCESSANDO",
        numero_documento=numero,
        serie=fiscal_settings.serie_nfe,
        ref_api=ref,
        ambiente_emissao=fiscal_settings.ambiente_emissao,
        valor_total=venda.total,
        data_emissao=datetime.now(timezone.utc),
    )
    # 5. Incrementar numeração (atômico na mesma transação)
    fiscal_settings.ultimo_numero_nfe = numero
    crud.salvar_documento(db, doc)

    # 6. Chamar client fiscal
    token = crud.get_licenca_token(db)
    client = get_fiscal_client(fiscal_settings.ambiente_emissao, token)

    try:
        resultado = client.emitir_nfe(ref, payload)
        _aplicar_resultado(doc, resultado)
    except NotImplementedError as e:
        doc.status = "REJEITADA"
        doc.mensagem_sefaz = str(e)
    except Exception as e:
        logger.error("[FISCAL] Erro ao emitir NF-e ref=%s: %s", ref, e)
        doc.status = "REJEITADA"
        doc.mensagem_sefaz = f"Erro de comunicação: {str(e)[:400]}"

    # 7. Reverter numeração se emissão falhou (evita gaps na sequência)
    if doc.status == "REJEITADA":
        fiscal_settings.ultimo_numero_nfe = numero - 1

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

    if doc.status not in ("PROCESSANDO", "PENDENTE"):
        return doc

    fiscal_settings = _obter_fiscal_settings(db, empresa_id)
    token = crud.get_licenca_token(db)
    client = get_fiscal_client(fiscal_settings.ambiente_emissao, token)

    try:
        resultado = client.consultar_nfe(doc.ref_api)
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
            if doc.status not in ("PROCESSANDO", "PENDENTE"):
                break
        except Exception as e:
            db.rollback()
            logger.error("[FISCAL] Erro no polling background: %s", e)
        finally:
            db.close()


def cancelar_documento(
    db: Session, documento_id: int, empresa_id: int, justificativa: str
) -> DocumentoFiscal:
    """Cancela documento fiscal autorizado."""
    doc = crud.get_documento_fiscal(db, documento_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento fiscal não encontrado.")

    if doc.status != "AUTORIZADA":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Apenas documentos autorizados podem ser cancelados.",
        )

    if not doc.ref_api:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Documento não possui referência de API para cancelamento.",
        )

    fiscal_settings = _obter_fiscal_settings(db, empresa_id)
    token = crud.get_licenca_token(db)
    client = get_fiscal_client(fiscal_settings.ambiente_emissao, token)

    try:
        resultado = client.cancelar_nfe(doc.ref_api, justificativa)
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


def reemitir_documento(db: Session, documento_id: int, empresa_id: int) -> DocumentoFiscal:
    """
    Cria NOVA linha DocumentoFiscal apontando para a tentativa anterior.
    O documento anterior mantém seu status original (REJEITADA/DENEGADA).
    O novo documento inicia como PENDENTE para nova tentativa.
    """
    doc_anterior = crud.get_documento_fiscal(db, documento_id)
    if not doc_anterior:
        raise HTTPException(status_code=404, detail="Documento fiscal não encontrado.")

    if doc_anterior.status not in ("REJEITADA", "DENEGADA"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Apenas documentos rejeitados ou denegados podem ser reemitidos.",
        )

    # Limitar retentativas (máx 5)
    MAX_RETENTATIVAS = 5
    tentativas = 0
    doc_chain = doc_anterior
    while doc_chain and doc_chain.tentativa_anterior_id:
        tentativas += 1
        doc_chain = crud.get_documento_fiscal(db, doc_chain.tentativa_anterior_id)
    if tentativas >= MAX_RETENTATIVAS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Limite de {MAX_RETENTATIVAS} retentativas atingido para este documento.",
        )

    fiscal_settings = _obter_fiscal_settings(db, empresa_id)
    ref = f"venda-{doc_anterior.origem_id}-retry-{doc_anterior.id}"

    novo_doc = DocumentoFiscal(
        tipo_documento=doc_anterior.tipo_documento,
        origem_tipo=doc_anterior.origem_tipo,
        origem_id=doc_anterior.origem_id,
        origem_numero_os=doc_anterior.origem_numero_os,
        status="PENDENTE",
        numero_documento=doc_anterior.numero_documento,
        serie=doc_anterior.serie,
        ref_api=ref,
        ambiente_emissao=fiscal_settings.ambiente_emissao,
        valor_total=doc_anterior.valor_total,
        tentativa_anterior_id=doc_anterior.id,
        data_emissao=datetime.now(timezone.utc),
    )
    crud.salvar_documento(db, novo_doc)

    return novo_doc


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
