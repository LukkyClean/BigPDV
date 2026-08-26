# ---------------------------------------------------------------------------
# ARQUIVO: app/services/documento_fiscal.py
# DESCRIÇÃO: CRUD e consultas para documentos fiscais do Centro Fiscal.
# ---------------------------------------------------------------------------

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.documento_fiscal import DocumentoFiscal
from app.schemas.documento_fiscal import (
    DocumentoFiscalHistorico,
    DocumentoFiscalListRead,
    DocumentoFiscalRead,
    DocumentoFiscalResumo,
)


def listar_documentos(
    db: Session,
    *,
    status_filtro: Optional[str] = None,
    tipo: Optional[str] = None,
    origem: Optional[str] = None,
    busca: Optional[str] = None,
    data_inicio=None,
    data_fim=None,
    pagina: int = 1,
    por_pagina: int = 20,
) -> DocumentoFiscalListRead:
    query = db.query(DocumentoFiscal)

    if status_filtro:
        query = query.filter(DocumentoFiscal.status == status_filtro.upper())
    if tipo:
        query = query.filter(DocumentoFiscal.tipo_documento == tipo.upper())
    if origem:
        query = query.filter(DocumentoFiscal.origem_tipo == origem.upper())
    if busca:
        termo = f"%{busca}%"
        query = query.filter(
            (DocumentoFiscal.chave_acesso.ilike(termo))
            | (DocumentoFiscal.origem_numero_os.ilike(termo))
        )
    if data_inicio:
        query = query.filter(DocumentoFiscal.data_emissao >= data_inicio)
    if data_fim:
        query = query.filter(DocumentoFiscal.data_emissao <= data_fim)

    total = query.count()
    total_paginas = (total + por_pagina - 1) // por_pagina if total > 0 else 0

    items = (
        query.order_by(DocumentoFiscal.data_criacao.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )

    return DocumentoFiscalListRead(
        items=[DocumentoFiscalRead.model_validate(item) for item in items],
        total=total,
        pagina=pagina,
        paginas=total_paginas,
    )


def obter_documento(db: Session, documento_id: int) -> DocumentoFiscal:
    doc = db.query(DocumentoFiscal).filter(DocumentoFiscal.id == documento_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento fiscal não encontrado.",
        )
    return doc


def obter_resumo(db: Session) -> DocumentoFiscalResumo:
    resultados = (
        db.query(DocumentoFiscal.status, func.count(DocumentoFiscal.id))
        .group_by(DocumentoFiscal.status)
        .all()
    )

    contadores = {row[0]: row[1] for row in resultados}

    return DocumentoFiscalResumo(
        pendentes=contadores.get("PENDENTE", 0) + contadores.get("PROCESSANDO", 0),
        autorizadas=contadores.get("AUTORIZADA", 0),
        rejeitadas=contadores.get("REJEITADA", 0),
        canceladas=contadores.get("CANCELADA", 0) + contadores.get("DENEGADA", 0),
    )


def reemitir_documento(db: Session, documento_id: int) -> DocumentoFiscal:
    """Mantido para retrocompatibilidade — delega para emissao.reemitir_documento."""
    from app.services.fiscal.emissao import reemitir_documento as _reemitir
    doc = obter_documento(db, documento_id)

    if doc.status not in ("REJEITADA", "DENEGADA"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Apenas documentos rejeitados ou denegados podem ser reemitidos.",
        )

    # Extrair empresa_id do contexto (o caller já validou via requer_modulo_fiscal)
    # Como não temos empresa_id aqui, criamos a nova tentativa manualmente
    from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings
    import uuid

    novo_doc = DocumentoFiscal(
        tipo_documento=doc.tipo_documento,
        origem_tipo=doc.origem_tipo,
        origem_id=doc.origem_id,
        origem_numero_os=doc.origem_numero_os,
        status="PENDENTE",
        numero_documento=doc.numero_documento,
        serie=doc.serie,
        ref_api=f"doc-{uuid.uuid4().hex[:12]}",
        ambiente_emissao=doc.ambiente_emissao,
        valor_total=doc.valor_total,
        tentativa_anterior_id=doc.id,
    )
    db.add(novo_doc)
    db.flush()

    return novo_doc


def obter_historico_tentativas(db: Session, documento_id: int) -> DocumentoFiscalHistorico:
    """Retorna cadeia completa de tentativas (do mais recente ao mais antigo)."""
    from app.services.fiscal.emissao import obter_historico_tentativas as _historico

    tentativas_models = _historico(db, documento_id)
    tentativas = [DocumentoFiscalRead.model_validate(t) for t in tentativas_models]

    return DocumentoFiscalHistorico(
        tentativas=tentativas,
        total_tentativas=len(tentativas),
    )
