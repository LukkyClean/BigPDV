# ---------------------------------------------------------------------------
# ARQUIVO: schemas/ordem_servico.py
# DESCRICAO: Schemas Pydantic para Ordens de Serviço (OS).
#
# Hierarquia de schemas:
#   OSItemCreate/Read/Update    → itens de peças e serviços dentro de uma OS
#   OSEquipamentoCreate/Read    → equipamento registrado no ato de abertura
#   OSEquipamentoUpdate         → atualização parcial do equipamento/cliente
#   OSPagamentoCreate/Read      → pagamentos criados apenas ao finalizar
#   OSFotoRead                  → fotos de diagnóstico
#   OrdemServicoBase            → campos comuns a criação e leitura
#   OrdemServicoCreate          → payload de abertura de OS
#   OrdemServicoUpdate          → atualização parcial da OS
#   OrdemServicoRead            → resposta completa com relacionamentos
#   OrdemServicoFinalizar       → payload de finalização com pagamentos
#   OrdemServicoCancelar        → payload de cancelamento
#   OrdemServicoFilterParams    → query params de listagem
#   OrdemServicoQuery           → resposta paginada
#   OrdemServicoStats           → estatísticas agregadas
# ---------------------------------------------------------------------------

from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Sequence, List

from app.core.enum import (
    OrdemServicoItemTipo,
    OrdemServicoItemAprovacao,
    UnidadeMedida,
    OrdemServicoStatus,
    TipoEquipamento,
    OrdemServicoPrioridade,
    SituacaoEquipamento,
    JurosResponsavel,
)

from app.schemas.cliente import ClienteRead
from app.schemas.funcionario import FuncionarioRead
from app.schemas.forma_pagamento import FormaPagamentoRead
from app.schemas.pagination import PaginationBase as Pagination

from app.schemas.examples.os_payload import os_example


# ===========================================================================
# ITENS DA OS
# ===========================================================================

class OSItemBase(BaseModel):
    """Payload para adicionar um item (produto ou serviço) a uma OS."""
    tipo: OrdemServicoItemTipo = Field(..., description="Tipo do item: PRODUTO ou SERVICO")
    nome: str = Field(..., max_length=255, min_length=3, description="Descrição do item")
    unidade_medida: UnidadeMedida = Field(..., description="Unidade de medida")
    quantidade: int = Field(..., gt=0, description="Quantidade")
    valor_unitario: int = Field(..., gt=0, description="Valor unitário em centavos")

    # Aprovação e garantia por item (fluxo de orçamento / oficina).
    # Default APROVADO preserva o comportamento atual (item conta no total).
    status_aprovacao: OrdemServicoItemAprovacao = Field(
        OrdemServicoItemAprovacao.APROVADO,
        description="Status de aprovação do item. REPROVADO não entra no total da OS."
    )
    garantia_dias: Optional[int] = Field(None, ge=0, description="Garantia do item em dias (opcional)")
    garantia_km: Optional[int] = Field(None, ge=0, description="Garantia do item em KM, ex: oficina (opcional)")

    model_config = ConfigDict(from_attributes=True)

class OSItemCreate(OSItemBase):
    item_id: Optional[int] = Field(None, description="ID do item no catálogo (produto ou serviço). None para item avulso.")

class OSItemRead(OSItemBase):
    """Resposta de um item de OS. Inclui IDs de referência no catálogo."""
    id: int = Field(..., description="ID único do item na OS")
    ordem_servico_id: int = Field(..., description="ID da OS à qual o item pertence")
    produto_id: Optional[int] = Field(None, description="ID do produto no catálogo (se tipo=PRODUTO)")
    servico_id: Optional[int] = Field(None, description="ID do serviço no catálogo (se tipo=SERVICO)")
    valor_total: int = Field(..., description="Valor total do item (quantidade × valor_unitario) em centavos")


class OSItemUpdate(BaseModel):
    """Payload para atualização parcial de um item de OS. Todos os campos são opcionais."""
    nome: Optional[str] = Field(None, max_length=255, min_length=3, description="Nova descrição")
    unidade_medida: Optional[UnidadeMedida] = Field(None, description="Nova unidade de medida")
    quantidade: Optional[int] = Field(None, gt=0, description="Nova quantidade")
    valor_unitario: Optional[int] = Field(None, gt=0, description="Novo valor unitário em centavos")
    status_aprovacao: Optional[OrdemServicoItemAprovacao] = Field(None, description="Novo status de aprovação do item")
    garantia_dias: Optional[int] = Field(None, ge=0, description="Nova garantia do item em dias")
    garantia_km: Optional[int] = Field(None, ge=0, description="Nova garantia do item em KM")

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# EQUIPAMENTO DA OS
# ===========================================================================

class OSObjetoCreate(BaseModel):
    """Payload para registrar um objeto de serviço ao abrir uma OS."""
    tipo_equipamento: Optional[TipoEquipamento] = Field(None, description="Tipo do equipamento (opcional - compatibilidade)")
    marca: str = Field(..., max_length=100, description="Marca do objeto (ex: Fiat, Samsung)")
    modelo: str = Field(..., max_length=100, description="Modelo do objeto (ex: Uno, S20)")
    numero_serie: str = Field(..., max_length=100, description="Número de série ou identificador principal (ex: Placa, Serial)")
    imei: Optional[str] = Field(None, max_length=20, description="IMEI (opcional - compatibilidade)")
    cor: Optional[str] = Field(None, max_length=50, description="Cor do objeto")
    proxima_revisao_data: Optional[date] = Field(None, description="Data agendada da próxima revisão (oficina)")
    proxima_revisao_km: Optional[int] = Field(None, ge=0, description="KM alvo da próxima revisão (oficina)")
    dados_adicionais: Optional[dict] = Field(default_factory=dict, description="Campos dinâmicos adicionais (JSON)")

    model_config = ConfigDict(from_attributes=True)


class OSObjetoRead(OSObjetoCreate):
    """Resposta completa do objeto de serviço de uma OS."""
    id: int = Field(..., description="ID único do objeto")
    cliente_id: int = Field(..., description="ID do cliente proprietário do objeto")
    ativo: bool = Field(..., description="Status ativo do objeto")
    data_criacao: datetime = Field(..., description="Data de cadastro")
    data_atualizacao: datetime = Field(..., description="Data da última atualização")

    # Na resposta, o tipo é livre por segmento (ex: 'COMPUTADOR' para informática,
    # 'Veículo' para oficina). Relaxamos o enum de TI para str e coagimos o valor
    # vindo da property/shim do modelo. A informática segue recebendo os mesmos
    # valores de sempre (ex: 'COMPUTADOR').
    tipo_equipamento: Optional[str] = Field(
        None, description="Tipo do objeto (livre por segmento; ex: COMPUTADOR, Veículo)"
    )

    @field_validator("tipo_equipamento", mode="before")
    @classmethod
    def _coagir_tipo_equipamento(cls, v):
        if v is None:
            return None
        return getattr(v, "value", None) or str(v)


class OSObjetoUpdate(BaseModel):
    """Payload para atualização parcial do objeto de serviço."""
    tipo_equipamento: Optional[TipoEquipamento] = Field(None, description="Novo tipo de equipamento")
    marca: Optional[str] = Field(None, max_length=100, description="Nova marca")
    modelo: Optional[str] = Field(None, max_length=100, description="Novo modelo")
    numero_serie: Optional[str] = Field(None, max_length=100, description="Novo identificador/placa")
    imei: Optional[str] = Field(None, max_length=20, description="Novo IMEI")
    cor: Optional[str] = Field(None, max_length=50, description="Nova cor")
    cliente_id: Optional[int] = Field(None, description="Novo ID do cliente proprietário")
    proxima_revisao_data: Optional[date] = Field(None, description="Nova data da próxima revisão")
    proxima_revisao_km: Optional[int] = Field(None, ge=0, description="Novo KM alvo da próxima revisão")
    dados_adicionais: Optional[dict] = Field(None, description="Novos dados adicionais (JSON)")

    model_config = ConfigDict(from_attributes=True)


# Aliases de compatibilidade
OSEquipamentoCreate = OSObjetoCreate
OSEquipamentoRead = OSObjetoRead
OSEquipamentoUpdate = OSObjetoUpdate

# ===========================================================================
# PAGAMENTOS DA OS
# ===========================================================================

class OSPagamentoCreate(BaseModel):
    """
    Payload para registrar um pagamento.
    Pagamentos são criados exclusivamente no ato de finalização da OS.
    Uma OS pode ter múltiplos pagamentos (ex: parte em Dinheiro + parte em PIX).
    A soma dos valores deve ser exatamente igual ao valor_total da OS.
    """
    forma_pagamento_id: int = Field(..., description="ID da forma de pagamento do catálogo")
    valor: int = Field(..., gt=0, description="Valor pago pelo cliente nesta forma de pagamento (centavos)")
    juros_valor: int = Field(0, ge=0, description="Juros calculados neste pagamento (centavos)")
    juros_responsavel: JurosResponsavel = Field(
        JurosResponsavel.CLIENTE,
        description="CLIENTE: juros embutido em `valor`. LOJA: juros absorvido, fora de `valor`.",
    )
    parcelas: int = Field(1, ge=1, description="Número de parcelas (mínimo 1)")
    bandeira_cartao: Optional[str] = Field(None, max_length=50, description="Bandeira do cartão (VISA, MASTERCARD, etc.)")
    vencimento: Optional[date] = Field(None, description="Data de vencimento do pagamento (ex: boletos)")
    detalhes: Optional[dict] = Field(None, description="Dados adicionais do pagamento em formato JSON")

    model_config = ConfigDict(from_attributes=True)


class OSPagamentoRead(BaseModel):
    """Resposta de um pagamento de OS. Inclui dados aninhados da forma de pagamento."""
    id: int = Field(..., description="ID único do pagamento")
    ordem_servico_id: int = Field(..., description="ID da OS associada")
    forma_pagamento: FormaPagamentoRead = Field(..., description="Forma de pagamento utilizada")
    valor: int = Field(..., description="Valor pago pelo cliente (centavos)")
    juros_valor: int = Field(0, description="Juros calculados neste pagamento (centavos)")
    juros_responsavel: JurosResponsavel = Field(
        JurosResponsavel.CLIENTE, description="Quem arca com o juros deste pagamento"
    )
    parcelas: int = Field(..., description="Número de parcelas")
    bandeira_cartao: Optional[str] = Field(None, description="Bandeira do cartão")
    vencimento: Optional[date] = Field(None, description="Data de vencimento do pagamento")
    detalhes: Optional[dict] = Field(None, description="Dados adicionais")

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# FOTOS DA OS
# ===========================================================================

class OSFotoRead(BaseModel):
    """Resposta de uma foto de diagnóstico de OS."""
    id: int = Field(..., description="ID único da foto")
    ordem_servico_id: int = Field(..., description="ID da OS associada")
    nome_arquivo: str = Field(..., description="Nome original do arquivo enviado")
    url: str = Field(..., description="Caminho/URL do arquivo no servidor")
    data_criacao: datetime = Field(..., description="Data de upload")

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# ORDEM DE SERVICO — BASE, CREATE, UPDATE, READ
# ===========================================================================

class OrdemServicoBase(BaseModel):
    """Campos base compartilhados entre criação e leitura de OS."""

    # Status e prioridade
    prioridade: OrdemServicoPrioridade = Field(..., description="Prioridade da OS: BAIXA, NORMAL, ALTA ou URGENTE")

    # Descrição técnica
    defeito_relatado: str = Field(..., max_length=500, description="Defeito descrito pelo cliente")
    diagnostico: Optional[str] = Field(None, max_length=500, description="Diagnóstico técnico realizado")
    solucao: Optional[str] = Field(None, max_length=500, description="Solução aplicada")

    # Observações operacionais
    senha_aparelho: Optional[str] = Field(None, max_length=100, description="Senha de desbloqueio do aparelho (retrocompatibilidade)")
    acessorios: Optional[str] = Field(None, max_length=500, description="Acessórios entregues (retrocompatibilidade)")
    condicoes_aparelho: Optional[str] = Field(None, max_length=500, description="Estado físico do aparelho (retrocompatibilidade)")
    observacoes: Optional[str] = Field(None, max_length=500, description="Observações gerais")

    # Esquema Dinâmico
    dados_adicionais: Optional[dict] = Field(default_factory=dict, description="Dados adicionais específicos do segmento (JSON)")

    # Financeiro
    desconto: Optional[int] = Field(None, ge=0, description="Desconto aplicado em centavos")
    valor_entrada: Optional[int] = Field(None, ge=0, description="Valor de entrada/adiantamento em centavos")
    taxa_entrega: Optional[int] = Field(None, ge=0, description="Taxa de entrega/frete em centavos")
    acrescimo: Optional[int] = Field(None, ge=0, description="Acréscimo de juros/cartão em centavos")

    # Prazos e garantia
    garantia: Optional[str] = Field(None, max_length=20, description="Prazo de garantia (ex: '90 dias')")
    data_previsao: Optional[datetime] = Field(None, description="Data prevista para conclusão")

    model_config = ConfigDict(from_attributes=True)


class OrdemServicoCreate(OrdemServicoBase):
    """
    Payload completo para abertura de uma nova OS.
    Cria a OS, o objeto associado e os itens iniciais em uma única transação.
    """
    # Vínculos
    cliente_id: int = Field(..., description="ID do cliente que trouxe o objeto/equipamento")
    funcionario_id: Optional[int] = Field(None, description="ID do funcionário responsável. Se omitido, fica sem responsável.")

    # Dados aninhados criados junto com a OS
    objeto: Optional[OSObjetoCreate] = Field(None, description="Dados do objeto a ser cadastrado")
    equipamento: Optional[OSEquipamentoCreate] = Field(None, description="Dados do equipamento a ser cadastrado (retrocompatibilidade)")
    itens: Sequence[OSItemCreate] = Field(default_factory=list, description="Lista de itens/serviços da OS")

    # Crédito
    usar_credito_cliente: Optional[bool] = Field(False, description="Se True, deduz valor_entrada do saldo de crédito do cliente")

    model_config = ConfigDict(
        json_schema_extra=os_example,
    )


class OrdemServicoUpdate(BaseModel):
    """
    Payload para atualização parcial da OS. Todos os campos são opcionais.
    Não é permitido atualizar OS com status FINALIZADA ou CANCELADA.

    Para alterar o funcionário responsável, informe funcionario_id.
    Para alterar status de forma manual (ex: ABERTA → EM_ANDAMENTO), informe status.
    Transições FINALIZADA e CANCELADA têm endpoints dedicados: /finalizar e /cancelar.
    """
    # Status e prioridade
    prioridade: Optional[OrdemServicoPrioridade] = Field(None, description="Nova prioridade")
    status: Optional[OrdemServicoStatus] = Field(
        None,
        description="Novo status manual. Não use FINALIZADA ou CANCELADA aqui — use /finalizar ou /cancelar."
    )

    # Descrição técnica
    defeito_relatado: Optional[str] = Field(None, max_length=500, description="Novo defeito relatado")
    diagnostico: Optional[str] = Field(None, max_length=500, description="Novo diagnóstico")
    solucao: Optional[str] = Field(None, max_length=500, description="Nova solução")

    # Observações
    senha_aparelho: Optional[str] = Field(None, max_length=100, description="Nova senha do aparelho")
    acessorios: Optional[str] = Field(None, max_length=500, description="Novos acessórios")
    condicoes_aparelho: Optional[str] = Field(None, max_length=500, description="Novas condições do aparelho")
    observacoes: Optional[str] = Field(None, max_length=500, description="Novas observações gerais")
    dados_adicionais: Optional[dict] = Field(None, description="Novos dados adicionais específicos do segmento (JSON)")

    # Financeiro e datas
    desconto: Optional[int] = Field(None, ge=0, description="Novo desconto em centavos (recalcula valor_total automaticamente)")
    valor_entrada: Optional[int] = Field(None, ge=0, description="Novo valor de entrada/adiantamento em centavos")
    garantia: Optional[str] = Field(None, max_length=20, description="Nova garantia")
    data_previsao: Optional[datetime] = Field(None, description="Nova data prevista")
    funcionario_id: Optional[int] = Field(None, description="ID do novo funcionário responsável")

    model_config = ConfigDict(from_attributes=True)


class OrdemServicoRead(OrdemServicoBase):
    """Resposta completa de uma OS com todos os relacionamentos carregados."""

    # Identificação
    id: int = Field(..., description="ID interno da OS")
    numero_os: str = Field(..., description="Número sequencial público (ex: OS-2026-000001)")

    # Estado
    status: OrdemServicoStatus = Field(..., description="Status atual da OS")
    situacao_equipamento: Optional[SituacaoEquipamento] = Field(None, description="Situação final do equipamento: REPARADO, SEM_REPARO ou CONDENADO")

    # Financeiro
    valor_bruto: int = Field(..., description="Soma dos valores dos itens antes do desconto (centavos)")
    valor_total: int = Field(..., description="Valor final após desconto (centavos)")
    taxa_entrega: int = Field(0, description="Taxa de entrega/frete (centavos)")
    acrescimo: int = Field(0, description="Acréscimo de juros/cartão (centavos)")
    credito_anterior: Optional[int] = Field(None, description="Crédito efetivo da finalização anterior ao reabrir (centavos)")

    # Datas
    data_finalizacao: Optional[datetime] = Field(None, description="Data de finalização efetiva")
    data_criacao: datetime = Field(..., description="Data de abertura da OS")
    data_atualizacao: datetime = Field(..., description="Data da última modificação")

    # Status lógico
    ativo: bool = Field(..., description="Indica se a OS está ativa (False = cancelada/desativada)")

    # Relacionamentos
    cliente: ClienteRead = Field(..., description="Cliente proprietário")
    funcionario: Optional[FuncionarioRead] = Field(None, description="Funcionário responsável")
    objeto: OSObjetoRead = Field(..., description="Objeto de serviço associado")
    equipamento: Optional[OSEquipamentoRead] = Field(None, description="Equipamento em serviço (retrocompatibilidade)")
    itens: Sequence[OSItemRead] = Field(..., description="Itens e serviços da OS")
    pagamentos: Sequence[OSPagamentoRead] = Field(default=[], description="Pagamentos registrados (populado após finalização)")
    fotos: Sequence[OSFotoRead] = Field(default=[], description="Fotos de diagnóstico da OS")


# ===========================================================================
# AÇÕES DE STATUS
# ===========================================================================

class OrdemServicoFinalizar(BaseModel):
    """
    Payload para finalizar uma OS.

    Regras de negócio:
    - A soma de todos os pagamentos.valor deve ser igual ao valor_total da OS.
    - Cada forma_pagamento_id deve existir e estar ativo no catálogo.
    - A OS não pode estar com status FINALIZADA ou CANCELADA.
    - Uma OS só é finalizada se for integralmente paga.
    """
    situacao_equipamento: Optional[SituacaoEquipamento] = Field(None, description="Situação final do equipamento: REPARADO, SEM_REPARO ou CONDENADO")
    garantia: Optional[str] = Field(None, max_length=20, description="Prazo de garantia do serviço (ex: '90 dias', '6 meses')")
    solucao: Optional[str] = Field(None, max_length=500, description="Descrição da solução aplicada")
    observacoes: Optional[str] = Field(None, max_length=500, description="Observações adicionais de finalização")
    desconto: Optional[int] = Field(None, ge=0, description="Desconto final em centavos (recalcula valor_total se informado)")
    valor_entrada: Optional[int] = Field(None, ge=0, description="Valor de entrada/adiantamento em centavos (abatido do valor a pagar)")
    taxa_entrega: Optional[int] = Field(None, ge=0, description="Taxa de entrega/frete em centavos")
    acrescimo: Optional[int] = Field(None, ge=0, description="Acréscimo de juros/cartão em centavos")
    pagamentos: List[OSPagamentoCreate] = Field(
        default=[],
        description="Lista de pagamentos. A soma dos valores deve ser igual ao valor_total da OS."
    )
    zerar_adiantamento: Optional[bool] = Field(
        False,
        description="Se True, o adiantamento foi devolvido em dinheiro. Se False, vira crédito para o cliente (apenas para SEM_REPARO/CONDENADO)."
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "solucao": "Substituição do módulo frontal e reconexão do flex do display.",
                "observacoes": "Testado e aprovado pelo cliente.",
                "desconto": 0,
                "pagamentos": [
                    {"forma_pagamento_id": 1, "valor": 45000, "parcelas": 1},
                    {"forma_pagamento_id": 2, "valor": 12000, "parcelas": 1}
                ]
            }
        }
    )


class OrdemServicoCancelar(BaseModel):
    """Payload para cancelar uma OS. O motivo é registrado nas observações da OS."""
    motivo: Optional[str] = Field(None, max_length=500, description="Motivo do cancelamento (acrescentado às observações)")
    zerar_adiantamento: Optional[bool] = Field(False, description="Se True, zera o valor_entrada (adiantamento devolvido ao cliente)")
    codigo_gerente: Optional[str] = Field(None, description="PIN do gerente para aprovar cancelamento")

    model_config = ConfigDict(
        json_schema_extra={"example": {"motivo": "Cliente desistiu do serviço.", "zerar_adiantamento": True}}
    )


class OrdemServicoReabrir(BaseModel):
    """Payload para reabrir uma OS."""
    codigo_gerente: Optional[str] = Field(None, description="PIN do gerente para aprovar reabertura")
    cliente_pagou: bool = Field(
        True,
        description=(
            "Se o cliente já pagou o valor da finalização anterior. True (padrão): o "
            "valor pago é preservado como crédito da OS e abatido do novo total. False: "
            "o pagamento não era real (ex.: reaberta na hora, antes de o cliente pagar) — "
            "os pagamentos são apagados e a OS recobra o valor cheio."
        ),
    )


# ===========================================================================
# FILTROS E PAGINAÇÃO
# ===========================================================================

class OrdemServicoFilterParams(BaseModel):
    """Query parameters para listagem e busca de OS."""
    search: Optional[str] = Field(
        None,
        description="Busca por número da OS, nome ou razão social do cliente"
    )
    status: Optional[OrdemServicoStatus] = Field(
        None,
        description="Filtro por status: ABERTA, EM_ANDAMENTO, AGUARDANDO_PECAS, AGUARDANDO_APROVACAO, AGUARDANDO_RETIRADA, FINALIZADA ou CANCELADA"
    )
    priority_sort: Optional[bool] = Field(
        None,
        description="Se true, ordena por prioridade (URGENTE → ALTA → NORMAL → BAIXA)"
    )


class OrdemServicoQuery(Pagination):
    """Resposta paginada de listagem de OS."""
    filters: OrdemServicoFilterParams
    items: Sequence[OrdemServicoRead]


# ===========================================================================
# ESTATÍSTICAS
# ===========================================================================

class OrdemServicoStats(BaseModel):
    """Estatísticas agregadas das Ordens de Serviço."""
    total: int = Field(..., description="Total de OS no sistema")
    abertas: int = Field(..., description="OS com status ABERTA")
    finalizadas: int = Field(..., description="OS com status FINALIZADA")
    ticket_medio: int = Field(..., description="Valor médio das OS finalizadas em centavos")
