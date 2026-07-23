# ---------------------------------------------------------------------------
# ARQUIVO: endpoints/ordem_servico.py
# DESCRICAO: Endpoints para Ordens de Serviço (OS).
#
# IMPORTANTE — Ordem de declaração das rotas:
#   Rotas com paths estáticos (ex: /stats, /finalizar) DEVEM ser declaradas
#   ANTES de rotas com path parameters (ex: /{os_number}), pois FastAPI
#   resolve rotas em ordem de declaração e um path param capturaria "stats"
#   como valor de os_number.
#
# Estrutura de endpoints:
#   POST   /                              → Criar OS
#   GET    /                              → Listar OS (paginado + filtros)
#   GET    /stats                         → Estatísticas agregadas
#   GET    /cliente/{cliente_id}          → Listar OS por cliente
#   GET    /{os_number}                   → Buscar OS pelo número
#   PUT    /{os_number}                   → Atualizar dados gerais da OS
#   PUT    /{os_number}/equipamento       → Atualizar equipamento/cliente
#   POST   /{os_number}/itens             → Adicionar item
#   PUT    /{os_number}/itens/{item_id}   → Atualizar item
#   DELETE /{os_number}/itens/{item_id}   → Remover item
#   PUT    /{os_number}/finalizar         → Finalizar OS com pagamentos
#   PUT    /{os_number}/cancelar          → Cancelar OS
#   PUT    /{os_number}/reabrir           → Reabrir OS finalizada/cancelada
#   POST   /{os_number}/fotos             → Upload de foto de diagnóstico
#   DELETE /{os_number}/fotos/{foto_id}   → Remover foto
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends, status, Path, Query, UploadFile, File, Response
from sqlalchemy.orm import Session

from app.core.depends import check_permission, get_current_active_user, _handle_db_transaction, is_visao_gerencial
from app.db.session import get_db
from app.schemas.ordem_servico import (
    OrdemServicoCreate,
    OrdemServicoRead,
    OrdemServicoQuery,
    OrdemServicoStats,
    OrdemServicoFilterParams,
    OrdemServicoUpdate,
    OSEquipamentoUpdate,
    OSItemCreate,
    OSItemUpdate,
    OrdemServicoFinalizar,
    OrdemServicoCancelar,
    OrdemServicoReabrir,
    OSFotoRead,
)
from app.services import ordem_servico as os_service
from app.services import ordem_servico_foto as os_foto_service
from app.services import segmentos as segmentos_service

router = APIRouter()

module_permission = "servico"


# ===========================================================================
# DEFINIÇÃO DE CAMPOS DO SEGMENTO (GET /definicao-campos)
# Rota estática — declarada antes das rotas com /{os_number}.
# ===========================================================================

@router.get(
    "/definicao-campos",
    summary="Definição de campos dinâmicos do segmento da empresa",
    description=(
        "Retorna o contrato de campos dinâmicos (veículo, check-in, acessórios e "
        "vistoria) do segmento da empresa, para o frontend renderizar o formulário "
        "de OS adequado. Segmentos sem definição dedicada retornam tem_definicao=false."
    ),
)
def get_definicao_campos_segmento(
    user_token: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return segmentos_service.get_definicao_campos(db)


@router.get(
    "/revisoes-pendentes",
    summary="Veículos com revisão vencida (por data e/ou KM)",
    description=(
        "Lista os veículos cuja próxima revisão está vencida — por data "
        "(proxima_revisao_data <= hoje) e/ou por KM (km atual >= proxima_revisao_km). "
        "Objetos sem revisão agendada (ex: informática) não aparecem."
    ),
)
def get_revisoes_pendentes(
    user_token: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return os_service.get_revisoes_pendentes(db)


@router.get(
    "/objeto/{objeto_id}/historico-km",
    summary="Histórico de KM do objeto/veículo",
    description=(
        "Retorna a evolução da quilometragem (km_entrada) de um objeto/veículo "
        "ao longo das suas OS, da mais antiga para a mais recente. Útil para oficina."
    ),
)
def get_historico_km_objeto(
    objeto_id: int = Path(..., description="ID do objeto/veículo"),
    user_token: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return os_service.get_historico_km(db, objeto_id)


# ===========================================================================
# CRIAÇÃO (POST /)
# ===========================================================================

@router.post(
    "/",
    response_model=OrdemServicoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Criar Nova OS",
    description=(
        "Cria uma nova Ordem de Serviço com equipamento e itens em uma única transação. "
        "O número da OS (ex: OS-2026-000001) é gerado automaticamente."
    )
)
def create_ordem_servico(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    os_data: OrdemServicoCreate,
    db: Session = Depends(get_db)
):
    return _handle_db_transaction(db, os_service.create_ordem_servico, os_data)


# ===========================================================================
# LISTAGEM E ESTATÍSTICAS (GET / e GET /stats)
# NOTA: Estas rotas estáticas devem estar ANTES de GET /{os_number}
# ===========================================================================

@router.get(
    "/",
    response_model=OrdemServicoQuery,
    status_code=status.HTTP_200_OK,
    summary="Listar OS",
    description=(
        "Retorna lista paginada de OS com suporte a filtros. "
        "Filtros disponíveis: busca por texto (numero_os, nome do cliente), "
        "status e ordenação por prioridade."
    )
)
def get_ordens_servico(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    filters: OrdemServicoFilterParams = Depends(),
    page: int = Query(1, ge=1, description="Página atual"),
    limit: int = Query(20, ge=1, le=100, description="Itens por página"),
    db: Session = Depends(get_db)
):
    filters_dict = filters.model_dump(exclude_unset=True)
    if not is_visao_gerencial(user_token):
        filters_dict["funcionario_id"] = user_token.get("funcionario_id")
    return os_service.get_ordem_servico_by_search(db, filters=filters_dict, page=page, limit=limit)


@router.get(
    "/stats",
    response_model=OrdemServicoStats,
    status_code=status.HTTP_200_OK,
    summary="Estatísticas de OS",
    description="Retorna contadores e ticket médio das OS no sistema."
)
def get_ordem_servico_stats(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    *,
    db: Session = Depends(get_db)
):
    funcionario_id = None if is_visao_gerencial(user_token) else user_token.get("funcionario_id")
    return os_service.get_ordem_servico_stats(db, funcionario_id=funcionario_id)


# ===========================================================================
# ALERTAS DE ABANDONO (GET /abandono)
# NOTA: Declarada ANTES de /{os_number} para não ser capturada como param
# ===========================================================================

@router.get(
    "/abandono",
    response_model=list[OrdemServicoRead],
    status_code=status.HTTP_200_OK,
    summary="OS em Abandono",
    description="Retorna OS finalizadas cujo prazo de abandono (configurável) já venceu."
)
def get_os_abandono(
    user_token: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    empresa_id = int(user_token.get("empresa_id"))
    funcionario_id = None if is_visao_gerencial(user_token) else user_token.get("funcionario_id")
    return os_service.get_os_abandono(db, empresa_id, funcionario_id=funcionario_id)


@router.get(
    "/atrasadas",
    response_model=list[OrdemServicoRead],
    status_code=status.HTTP_200_OK,
    summary="OS Atrasadas",
    description="Retorna OS abertas/em andamento com previsão de entrega vencida."
)
def get_os_atrasadas(
    user_token: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    empresa_id = int(user_token.get("empresa_id"))
    funcionario_id = None if is_visao_gerencial(user_token) else user_token.get("funcionario_id")
    return os_service.get_os_atrasadas(db, empresa_id, funcionario_id=funcionario_id)


# ===========================================================================
# HISTÓRICO POR CLIENTE (GET /cliente/{cliente_id})
# NOTA: Declarada ANTES de /{os_number} para não ser capturada como param
# ===========================================================================

@router.get(
    "/cliente/{cliente_id}",
    response_model=OrdemServicoQuery,
    status_code=status.HTTP_200_OK,
    summary="Listar OS por Cliente",
    description="Retorna lista paginada de OS vinculadas a um cliente específico."
)
def get_ordens_servico_by_cliente(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    cliente_id: int = Path(..., ge=1, description="ID do cliente"),
    *,
    page: int = Query(1, ge=1, description="Página atual"),
    limit: int = Query(10, ge=1, le=100, description="Itens por página"),
    db: Session = Depends(get_db)
):
    return os_service.get_ordens_servico_by_cliente_id(db, cliente_id, page, limit)


# ===========================================================================
# BUSCA POR NÚMERO (GET /{os_number})
# NOTA: Declarada APÓS as rotas estáticas para não capturar "stats" como param
# ===========================================================================

@router.get(
    "/{os_number}",
    response_model=OrdemServicoRead,
    status_code=status.HTTP_200_OK,
    summary="Buscar OS pelo Número",
    description="Retorna a OS completa (com itens, pagamentos e fotos) pelo número sequencial."
)
def get_ordem_servico_by_numero(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    os_number: str = Path(..., description="Número sequencial da OS (ex: OS-2026-000001)"),
    *,
    db: Session = Depends(get_db)
):
    return os_service.get_ordem_servico_by_numero_os(db, numero_os=os_number)


# ===========================================================================
# ATUALIZAÇÃO (PUT /{os_number})
# ===========================================================================

@router.put(
    "/{os_number}",
    response_model=OrdemServicoRead,
    status_code=status.HTTP_200_OK,
    summary="Atualizar OS",
    description=(
        "Atualiza campos gerais da OS. Todos os campos são opcionais. "
        "Não é permitido atualizar OS com status FINALIZADA ou CANCELADA. "
        "Para alterar o funcionário responsável, inclua funcionario_id. "
        "Para transições de status FINALIZADA/CANCELADA, use /finalizar e /cancelar."
    )
)
def update_ordem_servico(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    os_number: str = Path(..., description="Número da OS"),
    *,
    os_data: OrdemServicoUpdate,
    db: Session = Depends(get_db)
):
    return _handle_db_transaction(db, os_service.update_ordem_servico, os_number, os_data)


# ===========================================================================
# EQUIPAMENTO (PUT /{os_number}/equipamento)
# ===========================================================================

@router.put(
    "/{os_number}/objeto",
    response_model=OrdemServicoRead,
    status_code=status.HTTP_200_OK,
    summary="Atualizar Objeto da OS",
    description="Atualiza as informações do objeto associado à OS."
)
@router.put(
    "/{os_number}/equipamento",
    response_model=OrdemServicoRead,
    status_code=status.HTTP_200_OK,
    summary="Atualizar Equipamento da OS (Legado)",
    description=(
        "Atualiza as informações do equipamento associado à OS (compatibilidade). "
        "Permite também trocar o cliente proprietário do equipamento via cliente_id. "
        "Não é permitido em OS com status FINALIZADA ou CANCELADA."
    )
)
def update_equipamento_os(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    os_number: str = Path(..., description="Número da OS"),
    *,
    equipamento_data: OSEquipamentoUpdate,
    db: Session = Depends(get_db)
):
    return _handle_db_transaction(db, os_service.update_equipamento_os, os_number, equipamento_data)


# ===========================================================================
# ITENS
# ===========================================================================

@router.post(
    "/{os_number}/itens",
    response_model=OrdemServicoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Adicionar Item à OS",
    description=(
        "Adiciona um produto ou serviço à OS. "
        "O valor_total da OS é recalculado automaticamente. "
        "Não é permitido em OS com status FINALIZADA ou CANCELADA."
    )
)
def add_item_to_os(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    os_number: str = Path(..., description="Número da OS"),
    *,
    item_data: OSItemCreate,
    db: Session = Depends(get_db)
):
    return _handle_db_transaction(db, os_service.add_item_to_os, os_number, item_data)


@router.put(
    "/{os_number}/itens/{item_id}",
    response_model=OrdemServicoRead,
    status_code=status.HTTP_200_OK,
    summary="Atualizar Item da OS",
    description=(
        "Atualiza quantidade, valor unitário ou descrição de um item. "
        "O valor_total da OS é recalculado automaticamente."
    )
)
def update_item_os(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    os_number: str = Path(..., description="Número da OS"),
    item_id: int = Path(..., ge=1, description="ID do item"),
    *,
    item_data: OSItemUpdate,
    db: Session = Depends(get_db)
):
    return _handle_db_transaction(db, os_service.update_item_os, os_number, item_id, item_data)


@router.delete(
    "/{os_number}/itens/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover Item da OS",
    description="Remove um item da OS e recalcula o valor total."
)
def remove_item_from_os(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    os_number: str = Path(..., description="Número da OS"),
    item_id: int = Path(..., ge=1, description="ID do item"),
    *,
    db: Session = Depends(get_db)
):
    _handle_db_transaction(db, os_service.remove_item_from_os, os_number, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# AÇÕES DE STATUS
# ===========================================================================

@router.put(
    "/{os_number}/finalizar",
    response_model=OrdemServicoRead,
    status_code=status.HTTP_200_OK,
    summary="Finalizar OS",
    description=(
        "Finaliza a OS registrando a solução e os pagamentos. "
        "Regras: a soma dos pagamentos deve ser exatamente igual ao valor_total da OS. "
        "Cada forma_pagamento_id informado deve existir e estar ativo. "
        "Uma OS só é aceita como finalizada se o pagamento for integral."
    )
)
def finalizar_ordem_servico(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    os_number: str = Path(..., description="Número da OS"),
    *,
    data: OrdemServicoFinalizar,
    db: Session = Depends(get_db)
):
    return _handle_db_transaction(db, os_service.finalizar_ordem_servico, os_number, data)


@router.put(
    "/{os_number}/cancelar",
    response_model=OrdemServicoRead,
    status_code=status.HTTP_200_OK,
    summary="Cancelar OS",
    description=(
        "Cancela a OS. O motivo, se informado, é acrescentado às observações. "
        "Uma OS já cancelada não pode ser cancelada novamente — use /reabrir primeiro."
    )
)
def cancelar_ordem_servico(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    os_number: str = Path(..., description="Número da OS"),
    *,
    data: OrdemServicoCancelar,
    db: Session = Depends(get_db)
):
    return _handle_db_transaction(db, os_service.cancelar_ordem_servico, os_number, data)


@router.put(
    "/{os_number}/reabrir",
    response_model=OrdemServicoRead,
    status_code=status.HTTP_200_OK,
    summary="Reabrir OS",
    description=(
        "Reabre uma OS FINALIZADA ou CANCELADA. "
        "Os pagamentos existentes são removidos pois os valores podem ser renegociados. "
        "O status volta para EM_ANDAMENTO e a data de finalização é limpa."
    )
)
def reabrir_ordem_servico(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    os_number: str = Path(..., description="Número da OS"),
    *,
    payload: OrdemServicoReabrir = OrdemServicoReabrir(),
    db: Session = Depends(get_db)
):
    return _handle_db_transaction(
        db, os_service.reabrir_ordem_servico, os_number, payload.codigo_gerente, payload.cliente_pagou
    )


# ===========================================================================
# FOTOS
# ===========================================================================

@router.post(
    "/{os_number}/fotos",
    response_model=OSFotoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload de Foto da OS",
    description=(
        "Faz upload de uma foto de diagnóstico para a OS. "
        "O arquivo é salvo em static/uploads/ordens-servico/{os_id}/ com nome UUID. "
        "Formatos aceitos: JPEG, PNG, WEBP."
    )
)
def upload_foto_os(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    os_number: str = Path(..., description="Número da OS"),
    *,
    image_file: UploadFile = File(..., description="Arquivo de imagem (JPEG, PNG, WEBP)"),
    db: Session = Depends(get_db)
):
    return _handle_db_transaction(db, os_foto_service.upload_foto_os, os_number, image_file)


@router.delete(
    "/{os_number}/fotos/{foto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover Foto da OS",
    description="Remove uma foto de diagnóstico da OS (arquivo físico e registro no banco)."
)
def delete_foto_os(
    user_token: dict = Depends(check_permission(required_permission=module_permission)),
    os_number: str = Path(..., description="Número da OS"),
    foto_id: int = Path(..., ge=1, description="ID da foto"),
    *,
    db: Session = Depends(get_db)
):
    _handle_db_transaction(db, os_foto_service.delete_foto_os, os_number, foto_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
