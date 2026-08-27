# app/services/verificacao_fiscal/crud.py
from sqlalchemy.orm import Session, joinedload, subqueryload
from app.db.models.empresa import Empresa
from app.db.models.empresa_fiscal_settings import EmpresaFiscalSettings
from app.db.models.endereco import Endereco
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
        joinedload(Venda.cliente),
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

def get_aliquota_uf(db: Session, uf: str):
    return db.query(AliquotaUF).filter(AliquotaUF.uf == uf.upper()).first()