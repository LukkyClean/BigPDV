# ---------------------------------------------------------------------------
# ARQUIVO: schemas/dashboard.py
# DESCRICAO: Schemas Pydantic para os endpoints do Dashboard.
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, Literal


# ===========================================================================
# Stats Cards
# ===========================================================================

class DashboardStats(BaseModel):
    # Numero-heroi: faturamento total da loja = vendas + OS finalizadas no periodo.
    faturamento_total: int = Field(0, description="Faturamento total (vendas + OS finalizadas) no periodo (centavos)")
    faturamento_total_variacao: float = Field(0.0, description="Variacao percentual vs periodo anterior")

    vendas_total: int = Field(0, description="Valor total de vendas finalizadas no periodo (centavos)")
    vendas_total_variacao: float = Field(0.0, description="Variacao percentual vs periodo anterior")

    os_total: int = Field(0, description="Faturamento de OS finalizadas no periodo (centavos)")
    os_total_variacao: float = Field(0.0, description="Variacao percentual vs periodo anterior")

    os_count: int = Field(0, description="Quantidade de OS FINALIZADAS no periodo (mesma ancora do os_total)")
    os_count_variacao: float = Field(0.0, description="Variacao percentual vs periodo anterior")

    novos_clientes: int = Field(0, description="Novos clientes cadastrados no periodo")
    novos_clientes_variacao: float = Field(0.0, description="Variacao percentual vs periodo anterior")

    ticket_medio: int = Field(0, description="Ticket medio geral combinado vendas + OS (centavos)")
    ticket_medio_variacao: float = Field(0.0, description="Variacao percentual vs periodo anterior")


# ===========================================================================
# Tendencia — serie de faturamento por dia (grafico)
# ===========================================================================

class TendenciaDiaItem(BaseModel):
    dia: date = Field(..., description="Dia da serie (YYYY-MM-DD)")
    total_vendas: int = Field(0, description="Faturamento de vendas no dia (centavos)")
    total_os: int = Field(0, description="Faturamento de OS no dia (centavos)")
    total_geral: int = Field(0, description="Soma vendas + OS no dia (centavos)")


class TendenciaResponse(BaseModel):
    items: list[TendenciaDiaItem] = Field(default_factory=list)


# ===========================================================================
# OS Vencendo
# ===========================================================================

class OSVencendoItem(BaseModel):
    numero_os: str = Field(..., description="Numero sequencial da OS")
    cliente_nome: str = Field(..., description="Nome do cliente vinculado")
    defeito_relatado: str = Field(..., description="Defeito relatado pelo cliente")
    data_previsao: datetime = Field(..., description="Data prevista para conclusao")
    urgencia: Literal["vermelho", "amarelo", "verde"] = Field(..., description="Faixa de urgencia")


class OSVencendoResponse(BaseModel):
    items: list[OSVencendoItem] = Field(default_factory=list)


# ===========================================================================
# Estoque Baixo
# ===========================================================================

class EstoqueBaixoItem(BaseModel):
    produto_id: int = Field(..., description="ID do produto")
    nome: str = Field(..., description="Nome do produto")
    quantidade: int = Field(..., description="Quantidade atual em estoque")
    quantidade_minima: Optional[int] = Field(None, description="Quantidade minima configurada")
    status: Literal["zerado", "baixo"] = Field(..., description="Status do estoque")


class EstoqueBaixoResponse(BaseModel):
    items: list[EstoqueBaixoItem] = Field(default_factory=list)


# ===========================================================================
# Ultimas Vendas
# ===========================================================================

class UltimaVendaItem(BaseModel):
    id: int = Field(..., description="ID da venda")
    cliente_nome: Optional[str] = Field(None, description="Nome do cliente")
    total: int = Field(0, description="Total da venda (centavos)")
    status: str = Field(..., description="Status da venda")
    criado_em: datetime = Field(..., description="Data de criacao")


class UltimasVendasResponse(BaseModel):
    items: list[UltimaVendaItem] = Field(default_factory=list)


# ===========================================================================
# Meu Resumo (Dashboard do Funcionario)
# ===========================================================================

class MeuResumoStats(BaseModel):
    # Numero-heroi pessoal: meu faturamento = minhas vendas + minhas OS finalizadas.
    meu_faturamento: int = Field(0, description="Meu faturamento (minhas vendas + minhas OS finalizadas) no periodo (centavos)")
    minhas_vendas_valor: int = Field(0, description="Total em centavos das vendas finalizadas pelo funcionario no periodo")
    minhas_vendas_count: int = Field(0, description="Quantidade de vendas finalizadas pelo funcionario no periodo")
    minhas_os_valor: int = Field(0, description="Faturamento das OS finalizadas pelo funcionario no periodo (centavos)")
    minhas_os_abertas: int = Field(0, description="OS em andamento atribuidas ao funcionario")
    minhas_os_concluidas: int = Field(0, description="OS finalizadas pelo funcionario no periodo")


# ===========================================================================
# Minha Fila (OS abertas do funcionario)
# ===========================================================================

class MinhaFilaItem(BaseModel):
    numero_os: str
    cliente_nome: str
    defeito_relatado: str
    prioridade: str
    status: str
    data_previsao: Optional[datetime]


class MinhaFilaResponse(BaseModel):
    items: list[MinhaFilaItem] = Field(default_factory=list)


# ===========================================================================
# OS Atrasadas
# ===========================================================================

class OSAtrasadaItem(BaseModel):
    numero_os: str
    cliente_nome: str
    defeito_relatado: str
    data_previsao: datetime
    dias_atraso: int


class OSAtrasadaResponse(BaseModel):
    items: list[OSAtrasadaItem] = Field(default_factory=list)
    total: int = Field(0)


# ===========================================================================
# OS Aguardando Retirada
# ===========================================================================

class OSAguardandoRetiradaItem(BaseModel):
    numero_os: str
    cliente_nome: str
    equipamento: str
    data_finalizacao: Optional[datetime]


class OSAguardandoRetiradaResponse(BaseModel):
    items: list[OSAguardandoRetiradaItem] = Field(default_factory=list)


# ===========================================================================
# Atividade de Hoje
# ===========================================================================

class AtividadeItem(BaseModel):
    tipo: Literal["venda", "os"]
    referencia: str
    cliente_nome: Optional[str]
    valor: int = Field(0)
    status: str
    horario: datetime


class AtividadeHojeResponse(BaseModel):
    items: list[AtividadeItem] = Field(default_factory=list)


# ===========================================================================
# Master — Ranking de funcionarios
# ===========================================================================

class RankingFuncionarioItem(BaseModel):
    posicao: int
    id: int
    nome: str
    total_vendas_valor: int
    total_os_valor: int = Field(0, description="Faturamento de OS finalizadas no periodo (centavos)")
    total_geral: int = Field(0, description="Faturamento total (vendas + OS) — base do ranking (centavos)")
    qtd_vendas: int
    qtd_os_fechadas: int


class RankingFuncionariosResponse(BaseModel):
    items: list[RankingFuncionarioItem] = Field(default_factory=list)


# ===========================================================================
# Master — OS por status
# ===========================================================================

class OSPorStatusItem(BaseModel):
    status: str
    status_label: str
    count: int


class OSPorStatusResponse(BaseModel):
    items: list[OSPorStatusItem] = Field(default_factory=list)
    total_ativas: int = Field(0)


# ===========================================================================
# Master — Formas de pagamento
# ===========================================================================

class FormaPagamentoItem(BaseModel):
    nome: str
    valor_total: int


class FormasPagamentoResponse(BaseModel):
    items: list[FormaPagamentoItem] = Field(default_factory=list)
    total: int = Field(0)


# ===========================================================================
# Master — OS atrasadas da empresa
# ===========================================================================

class OSAtrasadaEmpresaItem(BaseModel):
    numero_os: str
    cliente_nome: str
    funcionario_nome: Optional[str]
    defeito_relatado: str
    data_previsao: datetime
    dias_atraso: int


class OSAtrasadaEmpresaResponse(BaseModel):
    items: list[OSAtrasadaEmpresaItem] = Field(default_factory=list)
    total: int = Field(0)
