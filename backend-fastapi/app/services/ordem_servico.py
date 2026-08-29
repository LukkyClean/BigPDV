# ---------------------------------------------------------------------------
# ARQUIVO: services/ordem_servico.py
# DESCRICAO: Regras de negócio para Ordens de Serviço.
#
# Fluxo de status permitidos:
#   ABERTA → EM_ANDAMENTO → AGUARDANDO_PECAS → AGUARDANDO_APROVACAO
#          → AGUARDANDO_RETIRADA → FINALIZADA
#   Qualquer status ativo → CANCELADA
#   FINALIZADA / CANCELADA → EM_ANDAMENTO  (via /reabrir)
#
# Regras financeiras:
#   valor_bruto = soma dos itens (quantidade × valor_unitario)
#   valor_total = valor_bruto - desconto
#   Finalização só é permitida se sum(pagamentos) + valor_entrada == valor_total
# ---------------------------------------------------------------------------

from datetime import datetime, date
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.ordem_servico import (
    OrdemServicoCreate,
    OrdemServicoUpdate,
    OSEquipamentoUpdate,
    OSItemCreate,
    OSItemUpdate,
    OrdemServicoFinalizar,
    OrdemServicoCancelar,
    OrdemServicoQuery,
    OrdemServicoStats
)

from app.db.models.ordem_servico import OrdemServico as OSModel
from app.db.models.objeto_servico import ObjetoServico as OSEquipamentoModel
from app.db.models.ordem_servico_item import OrdemServicoItem as OSItemModel
from app.db.models.ordem_servico_pagamento import OrdemServicoPagamento as OSPagamentoModel

from app.db.crud import ordem_servico as os_crud
from app.db.crud import cliente as cliente_crud
from app.db.crud import funcionario as funcionario_crud
from app.db.crud import forma_pagamento as fp_crud
from app.db.crud import configuracao_seguranca as config_seg_crud
from app.db.crud import produto as produto_crud

from app.services.segmentos import (
    validar_objeto_por_segmento,
    identificador_pesquisavel_atual,
    get_segmento_atual,
)
from app.core import segmentos as reg
from app.core.busca import compactar
from app.services import movimentacao_estoque as mov_service

from app.core.enum import (
    OrdemServicoItemTipo,
    OrdemServicoStatus,
    SituacaoEquipamento,
    OrdemServicoItemAprovacao,
    MovimentacaoTipo,
    MovimentacaoOrigem,
)
from app.core.security import verify_password
from app.helpers.set_pagination import _set_pagination


# ===========================================================================
# EXCEÇÕES REUTILIZÁVEIS
# ===========================================================================

os_not_found_exce = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Ordem de Serviço não encontrada"
)

cliente_not_found_exce = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Cliente não encontrado"
)

funcionario_not_found_exce = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Funcionário não encontrado"
)

item_not_found_exce = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Item não encontrado nesta OS"
)

forma_pagamento_not_found_exce = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Forma de pagamento não encontrada ou inativa"
)

os_fechada_exce = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="Esta operação não é permitida para OS com status FINALIZADA ou CANCELADA"
)


def _assert_forma_pagamento_entrada(db: Session, fp_id: int | None) -> None:
    """
    Valida a forma de pagamento do adiantamento.

    Mesma regra dos pagamentos da finalizacao (existir e estar ativa). A coluna
    e um FK sem constraint no SQLite (ver a migration d3e4f5a6b7c8), entao um id
    invalido passaria direto e so apareceria como forma vazia no resumo.

    None e valido: adiantamento sem forma declarada e o estado de toda OS
    anterior a este campo.
    """
    if fp_id is None:
        return
    forma_pagamento = fp_crud.get_forma_pagamento_by_id(db, fp_id=fp_id)
    if not forma_pagamento or not forma_pagamento.ativo:
        raise forma_pagamento_not_found_exce

os_nao_pode_reabrir_exce = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="Apenas OS com status FINALIZADA ou CANCELADA podem ser reabertas"
)

pagamento_valor_invalido_exce = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="A soma dos pagamentos não confere com o valor total da OS"
)

status_invalido_exce = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="Use os endpoints /finalizar ou /cancelar para essas transições de status"
)


# ===========================================================================
# HELPERS PRIVADOS
# ===========================================================================

def _get_os_or_raise(db: Session, numero_os: str) -> OSModel:
    """Busca OS pelo número ou lança 404."""
    os_in_db = os_crud.get_ordem_servico_by_numero_os(db, numero_os=numero_os)
    if not os_in_db:
        raise os_not_found_exce
    return os_in_db


def _assert_os_editavel(os_in_db: OSModel) -> None:
    """Lança 409 se a OS estiver FINALIZADA ou CANCELADA."""
    if os_in_db.status in (OrdemServicoStatus.FINALIZADA, OrdemServicoStatus.CANCELADA):
        raise os_fechada_exce


def _assert_sem_itens_pendentes(os_in_db: OSModel) -> None:
    """Lanca 422 se a OS tem item aguardando resposta do cliente.

    PENDENTE quer dizer que o cliente ainda nao disse se aprova ou recusa.
    Fechar a OS assim decide por ele: hoje o item entra no total (ele paga por
    peca que nao autorizou) e nao baixa do estoque (a peca sai da conta mas
    continua na prateleira). Ou aprova, ou recusa — nao da para entregar o
    veiculo com a pergunta em aberto.

    Nao afeta segmento sem aprovacao por item: la o default e APROVADO e nenhum
    item nasce PENDENTE.
    """
    pendentes = [
        item.nome for item in os_in_db.itens
        if item.status_aprovacao == OrdemServicoItemAprovacao.PENDENTE
    ]
    if pendentes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Ha itens aguardando aprovacao do cliente: "
                + ", ".join(pendentes)
                + ". Aprove ou reprove cada um antes de finalizar."
            ),
        )


def _assert_item_coerente(item: OSItemModel) -> None:
    """Peça embutida vale zero; item cobrado vale mais que zero.

    Espelha o validador de OSItemBase, para a regra valer também no PATCH — ver
    a explicação da invariante no modelo do item.
    """
    if not item.visivel_cliente and (item.valor_total or 0) != 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Peça embutida no serviço não é cobrada à parte: o valor dela deve ser zero",
        )
    if item.visivel_cliente and (item.valor_total or 0) <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Item cobrado do cliente precisa de valor maior que zero",
        )


def _item_conta_no_total(status: OrdemServicoItemAprovacao) -> bool:
    """Um item entra no total da OS a menos que esteja REPROVADO."""
    return status != OrdemServicoItemAprovacao.REPROVADO


def _recalcular_valor_total_os(os_in_db: OSModel) -> None:
    """
    Recalcula valor_bruto e valor_total com base nos itens atuais da OS.
    Itens REPROVADO são excluídos do total (fluxo de orçamento/oficina).
    Deve ser chamado sempre que itens ou desconto forem alterados.
    """
    valor_bruto = sum(
        item.valor_total for item in os_in_db.itens
        if _item_conta_no_total(item.status_aprovacao)
    )
    os_in_db.valor_bruto = valor_bruto
    os_in_db.valor_total = max(0, valor_bruto - (os_in_db.desconto or 0) + (os_in_db.taxa_entrega or 0) + (os_in_db.acrescimo or 0))


# ===========================================================================
# CRIAÇÃO (CREATE)
# ===========================================================================

def _preencher_identificador_gerado(
    db: Session,
    objeto_data: dict,
    numero_os: str,
    cliente,
) -> None:
    """Preenche, para segmentos que declaram identificador GERADO, o que o
    usuário não tem como saber.

    Muda `objeto_data` no lugar. É no-op para oficina e informática, que pedem
    o identificador ao usuário porque ele existe no mundo (placa, nº de série).

    Preenche também `marca`/`modelo` quando vierem vazios: são colunas NOT NULL
    herdadas do desenho de veículo/equipamento, e numa serigrafia a "marca" da
    arte, no caso comum, é o próprio cliente que está pedindo. Exigir que ele
    redigite o nome do cliente ali seria atrito sem informação nova.
    """
    segmento = get_segmento_atual(db)
    if not reg.identificador_e_gerado(segmento):
        return

    if not (objeto_data.get("numero_serie") or "").strip():
        objeto_data["numero_serie"] = reg.gerar_identificador(segmento, numero_os)

    if not (objeto_data.get("marca") or "").strip():
        objeto_data["marca"] = (getattr(cliente, "nome", None) or "").strip() or "—"

    if not (objeto_data.get("modelo") or "").strip():
        objeto_data["modelo"] = objeto_data["numero_serie"]


def _exigir_campos_do_objeto(db: Session, objeto_data: dict) -> None:
    """Repõe, no serviço, as exigências que saíram do schema.

    `marca`, `modelo` e `numero_serie` viraram opcionais no schema para o
    segmento que gera o próprio identificador e preenche o resto. Sem esta
    guarda, informática e oficina — que contavam com o `Field(...)` obrigatório
    — passariam a aceitar OS sem esses dados, e o objeto do cliente ficaria
    inencontrável. São colunas NOT NULL, então o banco explodiria com um 500
    feio em vez de um 422 explicando o que falta.

    Esta função é o que protege os dois segmentos que já estão em produção.
    Coberta por test/api/v1/test_os_identificador_gerado.py.
    """
    identificador = reg.get_identificador_segmento(get_segmento_atual(db)) or {}

    faltando = [
        rotulo
        for campo, rotulo in (
            ("marca", "Marca"),
            ("modelo", "Modelo"),
            ("numero_serie", identificador.get("label") or "Número de série"),
        )
        if not (objeto_data.get(campo) or "").strip()
    ]
    if not faltando:
        return

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=f"{', '.join(faltando)}: obrigatório para abrir uma OS.",
    )


def create_ordem_servico(db: Session, os_to_create: OrdemServicoCreate) -> OSModel:
    """
    Cria uma nova OS com equipamento e itens em uma única transação.

    Valida: cliente existe, funcionário existe (se informado).
    Gera: número sequencial, valor_bruto e valor_total.
    """
    cliente_in_db = cliente_crud.get_cliente_by_id(db, cliente_id=os_to_create.cliente_id)
    if not cliente_in_db:
        raise cliente_not_found_exce

    funcionario_in_db = None
    if os_to_create.funcionario_id:
        funcionario_in_db = funcionario_crud.get_funcionario_by_id(db, funcionario_id=os_to_create.funcionario_id)
        if not funcionario_in_db:
            raise funcionario_not_found_exce

    next_number = os_crud.get_next_numero(db)
    valor_bruto_os = 0
    itens_model = []

    for item in os_to_create.itens:
        valor_item = round(item.quantidade * item.valor_unitario)
        # Itens REPROVADO não entram no total (default APROVADO conta, como hoje).
        if _item_conta_no_total(item.status_aprovacao):
            valor_bruto_os += valor_item
        item_data = item.model_dump(exclude={"item_id"}, exclude_unset=True)
        itens_model.append(OSItemModel(
            **item_data,
            produto_id=item.item_id if item.item_id and item.tipo == OrdemServicoItemTipo.PRODUTO else None,
            servico_id=item.item_id if item.item_id and item.tipo == OrdemServicoItemTipo.SERVICO else None,
            valor_total=valor_item
        ))

    desconto = os_to_create.desconto or 0
    # Mesma fórmula de _recalcular_valor_total_os (inclui taxa de entrega e acréscimo),
    # para o total na criação bater com o total após qualquer recálculo posterior.
    valor_total_os = max(
        0,
        valor_bruto_os - desconto
        + (os_to_create.taxa_entrega or 0)
        + (os_to_create.acrescimo or 0),
    )

    # Suporta tanto 'objeto' quanto 'equipamento' (para retrocompatibilidade)
    objeto_schema = os_to_create.objeto or os_to_create.equipamento
    if not objeto_schema:
        raise HTTPException(
            status_code=400,
            detail="É necessário fornecer os dados do objeto/equipamento de serviço."
        )

    objeto_data = objeto_schema.model_dump(exclude_unset=True)

    # Extrai campos legados do objeto/equipamento e move para dados_adicionais
    obj_dados_adicionais = objeto_data.get("dados_adicionais") or {}
    for legacy_field in ["tipo_equipamento", "imei"]:
        if legacy_field in objeto_data:
            val = objeto_data.pop(legacy_field)
            if val:
                obj_dados_adicionais[legacy_field] = val.value if hasattr(val, 'value') else val

    objeto_data["dados_adicionais"] = obj_dados_adicionais

    # --- Identificador gerado pelo sistema (ex: serigrafia) ---
    # Placa e numero de serie existem no mundo: estao escritos no bem, e o
    # atendente so copia. Codigo de arte nao existe ate alguem inventar -- e
    # campo obrigatorio que o usuario nao tem como preencher vira lixo ("1",
    # "teste"), que e como dois notebooks ja colapsaram num cadastro so.
    #
    # Aqui o codigo nasce do numero da OS, que ja e sequencial e unico: nao ha
    # contador novo para manter nem corrida entre terminais para tratar.
    _preencher_identificador_gerado(db, objeto_data, next_number, cliente_in_db)
    _exigir_campos_do_objeto(db, objeto_data)

    # Validacao especifica de segmento (ex: placa para oficina). Gated: e no-op
    # para segmentos sem regra dedicada, entao o fluxo de informatica permanece intacto.
    validar_objeto_por_segmento(
        db,
        numero_serie=objeto_data.get("numero_serie"),
        dados_adicionais=obj_dados_adicionais,
    )

    # Reutiliza o objeto existente do cliente (mesma placa/serial) em vez de duplicar:
    # um bem físico é UM registro que acumula histórico (KM, revisão) entre as OSs.
    # Se não existir, cria um novo. Agnóstico de segmento.
    #
    # Só vale como chave um identificador de verdade: `numero_serie` é obrigatório,
    # então quem não tem o dado digita "S/N" — e por igualdade crua dois bens
    # distintos do mesmo cliente colapsavam em UM registro, com o segundo
    # sobrescrevendo marca/modelo do primeiro. Ver identificador_pesquisavel().
    numero_serie = objeto_data.get("numero_serie")
    equipamento_existente = (
        os_crud.get_objeto_ativo_by_cliente_e_serie(db, cliente_in_db.id, numero_serie)
        if numero_serie and identificador_pesquisavel_atual(db, numero_serie) else None
    )
    if equipamento_existente:
        # Atualiza os detalhes informados, mas PRESERVA a próxima revisão já agendada.
        for campo in ("marca", "modelo", "cor"):
            valor = objeto_data.get(campo)
            if valor:
                setattr(equipamento_existente, campo, valor)
        novos_dados = objeto_data.get("dados_adicionais") or {}
        if novos_dados:
            equipamento_existente.dados_adicionais = {
                **(equipamento_existente.dados_adicionais or {}),
                **novos_dados,
            }
        equipamento_to_db = equipamento_existente
    else:
        equipamento_to_db = OSEquipamentoModel(**objeto_data, cliente=cliente_in_db)

    valor_entrada = os_to_create.valor_entrada or 0
    _assert_forma_pagamento_entrada(db, os_to_create.forma_pagamento_entrada_id)
    if os_to_create.usar_credito_cliente and valor_entrada > 0:
        if (cliente_in_db.saldo_credito or 0) < valor_entrada:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Saldo de crédito insuficiente para cobrir o valor de entrada informado"
            )
        cliente_in_db.saldo_credito = (cliente_in_db.saldo_credito or 0) - valor_entrada

    os_data = os_to_create.model_dump(
        exclude={"cliente_id", "itens", "objeto", "equipamento", "valor_bruto", "usar_credito_cliente"},
        exclude_unset=True
    )

    # Extrai campos legados da OS e move para dados_adicionais
    dados_adicionais = os_data.get("dados_adicionais") or {}
    for legacy_field in ["senha_aparelho", "acessorios", "condicoes_aparelho"]:
        if legacy_field in os_data:
            val = os_data.pop(legacy_field)
            if val:
                dados_adicionais[legacy_field] = val

    os_data["dados_adicionais"] = dados_adicionais

    os_to_db = OSModel(
        **os_data,
        status=OrdemServicoStatus.ABERTA,
        valor_total=valor_total_os,
        valor_bruto=valor_bruto_os,
        numero_os=next_number,
        objeto=equipamento_to_db,
        itens=itens_model,
        funcionario=funcionario_in_db,
    )

    return os_crud.create_ordem_servico(db, os_to_add=os_to_db)


# ===========================================================================
# LEITURA (READ)
# ===========================================================================

def get_ordem_servico_by_numero_os(db: Session, numero_os: str) -> OSModel:
    """Busca OS pelo número sequencial público. Lança 404 se não encontrada."""
    os_in_db = os_crud.get_ordem_servico_by_numero_os(db, numero_os=numero_os)
    if not os_in_db:
        raise os_not_found_exce
    return os_in_db


def get_ordem_servico_by_search(db: Session, filters: dict, page: int, limit: int) -> OrdemServicoQuery:
    """Retorna lista paginada de OS com filtros dinâmicos."""
    skip = (page - 1) * limit
    (order_service_in_db, total_items) = os_crud.get_ordens_servico_by_search(
        db, filters=filters, skip=skip, limit=limit
    )

    (total_pages, link) = _set_pagination(
        total_items=total_items, filters=filters, page=page, limit=limit
    )

    return OrdemServicoQuery(
        filters=filters,
        items=order_service_in_db,
        total_items=total_items,
        page=page,
        limit=limit,
        total_pages=total_pages,
        links=link,
    )


def get_ordens_servico_by_cliente_id(
    db: Session, cliente_id: int, page: int, limit: int
) -> OrdemServicoQuery:
    """Retorna lista paginada de OS vinculadas a um cliente específico."""
    cliente_in_db = cliente_crud.get_cliente_by_id(db, cliente_id=cliente_id)
    if not cliente_in_db:
        raise cliente_not_found_exce

    skip = (page - 1) * limit
    (order_service_in_db, total_items) = os_crud.get_ordens_servico_by_cliente_id(
        db, cliente_id=cliente_id, skip=skip, limit=limit
    )

    filters = {"cliente_id": cliente_id}
    (total_pages, link) = _set_pagination(
        total_items=total_items, filters=filters, page=page, limit=limit
    )

    return OrdemServicoQuery(
        filters=filters,
        items=order_service_in_db,
        total_items=total_items,
        page=page,
        limit=limit,
        total_pages=total_pages,
        links=link,
    )


def get_ordem_servico_stats(db: Session, funcionario_id: int | None = None) -> OrdemServicoStats:
    """Retorna estatísticas agregadas das OS."""
    return os_crud.get_ordem_servico_stats(db, funcionario_id=funcionario_id)


# ===========================================================================
# ATUALIZAÇÃO (UPDATE)
# ===========================================================================

_CAMPOS_TEXTO = frozenset({
    'defeito_relatado', 'diagnostico', 'solucao',
    'observacoes', 'senha_aparelho', 'acessorios', 'condicoes_aparelho',
    'dados_adicionais'
})

def update_ordem_servico(db: Session, numero_os: str, data: OrdemServicoUpdate) -> OSModel:
    """
    Atualiza campos gerais de uma OS.

    Restrições:
    - OS FINALIZADA ou CANCELADA só aceita atualização de campos de texto.
    - Transições para FINALIZADA e CANCELADA são bloqueadas (use /finalizar ou /cancelar).
    - Se desconto mudar, valor_total é recalculado automaticamente.
    - Se funcionario_id mudar, o funcionário é validado no banco.
    """
    os_in_db = _get_os_or_raise(db, numero_os)

    update_data = data.model_dump(exclude_unset=True)

    # Extrai campos legados e move para dados_adicionais.
    # dict(...) cria um novo objeto para que o SQLAlchemy detecte a mudança
    # (JSON não é rastreado in-place; reatribuir a mesma referência não persiste).
    dados_adicionais = dict(getattr(os_in_db, "dados_adicionais", None) or {})
    if "dados_adicionais" in update_data:
        sent_data = update_data.pop("dados_adicionais") or {}
        dados_adicionais.update(sent_data)

    # O campo legado `acessorios` (texto, da informática) colide de nome com o
    # `dados_adicionais.acessorios` (Record de checkboxes da vistoria da oficina):
    # um "" vindo do form apagava o Record a cada update. Guarda: não sobrescreve
    # quando o valor já existente é um Record (dict) — condição que só a oficina
    # tem. Para a informática (sempre texto), o comportamento fica idêntico ao de
    # antes (inclusive continua podendo limpar o campo com string vazia).
    for legacy_field in ["senha_aparelho", "acessorios", "condicoes_aparelho"]:
        if legacy_field in update_data:
            val = update_data.pop(legacy_field)
            if val is not None and not isinstance(dados_adicionais.get(legacy_field), dict):
                dados_adicionais[legacy_field] = val

    os_in_db.dados_adicionais = dados_adicionais

    is_texto_only = update_data.keys() <= _CAMPOS_TEXTO
    if not is_texto_only:
        _assert_os_editavel(os_in_db)

    # Bloqueia transições que têm endpoints próprios
    new_status = update_data.get("status")
    if new_status in (OrdemServicoStatus.FINALIZADA, OrdemServicoStatus.CANCELADA):
        raise status_invalido_exce

    if "forma_pagamento_entrada_id" in update_data:
        _assert_forma_pagamento_entrada(db, update_data["forma_pagamento_entrada_id"])

    # Adiantamento zerado nao pode manter forma de pagamento pendurada.
    if update_data.get("valor_entrada") == 0:
        update_data["forma_pagamento_entrada_id"] = None

    # Valida novo funcionário se informado
    novo_funcionario_id = update_data.pop("funcionario_id", None)
    if novo_funcionario_id is not None:
        funcionario_in_db = funcionario_crud.get_funcionario_by_id(db, funcionario_id=novo_funcionario_id)
        if not funcionario_in_db:
            raise funcionario_not_found_exce
        os_in_db.funcionario = funcionario_in_db

    # Aplica os demais campos
    for key, value in update_data.items():
        setattr(os_in_db, key, value)

    # Recalcula total se desconto foi alterado
    if "desconto" in update_data:
        _recalcular_valor_total_os(os_in_db)

    return os_crud.update_ordem_servico(db, os_to_update=os_in_db)


def update_equipamento_os(db: Session, numero_os: str, data: OSEquipamentoUpdate) -> OSModel:
    """
    Atualiza informações do equipamento de uma OS.

    Permite também trocar o cliente proprietário via cliente_id.
    Restrição: OS FINALIZADA ou CANCELADA não pode ser editada.
    """
    os_in_db = _get_os_or_raise(db, numero_os)
    _assert_os_editavel(os_in_db)

    equipamento = os_in_db.equipamento
    update_data = data.model_dump(exclude_unset=True)

    # Valida e troca o cliente se solicitado
    novo_cliente_id = update_data.pop("cliente_id", None)
    if novo_cliente_id is not None:
        cliente_in_db = cliente_crud.get_cliente_by_id(db, cliente_id=novo_cliente_id)
        if not cliente_in_db:
            raise cliente_not_found_exce
        equipamento.cliente = cliente_in_db

    # Extrai dados_adicionais e campos de retrocompatibilidade do objeto.
    # dict(...) garante um novo objeto para o SQLAlchemy detectar a mudança.
    obj_dados_adicionais = dict(getattr(equipamento, "dados_adicionais", None) or {})
    if "dados_adicionais" in update_data:
        sent_data = update_data.pop("dados_adicionais") or {}
        obj_dados_adicionais.update(sent_data)

    for legacy_field in ["tipo_equipamento", "imei"]:
        if legacy_field not in update_data:
            continue
        val = update_data.pop(legacy_field)
        if val is None:
            # Nao informado: preserva o que ja existe (semantica de PATCH).
            continue
        valor = val.value if hasattr(val, 'value') else val
        if valor == "":
            # String vazia = limpar de proposito. Gravar "" era o bug: o form
            # devolve "" para campo nao preenchido e isso sobrescrevia o dado real.
            obj_dados_adicionais.pop(legacy_field, None)
        else:
            obj_dados_adicionais[legacy_field] = valor

    equipamento.dados_adicionais = obj_dados_adicionais

    for key, value in update_data.items():
        setattr(equipamento, key, value)

    # Validacao especifica de segmento sobre o estado final do objeto (gated).
    validar_objeto_por_segmento(
        db,
        numero_serie=equipamento.numero_serie,
        dados_adicionais=equipamento.dados_adicionais,
    )

    return os_crud.update_ordem_servico(db, os_to_update=os_in_db)


# ===========================================================================
# HISTÓRICO DE KM (oficina)
# ===========================================================================

def get_historico_km(db: Session, objeto_id: int) -> list[dict]:
    """
    Histórico de quilometragem de um objeto/veículo ao longo das suas OS.

    Lê o KM de entrada gravado em dados_adicionais["km_entrada"] de cada OS,
    da mais antiga para a mais recente. Retorna apenas as OS que registraram KM.
    """
    ordens = os_crud.get_ordens_by_objeto_id(db, objeto_id)
    historico = []
    for o in ordens:
        km = (o.dados_adicionais or {}).get("km_entrada")
        if km is None:
            continue
        historico.append({
            "numero_os": o.numero_os,
            "data": o.data_criacao,
            "km_entrada": km,
        })
    return historico


def _ultimo_km_conhecido(db: Session, objeto_id: int) -> int | None:
    """Maior km_entrada registrado nas OS de um objeto (KM atual estimado)."""
    kms = [
        (o.dados_adicionais or {}).get("km_entrada")
        for o in os_crud.get_ordens_by_objeto_id(db, objeto_id)
    ]
    kms = [k for k in kms if isinstance(k, int)]
    return max(kms) if kms else None


def get_revisoes_pendentes(db: Session) -> list[dict]:
    """
    Veículos com revisão vencida — por data (proxima_revisao_data <= hoje) e/ou
    por KM (km atual >= proxima_revisao_km). Objetos sem revisão agendada (ex:
    informática) não aparecem, pois têm ambos os campos nulos.
    """
    hoje = date.today()
    pendentes = []
    for obj in os_crud.get_objetos_com_revisao_agendada(db):
        km_atual = _ultimo_km_conhecido(db, obj.id)
        venc_data = obj.proxima_revisao_data is not None and obj.proxima_revisao_data <= hoje
        venc_km = (
            obj.proxima_revisao_km is not None
            and km_atual is not None
            and km_atual >= obj.proxima_revisao_km
        )
        if not (venc_data or venc_km):
            continue
        cliente_nome, cliente_telefone = _cliente_contato(obj.cliente)
        # Já existe uma OS em aberto (não finalizada/cancelada) para este veículo?
        # Usado pela UI para bloquear "Nova OS" e avisar o usuário.
        tem_os_aberta = any(
            o.status not in (OrdemServicoStatus.FINALIZADA, OrdemServicoStatus.CANCELADA)
            for o in os_crud.get_ordens_by_objeto_id(db, obj.id)
        )
        pendentes.append({
            "objeto_id": obj.id,
            "cliente_id": obj.cliente_id,
            "cliente_nome": cliente_nome,
            "cliente_telefone": cliente_telefone,
            "tem_os_aberta": tem_os_aberta,
            "numero_serie": obj.numero_serie,
            "marca": obj.marca,
            "modelo": obj.modelo,
            "proxima_revisao_data": obj.proxima_revisao_data,
            "proxima_revisao_km": obj.proxima_revisao_km,
            "km_atual": km_atual,
            "motivo": "data" if venc_data else "km",
            # Quando este veiculo mexeu pela ultima vez (o agendamento da revisao
            # grava aqui). E o que permite a UI mostrar a revisao mais recente no
            # topo: sem isto a lista saia na ordem do banco, e um veiculo que
            # acabou de entrar aparecia embaixo de um de semanas atras.
            "atualizado_em": obj.data_atualizacao,
        })
    # Mais recente primeiro. `datetime.min` no lugar de None manda o objeto sem
    # data para o fim SEM comparar None com None, que levanta TypeError no
    # sort e derrubaria a tela inteira de revisoes.
    pendentes.sort(key=lambda p: p["atualizado_em"] or datetime.min, reverse=True)
    return pendentes


def _cliente_contato(cliente) -> tuple[str | None, str | None]:
    """Nome de exibição e telefone do cliente (PF usa nome, PJ usa razão social)."""
    if cliente is None:
        return None, None
    nome = (
        getattr(cliente, "nome", None)
        or getattr(cliente, "razao_social", None)
        or getattr(cliente, "nome_fantasia", None)
    )
    telefone = getattr(cliente, "celular", None) or getattr(cliente, "telefone", None)
    return (nome.strip() if isinstance(nome, str) else nome), telefone


def verificar_identificador_objeto(
    db: Session,
    identificador: str,
    cliente_id: int | None = None,
) -> dict:
    """
    Responde se a placa/serial digitada já pertence a algum objeto cadastrado —
    inclusive de OUTRO cliente, que é o caso que o reuso comum nunca enxergou
    (`get_objeto_ativo_by_cliente_e_serie` é escopado ao dono).

    É um AVISO, nunca um bloqueio: a máquina pode ter sido vendida, e o atendente
    decide se abre a OS com o dono antigo ou segue com o novo.

    Duas regras de silêncio, para o aviso não virar ruído:
      - identificador não pesquisável ("S/N", "não sei") não bate com nada;
      - se o cliente atual JÁ tem um objeto com esse identificador, é o cliente
        voltando com o mesmo bem — reuso normal, nada a avisar. É isso que faz o
        aviso aparecer só na primeira OS depois da troca de dono, sem precisar
        guardar "já avisei" em lugar nenhum.
    """
    segmento = get_segmento_atual(db)
    pesquisavel = reg.identificador_pesquisavel(identificador, segmento)

    resultado: dict = {
        "identificador": identificador,
        "pesquisavel": pesquisavel,
        "conflitos": [],
    }

    if not pesquisavel:
        return resultado

    if cliente_id is not None and os_crud.get_objetos_ativos_por_identificador(
        db, identificador, cliente_id=cliente_id
    ):
        return resultado

    for objeto in os_crud.get_objetos_ativos_por_identificador(
        db, identificador, excluir_cliente_id=cliente_id
    ):
        nome_cliente, _ = _cliente_contato(objeto.cliente)
        ultima_os = os_crud.get_ultima_os_do_objeto(db, objeto.id)
        resultado["conflitos"].append({
            "objeto_id": objeto.id,
            "cliente_id": objeto.cliente_id,
            "cliente_nome": nome_cliente,
            "marca": objeto.marca,
            "modelo": objeto.modelo,
            "numero_serie": objeto.numero_serie,
            "ultima_os_numero": ultima_os.numero_os if ultima_os else None,
            "ultima_os_data": ultima_os.data_criacao if ultima_os else None,
        })

    return resultado


# Teto da lista devolvida ao seletor da OS. Busca por identificador que devolve
# vinte linhas ja errou o alvo -- quem digita placa quer UM bem.
BUSCA_OBJETO_LIMITE = 20

# Piso de caracteres para BUSCAR -- proposital que seja MENOR que o
# `IDENTIFICADOR_MIN_CARACTERES` (4) do registry.
#
# Os dois pisos respondem perguntas diferentes. La: "este texto identifica um
# bem?", e errar custa dedup errado, entao 4 e sensato. Aqui: "vale ir ao banco
# procurar?", e errar custa uma consulta que nao acha nada. Com 4, digitar as
# tres primeiras letras da placa ("ABC") nao devolvia o carro -- que e
# exatamente como se comeca a digitar uma placa.
BUSCA_OBJETO_MIN_CARACTERES = 3


def buscar_objetos_por_identificador(
    db: Session,
    termo: str,
    limite: int = BUSCA_OBJETO_LIMITE,
) -> list[dict]:
    """
    Objetos cujo identificador casa com o texto digitado, com o nome do dono
    junto -- o que permite ao seletor da OS achar o cliente pela placa, pelo
    numero de serie ou pelo codigo da arte, e nao so por nome/CPF.

    NAO usa `identificador_pesquisavel` para aprovar o termo, e isso e
    deliberado: aquela funcao cobra o regex do segmento, que na oficina e a
    placa INTEIRA (`^...$`). Quem lembra so o final da placa e digita "1D23"
    seria recusado justamente no segmento que mais precisa desta busca. Ali o
    regex esta certo -- decide o que vale como CHAVE de dedup; aqui seria
    errado, porque busca boa aceita pedaco.

    Ficam os dois filtros que a busca de fato precisa:
      - minimo de caracteres (ver BUSCA_OBJETO_MIN_CARACTERES), para "ab" nao
        varrer a loja inteira;
      - identificador generico, para "S/N" nao devolver todo mundo que nao
        tinha o numero em maos (ver IDENTIFICADORES_GENERICOS no registry).
    """
    compacto = compactar(termo)

    if len(compacto) < BUSCA_OBJETO_MIN_CARACTERES:
        return []
    if compacto in reg.IDENTIFICADORES_GENERICOS:
        return []

    encontrados: list[dict] = []
    for objeto in os_crud.buscar_objetos_por_identificador(db, termo, limite):
        nome_cliente, _ = _cliente_contato(objeto.cliente)
        encontrados.append({
            "objeto_id": objeto.id,
            "cliente_id": objeto.cliente_id,
            # Sai em cinza embaixo do objeto na lista. E o que distingue duas
            # linhas iguais quando o bem foi VENDIDO e existe no nome de dois
            # clientes -- o mesmo caso que o aviso de duplicidade ja trata.
            "cliente_nome": nome_cliente,
            "tipo_equipamento": str(objeto.tipo_equipamento),
            "marca": objeto.marca,
            "modelo": objeto.modelo,
            "numero_serie": objeto.numero_serie,
            "cor": objeto.cor,
            # Vao para o formulario junto com o resto: e o que faz a OS abrir
            # com chassi/ano/IMEI ja preenchidos, sem passar pela tela de
            # "objeto ja cadastrado?".
            "dados_adicionais": objeto.dados_adicionais or {},
        })

    return encontrados


# ===========================================================================
# ITENS (CREATE / UPDATE / DELETE)
# ===========================================================================

def add_item_to_os(db: Session, numero_os: str, item_data: OSItemCreate) -> OSModel:
    """
    Adiciona um novo item (produto ou serviço) a uma OS existente.

    Recalcula valor_bruto e valor_total após a inserção.
    Restrição: OS FINALIZADA ou CANCELADA não pode receber novos itens.
    """
    os_in_db = _get_os_or_raise(db, numero_os)
    _assert_os_editavel(os_in_db)

    valor_item = round(item_data.quantidade * item_data.valor_unitario)
    item_dict = item_data.model_dump(exclude={"item_id"}, exclude_unset=True)

    novo_item = OSItemModel(
        **item_dict,
        ordem_servico_id=os_in_db.id,
        produto_id=item_data.item_id if item_data.item_id and item_data.tipo == OrdemServicoItemTipo.PRODUTO else None,
        servico_id=item_data.item_id if item_data.item_id and item_data.tipo == OrdemServicoItemTipo.SERVICO else None,
        valor_total=valor_item,
    )

    os_crud.create_os_item(db, item_to_add=novo_item)
    db.refresh(os_in_db)  # Recarrega a lista de itens atualizada
    _recalcular_valor_total_os(os_in_db)

    return os_crud.update_ordem_servico(db, os_to_update=os_in_db)


def update_item_os(db: Session, numero_os: str, item_id: int, data: OSItemUpdate) -> OSModel:
    """
    Atualiza um item de OS.

    Verifica que o item pertence à OS informada antes de atualizar.
    Recalcula valor_bruto e valor_total após a atualização.
    """
    os_in_db = _get_os_or_raise(db, numero_os)
    _assert_os_editavel(os_in_db)

    item_in_db = os_crud.get_os_item_by_id(db, item_id=item_id)
    if not item_in_db or item_in_db.ordem_servico_id != os_in_db.id:
        raise item_not_found_exce

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item_in_db, key, value)

    # Recalcula valor_total do item se quantidade ou valor_unitario mudarem
    if "quantidade" in update_data or "valor_unitario" in update_data:
        item_in_db.valor_total = round(item_in_db.quantidade * item_in_db.valor_unitario)

    # Visibilidade e valor precisam continuar coerentes DEPOIS do patch — os dois
    # campos podem vir em requisições separadas, e só aqui dá para ver o estado
    # final. Sem esta guarda, marcar uma peça como embutida sem zerar o valor
    # deixaria a via do cliente com linhas que não somam o total impresso.
    _assert_item_coerente(item_in_db)

    os_crud.update_os_item(db, item_to_update=item_in_db)
    db.refresh(os_in_db)
    _recalcular_valor_total_os(os_in_db)

    return os_crud.update_ordem_servico(db, os_to_update=os_in_db)


def remove_item_from_os(db: Session, numero_os: str, item_id: int) -> None:
    """
    Remove um item de uma OS.

    Verifica que o item pertence à OS informada.
    Recalcula valor_bruto e valor_total após a remoção.
    Restrição: OS FINALIZADA ou CANCELADA não pode ter itens removidos.
    """
    os_in_db = _get_os_or_raise(db, numero_os)
    _assert_os_editavel(os_in_db)

    item_in_db = os_crud.get_os_item_by_id(db, item_id=item_id)
    if not item_in_db or item_in_db.ordem_servico_id != os_in_db.id:
        raise item_not_found_exce

    os_crud.delete_os_item(db, item_to_delete=item_in_db)
    db.refresh(os_in_db)
    _recalcular_valor_total_os(os_in_db)

    os_crud.update_ordem_servico(db, os_to_update=os_in_db)


# ===========================================================================
# ESTOQUE
#
# Peça aplicada numa OS sai do estoque igual peça vendida no balcão — o que
# mudava era só que ninguém dava a baixa. A baixa acontece na FINALIZAÇÃO (é
# quando a OS vira fato consumado, mesmo padrão da venda) e é desfeita se a OS
# for cancelada ou reaberta, senão reabrir e refinalizar tirava a peça duas
# vezes do estoque.
# ===========================================================================

def _itens_de_produto(os_in_db: OSModel) -> list[OSItemModel]:
    """Itens que consomem estoque: produto do catálogo e APROVADO.

    Item PENDENTE ou REPROVADO não entra no valor_total da OS, então também não
    pode sair do estoque — o cliente recusou a peça e ela continua na prateleira.
    Item avulso (sem produto_id) não tem estoque para movimentar.
    """
    return [
        item for item in os_in_db.itens
        if item.tipo == OrdemServicoItemTipo.PRODUTO
        and item.produto_id is not None
        and item.status_aprovacao == OrdemServicoItemAprovacao.APROVADO
        and (item.quantidade or 0) > 0
    ]


def _movimentar_estoque_os(
    db: Session,
    os_in_db: OSModel,
    saida: bool,
    usuario_token: dict | None = None,
) -> None:
    """Aplica (saida=True) ou estorna (saida=False) o estoque dos itens da OS.

    Delega ao registro central em services/movimentacao_estoque, que é quem
    altera a quantidade e grava o histórico na mesma operação. `permitir_negativo`
    é a regra específica da OS (ver o helper).
    """
    usuario_token = usuario_token or {}
    sub = usuario_token.get("sub")

    for item in _itens_de_produto(os_in_db):
        produto = produto_crud.get_produto_by_id(db, produto_id=item.produto_id)
        mov_service.registrar_movimentacao(
            db,
            produto=produto,
            tipo=MovimentacaoTipo.SAIDA if saida else MovimentacaoTipo.ENTRADA,
            quantidade=item.quantidade or 0,
            origem=MovimentacaoOrigem.ORDEM_SERVICO,
            usuario_id=int(sub) if sub else None,
            usuario_nome=usuario_token.get("nome", "Sistema"),
            ordem_servico_id=os_in_db.id,
            observacao=f"{'Baixa' if saida else 'Estorno'} pela OS {os_in_db.numero_os}",
            permitir_negativo=True,
        )


# ===========================================================================
# AÇÕES DE STATUS
# ===========================================================================

def finalizar_ordem_servico(
    db: Session,
    numero_os: str,
    data: OrdemServicoFinalizar,
    usuario_token: dict | None = None,
) -> OSModel:
    """
    Finaliza uma OS registrando a solução e os pagamentos.

    Regras de negócio:
    1. OS não pode estar FINALIZADA ou CANCELADA.
    2. Se desconto for informado, recalcula valor_total antes da validação.
    3. A soma dos pagamentos deve ser exatamente igual ao valor_total.
    4. Cada forma_pagamento_id deve existir e estar ativa no catálogo.
    5. Status → FINALIZADA, data_finalizacao → now().
    6. Nenhum item pode estar PENDENTE (aguardando resposta do cliente).
    """
    os_in_db = _get_os_or_raise(db, numero_os)
    _assert_os_editavel(os_in_db)
    _assert_sem_itens_pendentes(os_in_db)

    # Aplica campos financeiros se informados
    if data.desconto is not None:
        # Acumula desconto de todas as finalizações (não sobrescreve) — mesmo padrão do acrescimo
        os_in_db.desconto = (os_in_db.desconto or 0) + data.desconto
    if data.valor_entrada is not None:
        os_in_db.valor_entrada = data.valor_entrada
        # Adiantamento zerado nao pode manter forma de pagamento pendurada:
        # sobraria "pago em PIX" sem valor algum por tras.
        if data.valor_entrada == 0:
            os_in_db.forma_pagamento_entrada_id = None
    if data.taxa_entrega is not None:
        os_in_db.taxa_entrega = data.taxa_entrega
    if data.acrescimo is not None:
        # Acumula juros de todas as finalizações (não sobrescreve) para preservar histórico
        os_in_db.acrescimo = (os_in_db.acrescimo or 0) + data.acrescimo

    # Recalcula valor_total com todos os campos financeiros atualizados
    _recalcular_valor_total_os(os_in_db)

    # Valida valor total: pagamentos desta sessão + novos + entrada >= valor_total
    # credito_anterior = total pago em finalizações anteriores (pagamentos + entrada anterior)
    # max(0,...) evita negativo: se os pagamentos em DB são todos históricos, total_anteriores = 0
    total_historico = os_in_db.credito_anterior or 0
    total_anteriores = max(0, sum(p.valor for p in os_in_db.pagamentos) - total_historico)
    total_novos = sum(p.valor for p in data.pagamentos)
    valor_entrada = os_in_db.valor_entrada or 0
    situacao_sem_cobranca = data.situacao_equipamento in (
        SituacaoEquipamento.SEM_REPARO, SituacaoEquipamento.CONDENADO
    )
    if not situacao_sem_cobranca:
        if (total_historico + total_anteriores + total_novos + valor_entrada) < os_in_db.valor_total:
            raise pagamento_valor_invalido_exce

    # Valida e cria cada pagamento
    pagamentos_criados = []
    for pagamento_data in data.pagamentos:
        forma_pagamento = fp_crud.get_forma_pagamento_by_id(db, fp_id=pagamento_data.forma_pagamento_id)
        if not forma_pagamento or not forma_pagamento.ativo:
            raise forma_pagamento_not_found_exce

        pagamento = OSPagamentoModel(
            ordem_servico_id=os_in_db.id,
            forma_pagamento_id=pagamento_data.forma_pagamento_id,
            valor=pagamento_data.valor,
            juros_valor=pagamento_data.juros_valor,
            juros_responsavel=pagamento_data.juros_responsavel.value,
            parcelas=pagamento_data.parcelas,
            bandeira_cartao=pagamento_data.bandeira_cartao,
            vencimento=pagamento_data.vencimento,
            detalhes=pagamento_data.detalhes,
        )
        os_crud.create_os_pagamento(db, pagamento_to_add=pagamento)
        # Guarda só os desta finalização: `os_in_db.pagamentos` traz também os
        # de finalizações anteriores, e relançá-los duplicaria dinheiro no livro.
        pagamentos_criados.append(pagamento)

    # Para SEM_REPARO / CONDENADO: trata o excedente do adiantamento (entrada - total cobrado)
    if situacao_sem_cobranca and (os_in_db.valor_entrada or 0) > 0:
        excedente = max(0, (os_in_db.valor_entrada or 0) - (os_in_db.valor_total or 0))
        if excedente > 0 and not data.zerar_adiantamento:
            cliente = os_in_db.equipamento.cliente if os_in_db.equipamento else None
            if cliente:
                cliente.saldo_credito = (cliente.saldo_credito or 0) + excedente

    # Baixa das peças aplicadas. Vai aqui, junto da mudança de status, para que
    # a OS só consuma estoque quando de fato fecha — e para que reabrir devolva.
    _movimentar_estoque_os(db, os_in_db, saida=True, usuario_token=usuario_token)

    # O dinheiro entra no livro junto com a peça saindo do estoque, e pelo mesmo
    # motivo: é neste instante que a OS fecha. Sem isto o fechamento de caixa
    # somava a origem ORDEM_SERVICO que ninguém escrevia, e a gaveta de uma loja
    # com caixa ligado fechava com sobra todo dia.
    from app.services import sessao_caixa as caixa_service
    caixa_service.registrar_pagamentos_de_os(
        db,
        os_in_db,
        pagamentos_criados,
        operador_funcionario_id=(usuario_token or {}).get("funcionario_id"),
    )

    # E o que NÃO entrou na gaveta por ser promessa vira conta a receber. Roda
    # com o caixa ligado ou desligado — fiado é fiado em qualquer loja.
    from app.services import financeiro_receber as financeiro_receber_service
    financeiro_receber_service.registrar_promessas_de_os(db, os_in_db, pagamentos_criados)

    # Aplica finalização
    os_in_db.situacao_equipamento = data.situacao_equipamento
    os_in_db.garantia = data.garantia
    os_in_db.solucao = data.solucao
    os_in_db.status = OrdemServicoStatus.FINALIZADA
    # UTC, não hora local. Todo o resto do sistema grava em UTC (func.now()) e os
    # filtros de período do dashboard/relatórios comparam em UTC. Com hora local
    # (UTC-3), uma OS finalizada depois das 21h caía no dia seguinte pela régua
    # do relatório — e desde que o faturamento passou a ancorar em
    # data_finalizacao, isso virou dinheiro no dia errado.
    os_in_db.data_finalizacao = datetime.utcnow()

    if data.observacoes:
        os_in_db.observacoes = data.observacoes

    return os_crud.update_ordem_servico(db, os_to_update=os_in_db)


def cancelar_ordem_servico(
    db: Session,
    numero_os: str,
    data: OrdemServicoCancelar,
    usuario_token: dict | None = None,
) -> OSModel:
    """
    Cancela uma OS.

    O motivo, se informado, é acrescentado ao campo observações.
    Restrição: OS já CANCELADA não pode ser cancelada novamente.
    """
    os_in_db = _get_os_or_raise(db, numero_os)

    if os_in_db.status == OrdemServicoStatus.CANCELADA:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta OS já está cancelada"
        )

    if os_in_db.funcionario:
        empresa_id = os_in_db.funcionario.empresa_id
        config_seg = config_seg_crud.get_configuracao_seguranca(db, empresa_id=empresa_id)
        if config_seg and config_seg.requer_pin_cancelar_os and config_seg.pin_gerente:
            if not data.codigo_gerente:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="REQUER_APROVACAO_GERENTE")
            if not verify_password(data.codigo_gerente, config_seg.pin_gerente):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PIN_GERENTE_INVALIDO")

    # Só devolve peça ao estoque se ela chegou a sair — ou seja, se a OS estava
    # FINALIZADA. Cancelar uma OS que nunca foi finalizada não movimenta nada;
    # estornar aqui inventaria estoque que nunca saiu.
    if os_in_db.status == OrdemServicoStatus.FINALIZADA:
        _movimentar_estoque_os(db, os_in_db, saida=False, usuario_token=usuario_token)

    os_in_db.status = OrdemServicoStatus.CANCELADA

    if data.motivo:
        obs_atual = os_in_db.observacoes or ""
        os_in_db.observacoes = f"{obs_atual}\n[CANCELAMENTO] {data.motivo}".strip()

    if data.zerar_adiantamento:
        os_in_db.valor_entrada = 0
        os_in_db.forma_pagamento_entrada_id = None
    elif os_in_db.valor_entrada > 0:
        cliente = os_in_db.equipamento.cliente if os_in_db.equipamento else None
        if cliente:
            cliente.saldo_credito = (cliente.saldo_credito or 0) + os_in_db.valor_entrada

    return os_crud.update_ordem_servico(db, os_to_update=os_in_db)


def reabrir_ordem_servico(
    db: Session,
    numero_os: str,
    codigo_gerente: str | None = None,
    cliente_pagou: bool = True,
    usuario_token: dict | None = None,
) -> OSModel:
    """
    Reabre uma OS FINALIZADA ou CANCELADA.

    Limpa: status → EM_ANDAMENTO, data_finalizacao → None.

    cliente_pagou:
      - True (padrão): o valor já pago é preservado como crédito da OS
        (credito_anterior) e será abatido do novo total ao refinalizar.
      - False: o pagamento não era real (ex.: OS reaberta na hora, antes de o
        cliente pagar). Apaga os pagamentos e zera o crédito, então a OS recobra
        o valor cheio. Só use quando tiver certeza de que o dinheiro NÃO entrou —
        senão o registro do pagamento do cliente é perdido.
    """
    os_in_db = _get_os_or_raise(db, numero_os)

    if os_in_db.status not in (OrdemServicoStatus.FINALIZADA, OrdemServicoStatus.CANCELADA):
        raise os_nao_pode_reabrir_exce

    if os_in_db.funcionario:
        empresa_id = os_in_db.funcionario.empresa_id
        config_seg = config_seg_crud.get_configuracao_seguranca(db, empresa_id=empresa_id)
        if config_seg and config_seg.requer_pin_reabrir_os and config_seg.pin_gerente:
            if not codigo_gerente:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="REQUER_APROVACAO_GERENTE")
            if not verify_password(codigo_gerente, config_seg.pin_gerente):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PIN_GERENTE_INVALIDO")

    # Devolve as peças ao estoque, mas SÓ se elas tinham saído. Vindo de
    # FINALIZADA, saíram na finalização. Vindo de CANCELADA, o cancelamento já
    # estornou — estornar de novo aqui criaria estoque do nada, e o erro só
    # apareceria muito depois, na contagem física.
    if os_in_db.status == OrdemServicoStatus.FINALIZADA:
        _movimentar_estoque_os(db, os_in_db, saida=False, usuario_token=usuario_token)

    if cliente_pagou:
        # Preserva o que foi pago como crédito abatido do novo total.
        total_bruto = sum(p.valor for p in os_in_db.pagamentos) + (os_in_db.valor_entrada or 0)
        valor_total = os_in_db.valor_total or 0
        os_in_db.credito_anterior = min(total_bruto, valor_total) or None
    else:
        # Pagamento não era real: apaga os pagamentos (cascade delete-orphan) e
        # zera o crédito, para a OS recobrar o valor cheio.
        #
        # Antes de apagar, devolve ao livro o que chegou a entrar. A FK do
        # movimento é SET NULL, então as linhas ficariam para trás contando
        # dinheiro que nunca existiu, e o turno passaria a fechar com FALTA.
        # O estorno lança o contrário na data de hoje; nada é apagado do livro.
        from app.services import sessao_caixa as caixa_service
        caixa_service.estornar_pagamentos_de_os(
            db,
            os_in_db,
            list(os_in_db.pagamentos),
            operador_funcionario_id=(usuario_token or {}).get("funcionario_id"),
        )
        os_in_db.pagamentos.clear()
        os_in_db.credito_anterior = None

    os_in_db.valor_entrada = 0
    os_in_db.forma_pagamento_entrada_id = None
    os_in_db.status = OrdemServicoStatus.EM_ANDAMENTO
    os_in_db.data_finalizacao = None

    return os_crud.update_ordem_servico(db, os_to_update=os_in_db)


def get_os_abandono(db: Session, empresa_id: int, funcionario_id: int | None = None) -> list[OSModel]:
    """Retorna OS finalizadas cujo prazo de abandono já venceu, usando config da empresa."""
    from app.services.configuracao_os import get_or_create_configuracao_os
    config = get_or_create_configuracao_os(db, empresa_id)
    return os_crud.get_os_abandono(db, empresa_id, config.prazo_abandono_dias, funcionario_id=funcionario_id)


def get_os_atrasadas(db: Session, empresa_id: int, funcionario_id: int | None = None) -> list[OSModel]:
    """Retorna OS abertas com prazo de entrega vencido."""
    return os_crud.get_os_atrasadas(db, empresa_id, funcionario_id=funcionario_id)
