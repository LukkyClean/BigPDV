# ---------------------------------------------------------------------------
# ARQUIVO: app/services/documento_fiscal.py
# DESCRIÇÃO: CRUD e consultas para documentos fiscais do Centro Fiscal.
# ---------------------------------------------------------------------------

from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.documento_fiscal import DocumentoFiscal
from app.db.models.venda import Venda
from app.db.models.cliente import Cliente, ClientePF, ClientePJ
from app.db.crud import fiscal as fiscal_crud
from app.schemas.documento_fiscal import (
    DocumentoFiscalHistorico,
    DocumentoFiscalListRead,
    DocumentoFiscalRead,
    DocumentoFiscalResumo,
    DocumentoItemResumo,
)


def _hidratar_documento_com_venda(db: Session, doc: DocumentoFiscal) -> DocumentoFiscalRead:
    """Hidrata DocumentoFiscalRead com dados enriquecidos de venda, cliente e itens."""
    doc_read = DocumentoFiscalRead.model_validate(doc)

    if doc.origem_tipo == "VENDA" and doc.origem_id is not None:
        venda = (
            db.query(Venda)
            .filter(Venda.numero_venda == doc.origem_id)
            .first()
        )
        if not venda:
            venda = db.query(Venda).filter(Venda.id == doc.origem_id).first()

        if venda:
            doc_read.venda_id = venda.id
            if venda.cliente_id:
                doc_read.destinatario_id = venda.cliente_id
                cliente = db.query(Cliente).filter(Cliente.id == venda.cliente_id).first()
                if cliente:
                    if cliente.tipo and cliente.tipo.value == "PF":
                        pf = db.query(ClientePF).filter(ClientePF.id == cliente.id).first()
                        if pf:
                            doc_read.destinatario_nome = pf.nome
                            doc_read.destinatario_documento = pf.cpf
                    elif cliente.tipo and cliente.tipo.value == "PJ":
                        pj = db.query(ClientePJ).filter(ClientePJ.id == cliente.id).first()
                        if pj:
                            doc_read.destinatario_nome = pj.razao_social or pj.nome_fantasia
                            doc_read.destinatario_documento = pj.cnpj

                    end = cliente.endereco[0] if isinstance(cliente.endereco, list) and cliente.endereco else (cliente.endereco if hasattr(cliente.endereco, "estado") else None)
                    if end:
                        doc_read.destinatario_uf = (
                            end.estado.value
                            if hasattr(end.estado, "value")
                            else str(end.estado)
                        )
                        doc_read.destinatario_municipio = end.cidade
            else:
                doc_read.destinatario_nome = "Consumidor Final"

            # Itens da venda para conferência fiscal
            itens_list = []
            for item in venda.itens:
                ncm = None
                cfop = None
                cod_barras = None
                nome_prod = item.descricao_avulsa or (item.produto.nome if item.produto else "Item")
                if item.produto:
                    cod_barras = item.produto.codigo_barras
                    if item.produto.fiscal:
                        ncm = item.produto.fiscal.ncm
                        cfop = item.produto.fiscal.cfop_padrao

                itens_list.append(
                    DocumentoItemResumo(
                        id=item.id,
                        produto_id=item.produto_id,
                        nome=nome_prod,
                        codigo_barras=cod_barras,
                        quantidade=item.quantidade,
                        valor_unitario=item.valor_unitario,
                        subtotal=item.subtotal,
                        desconto=item.desconto or 0,
                        ncm=ncm,
                        cfop=cfop,
                    )
                )
            doc_read.itens_resumo = itens_list

    return doc_read


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

    docs = [_hidratar_documento_com_venda(db, item) for item in items]

    return DocumentoFiscalListRead(
        items=docs,
        total=total,
        pagina=pagina,
        paginas=total_paginas,
    )


def obter_documento(db: Session, documento_id: int) -> DocumentoFiscalRead:
    doc = db.query(DocumentoFiscal).filter(DocumentoFiscal.id == documento_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento fiscal não encontrado.",
        )
    return _hidratar_documento_com_venda(db, doc)


def obter_resumo(db: Session, tipo: Optional[str] = None) -> DocumentoFiscalResumo:
    """Contadores por status, opcionalmente restritos a um tipo de documento.

    O `tipo` existe para as telas por modelo (NF-e, NFC-e): sem ele a tela da
    NFC-e mostraria também as NF-e nos cartões, e o lojista leria "3 rejeitadas"
    achando que são cupons quando são notas de outro modelo.
    """
    consulta = db.query(DocumentoFiscal.status, func.count(DocumentoFiscal.id))
    if tipo:
        consulta = consulta.filter(DocumentoFiscal.tipo_documento == tipo)

    resultados = consulta.group_by(DocumentoFiscal.status).all()

    contadores = {row[0]: row[1] for row in resultados}

    return DocumentoFiscalResumo(
        pendentes=contadores.get("PENDENTE", 0) + contadores.get("PROCESSANDO", 0),
        autorizadas=contadores.get("AUTORIZADA", 0),
        rejeitadas=contadores.get("REJEITADA", 0),
        canceladas=contadores.get("CANCELADA", 0) + contadores.get("DENEGADA", 0),
    )


def reemitir_documento(db: Session, documento_id: int) -> DocumentoFiscal:
    """Cria nova tentativa de emissão encadeada para um documento rejeitado/denegado."""
    doc = db.query(DocumentoFiscal).filter(DocumentoFiscal.id == documento_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento fiscal não encontrado.",
        )

    if doc.status not in ("REJEITADA", "DENEGADA"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Apenas documentos rejeitados ou denegados podem ser reemitidos.",
        )

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
    """Retorna cadeia completa de tentativas (do mais recente ao mais antigo) hidratada."""
    from app.services.fiscal.emissao import obter_historico_tentativas as _historico

    tentativas_models = _historico(db, documento_id)
    tentativas = [_hidratar_documento_com_venda(db, t) for t in tentativas_models]

    return DocumentoFiscalHistorico(
        tentativas=tentativas,
        total_tentativas=len(tentativas),
    )
