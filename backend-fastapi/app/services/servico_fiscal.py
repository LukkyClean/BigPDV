# ---------------------------------------------------------------------------
# ARQUIVO: app/services/servico_fiscal.py
# DESCRIÇÃO: Lógica de negócio para dados fiscais de serviço.
# ---------------------------------------------------------------------------

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.crud import servico_fiscal as crud
from app.db.models.servico_fiscal import ServicoFiscal
from app.db.models.servico import Servico
from app.schemas.servico_fiscal import ServicoFiscalUpdate

def _validar_servico(db: Session, servico_id: int) -> None:
    """Levanta 404 se o serviço não existir."""
    servico = db.query(Servico).filter(Servico.id == servico_id).first()
    if not servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")


def get_dados_fiscais(db: Session, servico_id: int) -> Optional[ServicoFiscal]:
    """
    Retorna os dados fiscais do serviço ou None se ainda não foram preenchidos.
    Levanta 404 se o serviço não existir.
    """
    _validar_servico(db, servico_id)
    return crud.get_by_servico_id(db, servico_id)


def upsert_dados_fiscais(
    db: Session,
    servico_id: int,
    dados: ServicoFiscalUpdate,
) -> ServicoFiscal:
    """
    Cria ou atualiza os dados fiscais do serviço.
    Levanta 404 se o serviço não existir.
    """
    _validar_servico(db, servico_id)
    return crud.upsert(db, servico_id, dados)
