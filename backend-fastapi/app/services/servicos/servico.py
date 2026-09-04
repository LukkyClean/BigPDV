# ---------------------------------------------------------------------------
# ARQUIVO: app/services/servico/servico.py
# MÓDULO: Regras de Negócio (Service Layer)
# DESCRIÇÃO: Orquestra validações, verificação de conflitos e persistência
#            para operações relacionadas a Serviços
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session

# Schemas Pydantic (para validação de entrada e saída)
from app.schemas.servico import ServicoCreate, ServicoUpdate, ServicoQuery, ServicoStats
# Modelo SQLAlchemy (para mapeamento do DB)
from app.db.models.servico import Servico as ServicoModel
# Camada CRUD (para acesso direto ao DB)
from app.db.crud import servico as servico_crud

# Importa exceções globalmente definidas no módulo
from ._errors import not_found_exce, conflict_exce

SERVICE_URL = 'servicos/'

# ===========================================================================
# LÓGICA DE CRIAÇÃO (CREATE)
# ===========================================================================

def create_servico(db: Session, servico_to_add: ServicoCreate) -> ServicoModel:
    """
    Aplica regras de negócio para criação de um Serviço.
    
    1. Verifica conflito de unicidade (Descrição).
    2. Instancia o modelo ORM.
    3. Persiste o serviço através do CRUD.
    """
    # Verifica se já existe serviço com a mesma descrição
    servico_in_db = servico_crud.get_servico_by_description(db, description_to_search=servico_to_add.descricao)
    if servico_in_db:
        raise conflict_exce
        
    # Prepara os dados ignorando campos não definidos
    servico_data = servico_to_add.model_dump(exclude_unset=True)
    servico_to_db = ServicoModel(**servico_data)
    
    return servico_crud.create_servico(db, servico_to_add=servico_to_db)

# ===========================================================================
# LÓGICA DE LEITURA (READ)
# ===========================================================================

def get_servico_by_search(db: Session, filters: dict, page: int, limit: int) -> ServicoQuery:
    """
    Intermediário para busca de serviços.
    Repassa a query string para o CRUD realizar a filtragem.
    """
    # Quantidades de Elementos Desnecessários
    skip = (page - 1) * limit
    
    (servicos_in_db, total_items) = servico_crud.get_servico_by_search(db, filters=filters, skip=skip, limit=limit)
    
    total_pages = (
        # Retorna total_items // limit se resto = 0
        total_items // limit
        if total_items % limit == 0 
        # Caso contrário, retorna resultado + 1
        else total_items // limit + 1
    )
    
    # Trata os valores para não aparecer "None" na URL
    search_val = filters.get('search') if filters.get('search') is not None else ""
    active_val = filters.get('active') if filters.get('active') is not None else ""
    
    links = {
        "next": f"{SERVICE_URL}?page={page + 1}&limit={limit}&search={search_val}&active={active_val}" if page < total_pages else None,
        "prev": f"{SERVICE_URL}?page={page - 1}&limit={limit}&search={search_val}&active={active_val}" if page > 1 else None
    }
    
    servicos_query = ServicoQuery(
        filters=filters,
        items=servicos_in_db,
        total_items=total_items,
        page=page,
        limit=limit,
        total_pages=total_pages,
        links=links,
    )
    
    return servicos_query

def get_servico_stats(db: Session) -> ServicoStats:
    """Retorna estatísticas agregadas dos serviços."""
    stats_data = servico_crud.get_servico_stats(db)
    return ServicoStats(**stats_data)

# ===========================================================================
# LÓGICA DE ATUALIZAÇÃO (UPDATE)
# ===========================================================================

def update_servico_by_id(db: Session, servico_id: int, servico_to_update: ServicoUpdate) -> ServicoModel:
    """
    Atualiza dados de um serviço existente.
    
    1. Verifica se o serviço existe.
    2. Garante que a nova descrição (se houver) não gere conflito com outro serviço.
    3. Atualiza dinamicamente os atributos do objeto.
    """
    # 1. Busca o serviço atual
    servico_in_db = servico_crud.get_servico_by_id(db, servico_id=servico_id)
    if not servico_in_db:
       raise not_found_exce
       
    # 2. Verifica conflito de descrição (caso esteja sendo alterada)
    if servico_to_update.descricao:
        potential_conflict = servico_crud.get_servico_by_description(db, servico_to_update.descricao)
        if potential_conflict and potential_conflict.id != servico_id: 
            raise conflict_exce
            
    data_update = servico_to_update.model_dump(exclude_unset=True)
    
    # 3. Atualiza dinamicamente os atributos do objeto SQLAlchemy
    for key, value in data_update.items():
        setattr(servico_in_db, key, value)
        
    # 4. Delega para o CRUD
    return servico_crud.update_servico(db, servico_in_db)

# ===========================================================================
# LÓGICA DE STATUS (TOGGLE)
# ===========================================================================

def toggle_active_disable_servico_by_id(db: Session, servico_id: int) -> ServicoModel:
    """
    Inverte o status 'ativo' do serviço (True <-> False).
    Útil para soft-delete ou reativação.
    """
    servico_in_db = servico_crud.get_servico_by_id(db, servico_id=servico_id)
    if not servico_in_db:
        raise not_found_exce
        
    servico_in_db.ativo = not servico_in_db.ativo
    return servico_crud.update_servico(db, servico_to_update=servico_in_db)