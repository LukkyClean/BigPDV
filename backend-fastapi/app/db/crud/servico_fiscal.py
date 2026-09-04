# ---------------------------------------------------------------------------
# ARQUIVO: app/db/crud/servico_fiscal.py
# DESCRIÇÃO: Operações de banco de dados para dados fiscais de serviço.
# ---------------------------------------------------------------------------

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.servico_fiscal import ServicoFiscal
from app.schemas.servico_fiscal import ServicoFiscalCreate, ServicoFiscalUpdate


def get_by_servico_id(db: Session, servico_id: int) -> Optional[ServicoFiscal]:
    """Retorna o registro fiscal do serviço ou None se não existir."""
    return db.query(ServicoFiscal).filter(ServicoFiscal.servico_id == servico_id).first()


def create(db: Session, servico_id: int, dados: ServicoFiscalCreate) -> ServicoFiscal:
    """Cria um novo registro fiscal para o serviço."""
    registro = ServicoFiscal(servico_id=servico_id, **dados.model_dump(exclude_unset=False))
    db.add(registro)
    db.flush()
    db.refresh(registro)
    return registro


def update(db: Session, registro: ServicoFiscal, dados: ServicoFiscalUpdate) -> ServicoFiscal:
    """Atualiza um registro fiscal existente."""
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(registro, campo, valor)
    db.flush()
    db.refresh(registro)
    return registro


def upsert(db: Session, servico_id: int, dados: ServicoFiscalUpdate) -> ServicoFiscal:
    """Cria ou atualiza os dados fiscais do serviço (upsert)."""
    registro = get_by_servico_id(db, servico_id)
    if registro is None:
        return create(db, servico_id, ServicoFiscalCreate(**dados.model_dump()))
    return update(db, registro, dados)
