# app/services/verificacao_fiscal/crud.py
from sqlalchemy.orm import Session, joinedload, subqueryload
from app.db.models.empresa import Empresa
from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings
from app.db.models.endereco import Endereco
from app.db.models.cliente import Cliente
from app.db.models.venda import Venda
from app.db.models.venda_pagamento import PagamentoVenda
from app.db.models.venda_produto import ProdutoVenda
from app.db.models.ordem_servico import OrdemServico
from app.db.models.ordem_servico_pagamento import OrdemServicoPagamento
from app.db.models.ordem_servico_item import OrdemServicoItem
from app.db.models.produto_fiscal import ProdutoFiscal
from app.db.models.servico_fiscal import ServicoFiscal
from app.core.enum import EntityType

def get_empresa(db: Session, empresa_id: int):
    return db.query(Empresa).filter(Empresa.id == empresa_id).first()

def get_endereco_empresa(db: Session, empresa_id: int):
    return db.query(Endereco).filter(
        Endereco.id_entidade == empresa_id,
        Endereco.tipo_entidade == EntityType.EMPRESA,
    ).first()

def get_fiscal_settings(db: Session, empresa_id: int):
    return db.query(EmpresaFiscalSettings).filter(
        EmpresaFiscalSettings.empresa_id == empresa_id
    ).first()

def get_produto_fiscal(db: Session, produto_id: int):
    return db.query(ProdutoFiscal).filter(ProdutoFiscal.produto_id == produto_id).first()

def get_servico_fiscal(db: Session, servico_id: int):
    return db.query(ServicoFiscal).filter(ServicoFiscal.servico_id == servico_id).first()

def get_venda_completa(db: Session, venda_id: int):
    return db.query(Venda).options(
        joinedload(Venda.cliente).subqueryload(Cliente.endereco),
        subqueryload(Venda.itens).joinedload(ProdutoVenda.produto),
        subqueryload(Venda.pagamentos).joinedload(PagamentoVenda.forma_pagamento),
    ).filter(Venda.id == venda_id).first()

def get_os_completa(db: Session, numero_os: str):
    from app.db.models.objeto_servico import ObjetoServico
    return db.query(OrdemServico).options(
        joinedload(OrdemServico.objeto).joinedload(ObjetoServico.cliente),
        subqueryload(OrdemServico.itens).joinedload(OrdemServicoItem.produtos),
        subqueryload(OrdemServico.itens).joinedload(OrdemServicoItem.servico),
        subqueryload(OrdemServico.pagamentos).joinedload(OrdemServicoPagamento.forma_pagamento),
        joinedload(OrdemServico.nota_fiscal),
    ).filter(OrdemServico.numero_os == numero_os).first()

from app.db.models.documento_fiscal import DocumentoFiscal
from app.db.models.configuracao_licenca import ConfiguracaoLicenca
from app.db.models.aliquota_uf import AliquotaUF

def get_licenca_token(db: Session) -> str:
    licenca = db.query(ConfiguracaoLicenca).first()
    return licenca.token if licenca else ""

def get_documento_fiscal(db: Session, documento_id: int):
    return db.query(DocumentoFiscal).filter(DocumentoFiscal.id == documento_id).first()

def get_documento_by_tentativa_anterior(db: Session, anterior_id: int):
    return db.query(DocumentoFiscal).filter(DocumentoFiscal.tentativa_anterior_id == anterior_id).first()

def salvar_documento(db: Session, documento: DocumentoFiscal):
    db.add(documento)
    db.flush()
    return documento

def get_documento_ativo_por_venda(db: Session, numero_venda: int):
    return db.query(DocumentoFiscal).filter(
        DocumentoFiscal.origem_tipo == "VENDA",
        DocumentoFiscal.origem_id == numero_venda,
        DocumentoFiscal.status.in_(["PROCESSANDO", "PENDENTE", "AUTORIZADA"]),
    ).first()

def get_documentos_ativos_por_vendas(db: Session, numeros_venda: list[int]) -> dict[int, DocumentoFiscal]:
    """Retorna {numero_venda: DocumentoFiscal} para docs ativos (PROCESSANDO/PENDENTE/AUTORIZADA)."""
    if not numeros_venda:
        return {}
    docs = db.query(DocumentoFiscal).filter(
        DocumentoFiscal.origem_tipo == "VENDA",
        DocumentoFiscal.origem_id.in_(numeros_venda),
        DocumentoFiscal.status.in_(["PROCESSANDO", "PENDENTE", "AUTORIZADA"]),
    ).all()
    return {doc.origem_id: doc for doc in docs}

def get_documentos_relevantes_por_vendas(db: Session, numeros_venda: list[int]) -> dict[int, DocumentoFiscal]:
    """Retorna {numero_venda: DocumentoFiscal} incluindo REJEITADA/DENEGADA (tudo exceto CANCELADA)."""
    if not numeros_venda:
        return {}
    docs = db.query(DocumentoFiscal).filter(
        DocumentoFiscal.origem_tipo == "VENDA",
        DocumentoFiscal.origem_id.in_(numeros_venda),
        DocumentoFiscal.status.in_(["PROCESSANDO", "PENDENTE", "AUTORIZADA", "REJEITADA", "DENEGADA"]),
    ).all()
    # Prioridade: AUTORIZADA > PROCESSANDO/PENDENTE > REJEITADA/DENEGADA
    resultado = {}
    prioridade = {"AUTORIZADA": 0, "PROCESSANDO": 1, "PENDENTE": 2, "REJEITADA": 3, "DENEGADA": 4}
    for doc in docs:
        existente = resultado.get(doc.origem_id)
        if not existente or prioridade.get(doc.status, 99) < prioridade.get(existente.status, 99):
            resultado[doc.origem_id] = doc
    return resultado

def get_vendas_completas_batch(db: Session, venda_ids: list[int]) -> list[Venda]:
    """Carrega vendas com cliente, itens e pagamentos em queries otimizadas."""
    if not venda_ids:
        return []
    return db.query(Venda).options(
        joinedload(Venda.cliente),
        subqueryload(Venda.itens).joinedload(ProdutoVenda.produto),
        subqueryload(Venda.pagamentos).joinedload(PagamentoVenda.forma_pagamento),
    ).filter(Venda.id.in_(venda_ids)).all()

def contar_documentos_por_venda(db: Session, numero_venda: int) -> int:
    from sqlalchemy import func
    return db.query(func.count(DocumentoFiscal.id)).filter(
        DocumentoFiscal.origem_tipo == "VENDA",
        DocumentoFiscal.origem_id == numero_venda,
    ).scalar() or 0

def get_nomes_destinatarios_por_vendas(db: Session, numeros_venda: list[int]) -> dict[int, str]:
    """Retorna {numero_venda: nome_destinatario} para uma lista de números de venda."""
    from app.db.models.cliente import Cliente, ClientePF, ClientePJ

    if not numeros_venda:
        return {}

    rows = (
        db.query(Venda.numero_venda, Venda.cliente_id, Cliente.tipo)
        .outerjoin(Cliente, Venda.cliente_id == Cliente.id)
        .filter(Venda.numero_venda.in_(numeros_venda))
        .all()
    )

    nomes: dict[int, str] = {}
    cliente_ids_pf: list[int] = []
    cliente_ids_pj: list[int] = []
    venda_por_cliente: dict[int, int] = {}

    for num_venda, cliente_id, tipo in rows:
        if not cliente_id:
            nomes[num_venda] = "Consumidor Final"
            continue
        venda_por_cliente[cliente_id] = num_venda
        if tipo and tipo.value == "PF":
            cliente_ids_pf.append(cliente_id)
        elif tipo and tipo.value == "PJ":
            cliente_ids_pj.append(cliente_id)
        else:
            nomes[num_venda] = "Consumidor Final"

    if cliente_ids_pf:
        pf_rows = db.query(ClientePF.id, ClientePF.nome).filter(ClientePF.id.in_(cliente_ids_pf)).all()
        for cid, nome in pf_rows:
            nomes[venda_por_cliente[cid]] = nome or "Consumidor Final"

    if cliente_ids_pj:
        pj_rows = db.query(ClientePJ.id, ClientePJ.razao_social).filter(ClientePJ.id.in_(cliente_ids_pj)).all()
        for cid, razao in pj_rows:
            nomes[venda_por_cliente[cid]] = razao or "Consumidor Final"

    return nomes

def get_aliquota_uf(db: Session, uf: str):
    return db.query(AliquotaUF).filter(AliquotaUF.uf == uf.upper()).first()