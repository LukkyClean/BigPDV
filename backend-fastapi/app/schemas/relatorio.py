# ---------------------------------------------------------------------------
# ARQUIVO: schemas/relatorio.py
# DESCRICAO: Schemas de resposta do modulo de Relatorios.
#            Todos os valores monetarios sao INTEIROS EM CENTAVOS.
# ---------------------------------------------------------------------------

from datetime import date
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
