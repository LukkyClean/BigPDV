# ---------------------------------------------------------------------------
# ARQUIVO: app/db/crud/venda_nota_fiscal.py
# DESCRIÇÃO: Operações CRUD para a tabela venda_nota_fiscal.
# ---------------------------------------------------------------------------

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.venda_nota_fiscal import VendaNotaFiscal
from app.schemas.venda_nota_fiscal import VendaNotaFiscalUpdate


def get_by_venda_id(db: Session, venda_id: int) -> Optional[VendaNotaFiscal]:
    return db.query(VendaNotaFiscal).filter(VendaNotaFiscal.venda_id == venda_id).first()


def create(db: Session, venda_id: int, dados: VendaNotaFiscalUpdate) -> VendaNotaFiscal:
    nota = VendaNotaFiscal(venda_id=venda_id, **dados.model_dump(exclude_unset=False))
    db.add(nota)
    db.flush()
    db.refresh(nota)
    return nota


def update(db: Session, nota: VendaNotaFiscal, dados: VendaNotaFiscalUpdate) -> VendaNotaFiscal:
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(nota, campo, valor)
    db.flush()
    db.refresh(nota)
    return nota


def upsert(db: Session, venda_id: int, dados: VendaNotaFiscalUpdate) -> VendaNotaFiscal:
    nota = get_by_venda_id(db, venda_id)
    if nota is None:
        return create(db, venda_id, dados)
    return update(db, nota, dados)
