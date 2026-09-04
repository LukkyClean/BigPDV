# ---------------------------------------------------------------------------
# ARQUIVO: app/db/crud/ordem_servico_nota_fiscal.py
# DESCRIÇÃO: Operações CRUD para a tabela ordem_servico_nota_fiscal.
# ---------------------------------------------------------------------------

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.ordem_servico_nota_fiscal import OrdemServicoNotaFiscal
from app.schemas.ordem_servico_nota_fiscal import OrdemServicoNotaFiscalUpdate


def get_by_os_id(db: Session, os_id: int) -> Optional[OrdemServicoNotaFiscal]:
    return (
        db.query(OrdemServicoNotaFiscal)
        .filter(OrdemServicoNotaFiscal.os_id == os_id)
        .first()
    )


def create(
    db: Session, os_id: int, dados: OrdemServicoNotaFiscalUpdate
) -> OrdemServicoNotaFiscal:
    nota = OrdemServicoNotaFiscal(os_id=os_id, **dados.model_dump(exclude_unset=False))
    db.add(nota)
    db.flush()
    db.refresh(nota)
    return nota


def update(
    db: Session,
    nota: OrdemServicoNotaFiscal,
    dados: OrdemServicoNotaFiscalUpdate,
) -> OrdemServicoNotaFiscal:
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(nota, campo, valor)
    db.flush()
    db.refresh(nota)
    return nota


def upsert(
    db: Session, os_id: int, dados: OrdemServicoNotaFiscalUpdate
) -> OrdemServicoNotaFiscal:
    nota = get_by_os_id(db, os_id)
    if nota is None:
        return create(db, os_id, dados)
    return update(db, nota, dados)
