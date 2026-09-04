# ---------------------------------------------------------------------------
# ARQUIVO: app/services/ordem_servico_nota_fiscal.py
# DESCRIÇÃO: Lógica de negócio para nota fiscal por OS.
# ---------------------------------------------------------------------------

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.crud import ordem_servico as os_crud
from app.db.crud import ordem_servico_nota_fiscal as crud
from app.db.models.ordem_servico_nota_fiscal import OrdemServicoNotaFiscal
from app.schemas.ordem_servico_nota_fiscal import OrdemServicoNotaFiscalUpdate


def _get_os_id_or_raise(db: Session, numero_os: str) -> int:
    os = os_crud.get_ordem_servico_by_numero_os(db, numero_os)
    if os is None:
        raise HTTPException(status_code=404, detail="Ordem de Serviço não encontrada")
    return os.id


def get_dados_fiscais(db: Session, numero_os: str) -> Optional[OrdemServicoNotaFiscal]:
    os_id = _get_os_id_or_raise(db, numero_os)
    return crud.get_by_os_id(db, os_id)


def upsert_dados_fiscais(
    db: Session, numero_os: str, dados: OrdemServicoNotaFiscalUpdate
) -> OrdemServicoNotaFiscal:
    os_id = _get_os_id_or_raise(db, numero_os)
    return crud.upsert(db, os_id, dados)
