# ---------------------------------------------------------------------------
# ARQUIVO: crud/empresa_crud.py
# MÓDULO: Acesso a Dados (Repository)
# DESCRIÇÃO: Queries SQL para a entidade Empresa.
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional

from app.db.models.empresa import Empresa as EmpresaModel

# ===========================================================================
# LEITURA (READ)
# ===========================================================================

def get_empresa_by_id(db: Session, empresa_id: int) -> Optional[EmpresaModel]:
    """
    Busca uma empresa pela Chave Primária (ID).

    Args:
        db (Session): Sessão de banco de dados ativa.
        empresa_id (int): O ID da empresa (PK).

    Returns:
        Optional[EmpresaModel]: O objeto EmpresaModel se encontrado, ou None.
    """
    stmt = select(EmpresaModel).where(EmpresaModel.id == empresa_id)
    return db.scalars(stmt).first()


def get_empresa_atual(db: Session) -> Optional[EmpresaModel]:
    """
    Retorna a empresa da instalação (aplicação single-tenant: existe uma
    única empresa criada no setup). Usada para descobrir o segmento de negócio.

    Returns:
        Optional[EmpresaModel]: A primeira/única empresa, ou None se ainda não houver setup.
    """
    stmt = select(EmpresaModel).order_by(EmpresaModel.id).limit(1)
    return db.scalars(stmt).first()

# ===========================================================================
# ESCRITA (CREATE)
# ===========================================================================

def create_empresa(db: Session, empresa_to_add: EmpresaModel) -> EmpresaModel:
    """
    Persiste a empresa no banco de dados.

    Args:
        db (Session): Sessão de banco de dados ativa.
        empresa_to_add (EmpresaModel): O objeto ORM de empresa a ser adicionado.

    Returns:
        EmpresaModel: O objeto EmpresaModel recém-criado, após refresh (com ID populado).
    """
    db.add(empresa_to_add)
    db.flush()
    db.refresh(empresa_to_add)
    return empresa_to_add

def update_empresa(db: Session, empresa_to_update: EmpresaModel) -> EmpresaModel:
    db.flush()
    db.refresh(empresa_to_update)
    return empresa_to_update
    
    
