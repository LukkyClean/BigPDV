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
    doc = obter_documento(db, documento_id)

    if doc.status not in ("REJEITADA", "DENEGADA"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Apenas documentos rejeitados ou denegados podem ser reemitidos.",
        )

    doc.status = "PENDENTE"
    doc.mensagem_sefaz = None
    doc.motivo_rejeicao = None
    doc.codigo_status_sefaz = None

    return doc
