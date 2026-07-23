# ---------------------------------------------------------------------------
# ARQUIVO: schemas/relatorio.py
# DESCRICAO: Schemas de resposta do modulo de Relatorios.
#            Todos os valores monetarios sao INTEIROS EM CENTAVOS.
# ---------------------------------------------------------------------------

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class FaturamentoDiaItem(BaseModel):
    """Faturamento consolidado de um dia (vendas + OS)."""
    dia: date
    total_vendas: int = Field(..., description="Faturamento de vendas no dia (centavos)")
    total_os: int = Field(..., description="Faturamento de OS no dia (centavos)")
    total_geral: int = Field(..., description="Soma vendas + OS no dia (centavos)")


class FormaPagamentoResumo(BaseModel):
    """Total recebido por forma de pagamento no periodo."""
    nome: str
    valor_total: int = Field(..., description="Total recebido nesta forma (centavos)")


class RelatorioFaturamento(BaseModel):
    """Resposta do relatorio de faturamento por periodo."""
    inicio: date
    fim: date
    faturamento_total: int = Field(..., description="Vendas + OS finalizadas no periodo (centavos)")
    faturamento_vendas: int = Field(..., description="Somente vendas (centavos)")
    faturamento_os: int = Field(..., description="Somente OS (centavos)")
    ticket_medio: int = Field(..., description="Faturamento / nº de transacoes finalizadas (centavos)")
    qtd_vendas: int = Field(..., description="Quantidade de vendas finalizadas")
    qtd_os: int = Field(..., description="Quantidade de OS finalizadas")
    por_dia: list[FaturamentoDiaItem] = Field(default_factory=list)
    formas_pagamento: list[FormaPagamentoResumo] = Field(default_factory=list)


class RankingFuncionarioItem(BaseModel):
    """Faturamento de um funcionario no periodo (base da comissao)."""
    funcionario_id: int
    nome: str
    faturamento_vendas: int = Field(..., description="Vendas finalizadas do funcionario (centavos)")
    faturamento_os: int = Field(..., description="OS finalizadas do funcionario (centavos)")
    faturamento_total: int = Field(..., description="Vendas + OS (centavos)")
    qtd_vendas: int
    qtd_os: int


class RelatorioRanking(BaseModel):
    """Ranking de funcionarios por faturamento no periodo."""
    inicio: date
    fim: date
    itens: list[RankingFuncionarioItem] = Field(default_factory=list)


class ComissaoFuncionarioItem(BaseModel):
    """Comissao apurada de um funcionario no periodo."""
    funcionario_id: int
    nome: str
    faturamento_vendas: int = Field(..., description="Base de vendas (centavos)")
    faturamento_os: int = Field(..., description="Base de OS (centavos)")
    faturamento_total: int
    percentual_venda: Optional[int] = Field(None, description="Taxa aplicada em vendas (basis points); None = sem taxa")
    percentual_servico: Optional[int] = Field(None, description="Taxa aplicada em serviços (basis points)")
    comissao_vendas: int = Field(..., description="Comissao de vendas (centavos)")
    comissao_servico: int = Field(..., description="Comissao de serviços (centavos)")
    comissao_total: int = Field(..., description="Comissao total a pagar (centavos)")
    meta_mensal: Optional[int] = Field(None, description="Meta do funcionario/cargo (centavos)")
    meta_atingida_percentual: Optional[float] = Field(None, description="% da meta atingido no período")


class RelatorioComissao(BaseModel):
    """Relatorio de comissao por funcionario no periodo."""
    inicio: date
    fim: date
    total_comissao: int = Field(..., description="Soma das comissões — total a pagar (centavos)")
    itens: list[ComissaoFuncionarioItem] = Field(default_factory=list)
