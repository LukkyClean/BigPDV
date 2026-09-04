# ---------------------------------------------------------------------------
# ARQUIVO: app/schemas/venda_correcao_fiscal.py
# DESCRIÇÃO: Schema Pydantic para correção cadastral e fiscal de uma venda.
#            Permite atualizar cliente, observações e dados fiscais em vendas
#            ativas ou finalizadas, sem impactar estoque ou financeiro.
# ---------------------------------------------------------------------------

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class VendaCorrecaoFiscalPayload(BaseModel):
    """Payload para atualização cadastral/fiscal da venda para emissão de NF-e."""

    cliente_id: Optional[int] = Field(
        None,
        description="ID do cliente a ser vinculado ou substituído na venda. Envie null para desvincular.",
    )
    observacao: Optional[str] = Field(
        None,
        max_length=500,
        description="Observações gerais da venda.",
    )
    observacao_interna: Optional[str] = Field(
        None,
        max_length=500,
        description="Observação interna (não impressa na nota).",
    )
    natureza_operacao: Optional[str] = Field(
        None,
        max_length=60,
        description="Descrição da natureza da operação (ex: 'Venda de Mercadoria').",
    )
    consumidor_final: Optional[bool] = Field(
        None,
        description="Indica se a operação é para consumidor final.",
    )
    indicador_presenca: Optional[int] = Field(
        None,
        ge=0,
        le=9,
        description="1=Presencial, 2=Internet, 3=Teleatendimento, 4=Entrega, 9=Outros.",
    )
    finalidade_emissao: Optional[int] = Field(
        None,
        ge=1,
        le=4,
        description="1=Normal, 2=Complementar, 3=Ajuste, 4=Devolução/Retorno.",
    )

    model_config = ConfigDict(from_attributes=True)


class VendaCorrecaoFiscalRead(BaseModel):
    """Resposta após a correção da venda."""

    id: int
    numero_venda: Optional[int] = None
    cliente_id: Optional[int] = None
    status: str
    observacao: Optional[str] = None
    observacao_interna: Optional[str] = None
    natureza_operacao: Optional[str] = None
    consumidor_final: Optional[bool] = None
    indicador_presenca: Optional[int] = None
    finalidade_emissao: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
