# ---------------------------------------------------------------------------
# ARQUIVO: schemas/movimentacao_estoque.py
# DESCRIÇÃO: Schemas Pydantic para movimentações de estoque.
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

from app.core.enum import MovimentacaoTipo, MovimentacaoOrigem


class MovimentacaoCreate(BaseModel):
    """Dados de entrada para registrar uma movimentação de estoque."""
    tipo: MovimentacaoTipo = Field(..., description="Tipo: ENTRADA, SAIDA ou AJUSTE")
    quantidade: float = Field(
        ...,
        ge=0,
        description=(
            "ENTRADA/SAIDA: unidades movimentadas (mínimo 1). "
            "AJUSTE: a quantidade FINAL contada, não a diferença."
        ),
    )
    custo_unitario: Optional[int] = Field(
        None,
        ge=0,
        description=(
            "Valor pago por unidade nesta compra, em centavos. Só faz sentido em "
            "ENTRADA: é ele que recalcula a média ponderada do produto. Omitir "
            "mantém a média intacta (caso de devolução, que não é compra)."
        ),
    )
    observacao: Optional[str] = Field(None, max_length=500, description="Motivo ou observação")

    model_config = ConfigDict(from_attributes=True)


class MovimentacaoRead(BaseModel):
    """Dados de saída de uma movimentação de estoque."""
    id: int
    produto_id: int
    produto_nome: str
    # Unidade do produto, para o painel escrever "2,5 kg" em vez de "2,5 un".
    #
    # Lida do produto no momento da consulta, e NAO desnormalizada como o
    # `produto_nome`: o nome e desnormalizado para o historico sobreviver a um
    # rename, mas a unidade descreve COMO a quantidade daquela linha deve ser
    # lida -- se ela mudar no cadastro, as linhas antigas passam a ser lidas na
    # unidade nova, que e o comportamento correto. Alem disso, evita migracao e
    # backfill num historico que ja esta em producao.
    unidade_medida: Optional[str] = None
    usuario_id: Optional[int]
    usuario_nome: str
    tipo: MovimentacaoTipo
    quantidade: float
    quantidade_anterior: float
    quantidade_posterior: float
    origem: MovimentacaoOrigem = Field(
        MovimentacaoOrigem.LEGADO,
        description="De onde veio: LEGADO, MANUAL, CADASTRO, VENDA ou ORDEM_SERVICO",
    )
    venda_id: Optional[int] = Field(None, description="Venda que causou (origem = VENDA)")
    ordem_servico_id: Optional[int] = Field(None, description="OS que causou (origem = ORDEM_SERVICO)")
    custo_unitario: Optional[int] = Field(
        None,
        description="Custo unitário congelado nesta movimentação (centavos). NULL nas linhas anteriores ao campo.",
    )
    observacao: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
