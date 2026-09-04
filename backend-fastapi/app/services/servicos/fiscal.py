# ---------------------------------------------------------------------------
# ARQUIVO: app/services/servico/fiscal.py
# DESCRIÇÃO: Lógica de negócio para dados fiscais de serviços
# ---------------------------------------------------------------------------

from typing import Optional
from sqlalchemy.orm import Session

from app.db.crud import servico_fiscal as crud
from app.db.models.servico_fiscal import ServicoFiscal
from app.schemas.servico_fiscal import ServicoFiscalUpdate

def _validar_servico(db: Session, servico_id: int) -> int:
    from app.db.crud import servico as servico_crud
    
    servico = servico_crud.get_servico_by_id(db, servico_id)
    if not servico:
        from app.services.servicos._errors import not_found_exce
        raise not_found_exce
    
def get_dados_fiscais(db: Session, servico_id: int) -> Optional[ServicoFiscal]:
    """
    Retorna os dados fiscais do serviço ou None se ainda não foram preenchidos.
    Levanta 404 se o serviço não existir.
    """
    servico_id = _validar_servico(db, servico_id)
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