# ---------------------------------------------------------------------------
# ARQUIVO: endpoints/fiscal.py
# DESCRIÇÃO: Endpoints do Centro Fiscal — documentos emitidos, pendências
#            e emissão de NF-e (real e teste/homologação).
#
# Todos os endpoints exigem módulo fiscal ativo (EmpresaFiscalSettings).
# ---------------------------------------------------------------------------

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.depends import get_db, requer_modulo_fiscal, _handle_db_transaction
from app.db.crud import fiscal as fiscal_crud
from app.schemas.documento_fiscal import (
    DocumentoFiscalHistorico,
    DocumentoFiscalListRead,
    DocumentoFiscalRead,
    DocumentoFiscalResumo,
    PendenciasGlobais,
)
from app.schemas.emissao_fiscal import (
    CancelamentoRequest,
    EmissaoBatchResponse,
    EmissaoNFeBatchRequest,
    EmissaoNFeRequest,
    EmissaoResponse,
    FiscalConfiguracao,
)
from app.services import documento_fiscal as documento_fiscal_service
from app.services import pendencias_globais as pendencias_globais_service

router = APIRouter()


# ===========================================================================
# RESUMO (contadores por status)
# ===========================================================================

@router.get(
    "/resumo",
    response_model=DocumentoFiscalResumo,
    summary="Resumo de Documentos Fiscais",
    description="Retorna contadores operacionais agrupados por status.",
)
def obter_resumo(
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
):
    return documento_fiscal_service.obter_resumo(db)


# ===========================================================================
# PENDÊNCIAS GLOBAIS
# ===========================================================================

@router.get(
    "/pendencias",
    response_model=PendenciasGlobais,
    summary="Pendências Fiscais Globais",
    description=(
        "Retorna pendências cadastrais que impedem emissão fiscal: "
        "produtos sem NCM, serviços sem código LC 116, pagamentos sem código SEFAZ "
        "e dados do emitente incompletos."
    ),
)
def obter_pendencias(
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
):
    empresa_id = user_token["empresa_id"]
    return pendencias_globais_service.obter_pendencias_globais(db, empresa_id)


# ===========================================================================
# LISTAGEM DE DOCUMENTOS
# ===========================================================================

@router.get(
    "/documentos",
    response_model=DocumentoFiscalListRead,
    summary="Listar Documentos Fiscais",
    description="Retorna lista paginada de documentos fiscais com filtros.",
)
def listar_documentos(
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
    status_filtro: Optional[str] = Query(None, alias="status", description="Filtrar por status"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo (NFE, NFCE, NFSE)"),
    origem: Optional[str] = Query(None, description="Filtrar por origem (VENDA, ORDEM_SERVICO)"),
    busca: Optional[str] = Query(None, description="Busca por chave de acesso ou número OS"),
    data_inicio: Optional[date] = Query(None, description="Data início (YYYY-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Data fim (YYYY-MM-DD)"),
    pagina: int = Query(1, ge=1, description="Número da página"),
    por_pagina: int = Query(20, ge=1, le=100, description="Itens por página"),
):
    return documento_fiscal_service.listar_documentos(
        db,
        status_filtro=status_filtro,
        tipo=tipo,
        origem=origem,
        busca=busca,
        data_inicio=data_inicio,
        data_fim=data_fim,
        pagina=pagina,
        por_pagina=por_pagina,
    )


# ===========================================================================
# DETALHE DO DOCUMENTO
# ===========================================================================

@router.get(
    "/documentos/{documento_id}",
    response_model=DocumentoFiscalRead,
    summary="Detalhe do Documento Fiscal",
    description="Retorna os dados completos de um documento fiscal.",
)
def obter_documento(
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
    documento_id: int = Path(..., ge=1, description="ID do documento fiscal"),
):
    return documento_fiscal_service.obter_documento(db, documento_id)


# ===========================================================================
# REEMISSÃO (cria nova tentativa — linked list)
# ===========================================================================

@router.post(
    "/documentos/{documento_id}/reemitir",
    response_model=DocumentoFiscalRead,
    summary="Reemitir Documento Fiscal",
    description=(
        "Cria nova tentativa de emissão a partir de um documento rejeitado/denegado. "
        "O documento original mantém seu status; o novo inicia como PENDENTE "
        "com tentativa_anterior_id apontando para o original."
    ),
)
def reemitir_documento(
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
    documento_id: int = Path(..., ge=1, description="ID do documento fiscal"),
):
    return _handle_db_transaction(
        db,
        documento_fiscal_service.reemitir_documento,
        documento_id,
    )


# ===========================================================================
# EMISSÃO DE NF-e
# ===========================================================================

from fastapi import BackgroundTasks
from app.schemas.emissao_fiscal import EmissaoPreviewResponse

@router.post(
    "/preview/nfe",
    response_model=EmissaoPreviewResponse,
    summary="Pré-visualizar NF-e",
    description="Gera um resumo da NF-e para visualização e verificação antes da emissão.",
)
def preview_nfe(
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
    payload: EmissaoNFeRequest = Body(...),
):
    from app.services.fiscal.emissao import preview_nfe_venda
    # FIXME: no futuro deve suportar preview_nfe_os também
    if payload.venda_id:
        return preview_nfe_venda(db, payload.venda_id, user_token["empresa_id"])
    raise HTTPException(status_code=400, detail="Somente pre-visualização de vendas está implementada")

@router.post(
    "/emitir/nfe",
    response_model=EmissaoResponse,
    summary="Emitir NF-e",
    description="Emite NF-e a partir de uma venda ou OS (apenas itens de produto).",
)
def emitir_nfe(
    background_tasks: BackgroundTasks,
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
    payload: EmissaoNFeRequest = Body(...),
):
    from app.services.fiscal.emissao import emitir_nfe_venda, poll_nfe_status_async

    empresa_id = user_token["empresa_id"]

    if payload.venda_id:
        doc = _handle_db_transaction(
            db, emitir_nfe_venda, payload.venda_id, empresa_id,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Emissão de NF-e para OS será implementada em fase futura.",
        )

    if doc.status == "PROCESSANDO":
        background_tasks.add_task(poll_nfe_status_async, doc.id, empresa_id)

    return EmissaoResponse(
        documento_id=doc.id,
        ref_api=doc.ref_api,
        status=doc.status,
        mensagem=doc.mensagem_sefaz or f"NF-e {doc.status.lower()}.",
        ambiente=doc.ambiente_emissao or 2,
    )


@router.post(
    "/emitir/nfe/batch",
    response_model=EmissaoBatchResponse,
    summary="Emitir NF-e em Lote",
    description="Emite NF-e para múltiplas vendas sequencialmente. Máximo 20 vendas por lote.",
)
def emitir_nfe_batch(
    background_tasks: BackgroundTasks,
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
    payload: EmissaoNFeBatchRequest = Body(...),
):
    from app.services.fiscal.emissao import emitir_nfe_batch as _emitir_batch, poll_nfe_status_async

    empresa_id = user_token["empresa_id"]
    resultados = _emitir_batch(db, payload.venda_ids, empresa_id)

    for r in resultados:
        if r["status"] == "PROCESSANDO" and r["documento_id"]:
            background_tasks.add_task(poll_nfe_status_async, r["documento_id"], empresa_id)

    sucesso = sum(1 for r in resultados if r["status"] not in ("ERRO", "REJEITADA"))
    return EmissaoBatchResponse(
        resultados=resultados,
        total=len(resultados),
        sucesso=sucesso,
        falha=len(resultados) - sucesso,
    )


@router.post(
    "/emitir/teste/nfe",
    response_model=EmissaoResponse,
    summary="Emitir NF-e de Teste",
    description=(
        "Emite NF-e com dados fictícios no ambiente de homologação. "
        "Apenas disponível quando ambiente_emissao = 2 (Homologação)."
    ),
)
def emitir_teste_nfe(
    background_tasks: BackgroundTasks,
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
):
    from app.services.fiscal.emissao import emitir_teste_nfe as _emitir_teste, poll_nfe_status_async

    empresa_id = user_token["empresa_id"]
    doc = _handle_db_transaction(db, _emitir_teste, empresa_id)

    if doc.status == "PROCESSANDO":
        background_tasks.add_task(poll_nfe_status_async, doc.id, empresa_id)

    return EmissaoResponse(
        documento_id=doc.id,
        ref_api=doc.ref_api,
        status=doc.status,
        mensagem=doc.mensagem_sefaz or f"NF-e de teste {doc.status.lower()}.",
        ambiente=2,
    )


# ===========================================================================
# CONSULTA (polling de status na API)
# ===========================================================================

@router.get(
    "/documentos/{documento_id}/consultar",
    response_model=DocumentoFiscalRead,
    summary="Consultar Status do Documento",
    description="Consulta o status atualizado do documento na API de emissão.",
)
def consultar_documento(
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
    documento_id: int = Path(..., ge=1, description="ID do documento fiscal"),
):
    from app.services.fiscal.emissao import consultar_documento as _consultar

    empresa_id = user_token["empresa_id"]
    return _handle_db_transaction(
        db, _consultar, documento_id, empresa_id,
    )


# ===========================================================================
# CANCELAMENTO
# ===========================================================================

@router.post(
    "/documentos/{documento_id}/cancelar",
    response_model=DocumentoFiscalRead,
    summary="Cancelar Documento Fiscal",
    description="Solicita cancelamento de documento autorizado (justificativa mínima: 15 caracteres).",
)
def cancelar_documento(
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
    documento_id: int = Path(..., ge=1, description="ID do documento fiscal"),
    payload: CancelamentoRequest = Body(...),
):
    from app.services.fiscal.emissao import cancelar_documento as _cancelar

    empresa_id = user_token["empresa_id"]
    return _handle_db_transaction(
        db,
        _cancelar,
        documento_id,
        empresa_id,
        payload.justificativa,
    )


# ===========================================================================
# HISTÓRICO DE TENTATIVAS
# ===========================================================================

@router.get(
    "/documentos/{documento_id}/historico",
    response_model=DocumentoFiscalHistorico,
    summary="Histórico de Tentativas",
    description="Retorna a cadeia completa de tentativas de emissão (do mais recente ao mais antigo).",
)
def obter_historico(
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
    documento_id: int = Path(..., ge=1, description="ID do documento fiscal"),
):
    return documento_fiscal_service.obter_historico_tentativas(db, documento_id)


# ===========================================================================
# CONFIGURAÇÃO DO AMBIENTE FISCAL
# ===========================================================================

@router.get(
    "/configuracao",
    response_model=FiscalConfiguracao,
    summary="Configuração Fiscal",
    description="Retorna o ambiente atual (homologação/produção) e status do módulo.",
)
def obter_configuracao(
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
):
    empresa_id = user_token["empresa_id"]
    fs = fiscal_crud.get_fiscal_settings(db, empresa_id)

    ambiente = fs.ambiente_emissao if fs else 2
    cert_configurado = bool(
        fs and (fs.certificado_digital_path or fs.certificado_thumbprint or fs.tipo_certificado == "NUVEM" or fs.certificado_status == "CONECTADO_NUVEM")
    )
    cert_valido = bool(
        cert_configurado and fs.certificado_validade and fs.certificado_validade.replace(tzinfo=None) > datetime.now()
    )

    return FiscalConfiguracao(
        ambiente=ambiente,
        ambiente_label="Homologação" if ambiente == 2 else "Produção",
        mock_ativo=settings.FISCAL_MOCK_ENABLED or ambiente == 2,
        certificado_configurado=cert_configurado,
        certificado_valido=cert_valido,
        certificado_status=fs.certificado_status if fs else None,
        certificado_cnpj=fs.certificado_cnpj if fs else None,
        serie_nfe=fs.serie_nfe if fs else 1,
        ultimo_numero_nfe=fs.ultimo_numero_nfe if fs else 0,
        serie_nfce=fs.serie_nfce if fs else 1,
        ultimo_numero_nfce=fs.ultimo_numero_nfce if fs else 0,
        csc_token=fs.csc_token if fs else None,
        csc_id=fs.csc_id if fs else None,
    )

from app.schemas.empresa import FiscalSettingsUpdate
from app.services.empresa import update_fiscal_settings, upload_certificado_focus
from fastapi import UploadFile, File, Form

@router.put(
    "/configuracao",
    response_model=FiscalConfiguracao,
    summary="Atualizar Configuração Fiscal",
    description="Atualiza configurações fiscais da empresa.",
)
def atualizar_configuracao(
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
    payload: FiscalSettingsUpdate = Body(...)
):
    empresa_id = user_token["empresa_id"]
    fs = update_fiscal_settings(db, empresa_id, payload)
    
    ambiente = fs.ambiente_emissao if fs else 2
    cert_configurado = bool(
        fs and (fs.certificado_digital_path or fs.certificado_thumbprint or fs.tipo_certificado == "NUVEM" or fs.certificado_status == "CONECTADO_NUVEM")
    )
    cert_valido = bool(
        cert_configurado and fs.certificado_validade and fs.certificado_validade.replace(tzinfo=None) > datetime.now()
    )

    return FiscalConfiguracao(
        ambiente=ambiente,
        ambiente_label="Homologação" if ambiente == 2 else "Produção",
        mock_ativo=settings.FISCAL_MOCK_ENABLED or ambiente == 2,
        certificado_configurado=cert_configurado,
        certificado_valido=cert_valido,
        certificado_status=fs.certificado_status if fs else None,
        certificado_cnpj=fs.certificado_cnpj if fs else None,
        serie_nfe=fs.serie_nfe if fs else 1,
        ultimo_numero_nfe=fs.ultimo_numero_nfe if fs else 0,
        serie_nfce=fs.serie_nfce if fs else 1,
        ultimo_numero_nfce=fs.ultimo_numero_nfce if fs else 0,
        csc_token=fs.csc_token if fs else None,
        csc_id=fs.csc_id if fs else None,
    )

@router.post(
    "/certificado/upload-focus",
    summary="Upload de Certificado para a Nuvem",
    description="Envia o certificado para a API da Focus NFe (simulado) e atualiza o status."
)
def upload_certificado_focus_endpoint(
    user_token: dict = Depends(requer_modulo_fiscal),
    *,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    senha: str = Form(...)
):
    empresa_id = user_token["empresa_id"]
    upload_certificado_focus(db, empresa_id, file, senha)
    return {"message": "Certificado enviado e configurado com sucesso."}
