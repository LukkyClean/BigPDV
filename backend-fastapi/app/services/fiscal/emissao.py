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
from datetime import datetime
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


def _gerar_ref_api() -> str:
    """Gera referência única para a API de emissão."""
    return f"doc-{uuid.uuid4().hex[:12]}"


def _aplicar_resultado(doc: DocumentoFiscal, resultado: EmissaoResultado) -> None:
    """Atualiza DocumentoFiscal com o resultado da API."""
    status_api = resultado.get("status", "")

    if status_api == "autorizado":
        doc.status = "AUTORIZADA"
        doc.data_autorizacao = datetime.now()
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


def emitir_nfe_venda(db: Session, venda_id: int, empresa_id: int) -> DocumentoFiscal:
    """
    Emite NF-e para uma venda.

    1. Verifica completude fiscal
    2. Monta payload
    3. Cria DocumentoFiscal com status PROCESSANDO
    4. Incrementa numeração
    5. Chama client fiscal
    6. Atualiza DocumentoFiscal com resultado
    """
    # 1. Verificar completude
    verificacao = verificar_completude_venda(db, venda_id, empresa_id)
    if not verificacao.completo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "mensagem": "Dados fiscais incompletos para emissão.",
                "pendencias": [p.model_dump() for p in verificacao.pendencias],
            },
        )

    # 2. Obter dados
    fiscal_settings = _obter_fiscal_settings(db, empresa_id)
    empresa = crud.get_empresa(db, empresa_id)
    endereco = crud.get_endereco_empresa(db, empresa_id)
    venda = crud.get_venda_completa(db, venda_id)

    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada.")

    nota_fiscal = venda.nota_fiscal

    # 2.5. Calcular tributos via FiscalTaxEngine
    uf_emitente = endereco.estado.value if hasattr(endereco.estado, "value") else str(endereco.estado)
    simples = is_simples_nacional(empresa.regime_tributario)
    resultado_calculo = None

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

    # 3. Montar payload (com tributos calculados)
    payload = montar_payload_nfe(
        empresa, endereco, fiscal_settings, venda, nota_fiscal,
        resultado_calculo=resultado_calculo,
    )

    # 4. Criar documento fiscal
    ref = _gerar_ref_api()
    numero = fiscal_settings.ultimo_numero_nfe + 1

    doc = DocumentoFiscal(
        tipo_documento="NFE",
        origem_tipo="VENDA",
        origem_id=venda_id,
        status="PROCESSANDO",
        numero_documento=numero,
        serie=fiscal_settings.serie_nfe,
        ref_api=ref,
        ambiente_emissao=fiscal_settings.ambiente_emissao,
        valor_total=venda.total,
        data_emissao=datetime.now(),
    )
    db.add(doc)

    # 5. Incrementar numeração (atômico na mesma transação)
    fiscal_settings.ultimo_numero_nfe = numero

    db.flush()

    # 6. Chamar client fiscal
    client = get_fiscal_client(fiscal_settings.ambiente_emissao)

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

    return doc


def consultar_documento(db: Session, documento_id: int, empresa_id: int) -> DocumentoFiscal:
    """Polling: consulta status do documento na API e atualiza."""
    doc = db.query(DocumentoFiscal).filter(DocumentoFiscal.id == documento_id).first()
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
    client = get_fiscal_client(fiscal_settings.ambiente_emissao)

    try:
        resultado = client.consultar_nfe(doc.ref_api)
        _aplicar_resultado(doc, resultado)
    except NotImplementedError:
        pass
    except Exception as e:
        logger.error("[FISCAL] Erro ao consultar doc=%d: %s", documento_id, e)

    return doc


def cancelar_documento(
    db: Session, documento_id: int, empresa_id: int, justificativa: str
) -> DocumentoFiscal:
    """Cancela documento fiscal autorizado."""
    doc = db.query(DocumentoFiscal).filter(DocumentoFiscal.id == documento_id).first()
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
    client = get_fiscal_client(fiscal_settings.ambiente_emissao)

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
    doc_anterior = db.query(DocumentoFiscal).filter(DocumentoFiscal.id == documento_id).first()
    if not doc_anterior:
        raise HTTPException(status_code=404, detail="Documento fiscal não encontrado.")

    if doc_anterior.status not in ("REJEITADA", "DENEGADA"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Apenas documentos rejeitados ou denegados podem ser reemitidos.",
        )

    fiscal_settings = _obter_fiscal_settings(db, empresa_id)
    ref = _gerar_ref_api()

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
        data_emissao=datetime.now(),
    )
    db.add(novo_doc)
    db.flush()

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

    ref = _gerar_ref_api()
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
        data_emissao=datetime.now(),
    )
    db.add(doc)

    fiscal_settings.ultimo_numero_nfe = numero
    db.flush()

    client = get_fiscal_client(2)

    try:
        resultado = client.emitir_nfe(ref, payload)
        _aplicar_resultado(doc, resultado)
    except Exception as e:
        logger.error("[FISCAL] Erro ao emitir teste NF-e: %s", e)
        doc.status = "REJEITADA"
        doc.mensagem_sefaz = f"Erro no teste: {str(e)[:400]}"

    return doc


def obter_historico_tentativas(db: Session, documento_id: int) -> list[DocumentoFiscal]:
    """
    Retorna a cadeia completa de tentativas (do mais recente ao mais antigo).
    Segue a linked list via tentativa_anterior_id.
    """
    tentativas = []
    doc = db.query(DocumentoFiscal).filter(DocumentoFiscal.id == documento_id).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Documento fiscal não encontrado.")

    # Subir na cadeia: encontrar o documento mais recente que aponta para este
    doc_mais_recente = db.query(DocumentoFiscal).filter(
        DocumentoFiscal.tentativa_anterior_id == documento_id
    ).first()

    while doc_mais_recente:
        proximo = db.query(DocumentoFiscal).filter(
            DocumentoFiscal.tentativa_anterior_id == doc_mais_recente.id
        ).first()
        if proximo:
            doc_mais_recente = proximo
        else:
            break

    # Começar do mais recente (ou do documento pedido se não há mais recente)
    atual = doc_mais_recente or doc
    while atual:
        tentativas.append(atual)
        if atual.tentativa_anterior_id:
            atual = db.query(DocumentoFiscal).filter(
                DocumentoFiscal.id == atual.tentativa_anterior_id
            ).first()
        else:
            break

    return tentativas
