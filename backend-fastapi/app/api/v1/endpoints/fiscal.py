# ---------------------------------------------------------------------------
# ARQUIVO: endpoints/fiscal.py
# DESCRIÇÃO: Endpoints do Centro Fiscal — documentos emitidos e pendências.
#
# Todos os endpoints exigem módulo fiscal ativo (EmpresaFiscalSettings).
# ---------------------------------------------------------------------------

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.depends import get_db, requer_modulo_fiscal, _handle_db_transaction
from app.schemas.documento_fiscal import (
    DocumentoFiscalListRead,
    DocumentoFiscalRead,
    DocumentoFiscalResumo,
    PendenciasGlobais,
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
# REEMISSÃO
# ===========================================================================

@router.post(
    "/documentos/{documento_id}/reemitir",
    response_model=DocumentoFiscalRead,
    summary="Reemitir Documento Fiscal",
    description=(
        "Reseta o status de um documento rejeitado/denegado para PENDENTE, "
        "permitindo nova tentativa de emissão."
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
