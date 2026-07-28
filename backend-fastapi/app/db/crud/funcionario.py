# ---------------------------------------------------------------------------
# ARQUIVO: crud/funcionario_crud.py
# MÓDULO: Acesso a Dados (Repository)
# DESCRIÇÃO: Queries SQL para Funcionários.
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from sqlalchemy import select, or_, and_
from typing import Sequence, Callable, Optional

from app.db.models.funcionario import Funcionario as FuncionarioModel

# ===========================================================================
# VERIFICAÇÕES (AUXILIARES)
# ===========================================================================

def verify_funcionario_conflict(
    db: Session,
    funcionario_id: Optional[int],
    value: str,
    search_method: Callable[[Session, str], FuncionarioModel | None],
    search_name: str
) -> str | None:
    """Verifica duplicidade de campos únicos."""
    if not value:
        return None

    funcionario_in_db = search_method(db, value)

    # Nenhum registro com esse valor: não há conflito.
    # (Precisa vir ANTES de acessar .id — senão, ao editar e enviar um valor
    #  único inédito, o None.id derrubava o update com 500.)
    if not funcionario_in_db:
        return None

    # O valor pertence ao próprio funcionário sendo editado: não é conflito.
    if funcionario_id and funcionario_in_db.id == funcionario_id:
        return None

    if not funcionario_in_db.ativo:
        return "disabled funcionario"

    formated_search = search_name.replace("_", " ")
    return f"{formated_search.upper()} já cadastrado"

# ===========================================================================
# LEITURA (READ)
# ===========================================================================

def get_funcionario_by_id(db: Session, funcionario_id: int) -> FuncionarioModel | None:
    """Busca por ID (PK)."""
    stmt = select(FuncionarioModel).where(FuncionarioModel.id == funcionario_id)
    return db.scalars(stmt).first()

def get_funcionario_by_user_id(db: Session, user_id: int) -> FuncionarioModel | None:
    """Busca por ID de Usuário (1:1)."""
    stmt = select(FuncionarioModel).where(FuncionarioModel.usuario_id == user_id)
    return db.scalars(stmt).first()

def get_funcionario_by_cpf(db: Session, funcionario_cpf: str) -> FuncionarioModel | None:
    stmt = select(FuncionarioModel).where(FuncionarioModel.cpf == funcionario_cpf)
    return db.scalars(stmt).first()

def get_funcionario_by_email(db: Session, funcionario_email: str) -> FuncionarioModel | None:
    stmt = select(FuncionarioModel).where(FuncionarioModel.email == funcionario_email)
    return db.scalars(stmt).first()

def get_funcionario_by_rg(db: Session, funcionario_rg: str) -> FuncionarioModel | None:
    stmt = select(FuncionarioModel).where(FuncionarioModel.rg == funcionario_rg)
    return db.scalars(stmt).first()

def get_funcionario_by_ctps(db: Session, funcionario_ctps: str) -> FuncionarioModel | None:
    stmt = select(FuncionarioModel).where(FuncionarioModel.carteira_trabalho == funcionario_ctps)
    return db.scalars(stmt).first()

def get_funcionario_by_cnh(db: Session, funcionario_cnh: str) -> FuncionarioModel | None:
    stmt = select(FuncionarioModel).where(FuncionarioModel.cnh == funcionario_cnh)
    return db.scalars(stmt).first()

def get_funcionario_by_search(db: Session, search: str | None) -> Sequence[FuncionarioModel]:
    """
    Busca funcionários ativos.
    CORREÇÃO APLICADA: Uso de .is_(True) e lógica de 'search' corrigida.
    """
    
    # 1. Se NÃO tem termo de busca, traz todos os ativos
    if not search:
        stmt = select(FuncionarioModel)
        # .where(FuncionarioModel.ativo.is_(True))
        
    # 2. Se TEM termo, filtra por campos chave
    else:
        conditions = or_(
            FuncionarioModel.nome.ilike(f"%{search}%"),
            FuncionarioModel.cpf.startswith(search),
            FuncionarioModel.email.ilike(f"%{search}%"),
            FuncionarioModel.rg.startswith(search)
        )

        stmt = select(FuncionarioModel).where(
            and_(
                # FuncionarioModel.ativo.is_(True), # Correção do erro de operador
                conditions
            )
        )
        
    return db.scalars(stmt).all()

# ===========================================================================
# ESCRITA (CREATE / UPDATE)
# ===========================================================================

def create_funcionario(db: Session, funcionario_to_add: FuncionarioModel) -> FuncionarioModel:
    """Persiste novo funcionário."""
    db.add(funcionario_to_add)
    db.flush()
    db.refresh(funcionario_to_add)
    return funcionario_to_add

def update_funcionario_in_db(db: Session, funcionario_to_update: FuncionarioModel) -> FuncionarioModel:
    """Persiste alterações."""
    db.flush()
    db.refresh(funcionario_to_update)
    return funcionario_to_update