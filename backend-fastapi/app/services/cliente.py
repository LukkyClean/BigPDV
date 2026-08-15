# ---------------------------------------------------------------------------
# ARQUIVO: cliente_service.py
# MÓDULO: Regras de Negócio (Service Layer)
# DESCRIÇÃO: Orquestra validações, verificação de conflitos e persistência.
# ---------------------------------------------------------------------------

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.cliente import Cliente as ClienteModel, ClientePF as ClientePFModel, ClientePJ as ClientePJModel
from app.schemas.cliente import ClienteSimpleRead, ClienteUpdate, ClientePFCreate, ClientePJCreate
from app.db.crud import cliente as cliente_crud
from app.services import endereco as address_service
from app.core.enum import Gender, EntityType

# ===========================================================================
# EXCEÇÕES REUTILIZÁVEIS
# ===========================================================================

not_found_exce = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Cliente não encontrado no sistema"
)

def conflito_dados_exce(mensagem: str):
    """Lança erro 409 para conflitos simples."""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=mensagem
    )

def validation_exce(errors: list):
    """Lança erro 409 com uma lista detalhada de campos com erro."""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=errors
    )

# ===========================================================================
# CONFIGURAÇÃO DE VALIDAÇÃO (Campos Únicos)
# ===========================================================================

VALIDATORS_MAP = {
    "cpf": cliente_crud.get_cliente_by_cpf,
    "cnpj": cliente_crud.get_cliente_by_cnpj,
    "rg": cliente_crud.get_cliente_by_rg,
    "ie": cliente_crud.get_cliente_by_ie,
    "email": cliente_crud.get_cliente_by_email,
}

FIELD_LABELS = {
    "cpf": "CPF",
    "cnpj": "CNPJ",
    "rg": "RG",
    "ie": "Inscrição Estadual",
    "email": "E-mail",
}

# ===========================================================================
# HELPERS PRIVADOS
# ===========================================================================

def _validar_unicidade_cliente(db: Session, data_dict: dict, cliente_id: int | None = None):
    """Varre o VALIDATORS_MAP para checar conflitos de CPF, CNPJ, etc."""
    validation_errors = []

    for field, search_method in VALIDATORS_MAP.items():
        value = data_dict.get(field)
        if value:
            error = cliente_crud.verify_cliente_conflict(
                db=db,
                value=value,
                search_method=search_method,
                search_name=FIELD_LABELS[field],
                cliente_id=cliente_id,
            )
            if error:
                if error == "disabled cliente":
                    raise conflito_dados_exce(
                        f"Existe um cadastro desativado com este {FIELD_LABELS[field]}. Por favor, reative-o."
                    )
                validation_errors.append({"campo": field, "mensagem": error})

    if validation_errors:
        raise validation_exce(validation_errors)

def _get_cliente_or_raise(db: Session, cliente_id: int) -> ClienteModel:
    """Busca um cliente no banco. Se não existir, lança 404."""
    cliente_in_db = cliente_crud.get_cliente_by_id(db, cliente_id)
    if not cliente_in_db:
        raise not_found_exce
    return cliente_in_db


def get_cliente_by_id(db: Session, cliente_id: int) -> ClienteModel:
    """Retorna o cadastro completo (PF/PJ) do cliente pelo ID; 404 se não existir."""
    return _get_cliente_or_raise(db, cliente_id)

# ===========================================================================
# LÓGICA DE CRIAÇÃO (CREATE)
# ===========================================================================

def create_cliente_pf(db: Session, data: ClientePFCreate) -> ClientePFModel:
    """Aplica regras de negócio para criação de Pessoa Física."""
    cliente_data = data.model_dump(exclude={"endereco"})
    _validar_unicidade_cliente(db, cliente_data)

    novo_cliente = ClientePFModel(**cliente_data)
    cliente_in_db = cliente_crud.create_cliente(db, cliente_to_add=novo_cliente)

    if data.endereco:
        endereco_models = address_service.address_to_db(
            id_entity=cliente_in_db.id,
            type_entity=EntityType.CLIENTE,
            address_data=data.endereco,
        )
        for end in endereco_models:
            db.add(end)
        db.flush()

    return cliente_in_db


def create_cliente_pj(db: Session, data: ClientePJCreate) -> ClientePJModel:
    """Aplica regras de negócio para criação de Pessoa Jurídica."""
    cliente_data = data.model_dump(exclude={"endereco"})
    _validar_unicidade_cliente(db, cliente_data)

    novo_cliente = ClientePJModel(**cliente_data)
    cliente_in_db = cliente_crud.create_cliente(db, cliente_to_add=novo_cliente)

    if data.endereco:
        endereco_models = address_service.address_to_db(
            id_entity=cliente_in_db.id,
            type_entity=EntityType.CLIENTE,
            address_data=data.endereco,
        )
        for end in endereco_models:
            db.add(end)
        db.flush()

    return cliente_in_db

# ===========================================================================
# LÓGICA DE LEITURA (READ)
# ===========================================================================

def get_cliente_by_search(
    db: Session,
    filters: dict,
    page: int = 1,
    limit: int = 20,
) -> dict:
    """Retorna lista paginada de clientes com busca."""
    skip = (page - 1) * limit

    clientes, total_items = cliente_crud.get_cliente_by_search(
        db,
        filters=filters,
        skip=skip,
        limit=limit,
    )

    total_pages = (total_items + limit - 1) // limit if total_items > 0 else 0

    return {
        "items": clientes,
        "total_items": total_items,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "filters": filters,
    }

def get_cliente_simple_by_search(db: Session, search: str = None) -> list[ClienteSimpleRead]:
    return cliente_crud.get_cliente_simple_by_search(db, search=search)

def cliente_exists(db: Session, cliente_id: int) -> None:
    """Verifica se um cliente existe no banco."""
    customer_in_db = cliente_crud.get_cliente_by_id(db, cliente_id=cliente_id)
    if not customer_in_db:
        raise not_found_exce
    return customer_in_db

# ===========================================================================
# LÓGICA DE ATUALIZAÇÃO (UPDATE)
# ===========================================================================

def update_cliente_by_id(db: Session, cliente_id: int, data: ClienteUpdate) -> ClienteModel:
    """Atualiza dados de um cliente existente (PF ou PJ)."""
    cliente_in_db = _get_cliente_or_raise(db, cliente_id)

    update_data = data.model_dump(exclude_unset=True)
    _validar_unicidade_cliente(db, update_data, cliente_id=cliente_id)

    if "endereco" in update_data:
        enderecos_atualizados = address_service.update_address_in_db(
            address_in_db=cliente_in_db.endereco,
            address_to_update=data.endereco,
            id_entity=cliente_id,
            type_entity=EntityType.CLIENTE,
        )
        cliente_in_db.endereco = enderecos_atualizados
        del update_data["endereco"]

    for key, value in update_data.items():
        if key == "tipo":
            continue
        if key == "genero" and value is not None:
            value = Gender(value)
        setattr(cliente_in_db, key, value)

    return cliente_crud.update_cliente(db, cliente_to_update=cliente_in_db)

# ===========================================================================
# LÓGICA DE STATUS (TOGGLE)
# ===========================================================================

def toggle_active_disable_cliente_by_id(db: Session, cliente_id: int) -> ClienteModel:
    """Inverte o status 'ativo' do cliente (Ativar <-> Desativar)."""
    cliente_in_db = _get_cliente_or_raise(db, cliente_id)
    cliente_in_db.ativo = not cliente_in_db.ativo
    return cliente_crud.update_cliente(db, cliente_to_update=cliente_in_db)

# ===========================================================================
# EQUIPAMENTOS DO CLIENTE (HISTÓRICO)
# ===========================================================================

EQUIPMENT_HISTORY_LIMIT = 20

def get_equipamentos_historico_by_cliente_id(
    db: Session, cliente_id: int
) -> list:
    """
    Retorna equipamentos únicos (ativos) de um cliente, deduplicados
    por (tipo_equipamento, marca, modelo, numero_serie) e limitados
    aos mais recentes.
    """
    _get_cliente_or_raise(db, cliente_id)

    equipamentos = cliente_crud.get_objetos_by_cliente_id(db, cliente_id)

    seen: set[tuple] = set()
    resultado: list = []

    for equip in equipamentos:
        key = (equip.tipo_equipamento, equip.marca, equip.modelo, equip.numero_serie)
        if key not in seen:
            seen.add(key)
            resultado.append(equip)
        if len(resultado) >= EQUIPMENT_HISTORY_LIMIT:
            break

    return resultado
