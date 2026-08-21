from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ConfiguracaoVendasRead(BaseModel):
    id: int
    empresa_id: int

    permitir_desconto: bool
    desconto_maximo_percent: int
    exigir_cliente_identificado: bool
    valor_minimo_venda: int
    permitir_parcelamento: bool
    parcelas_maximas: int

    # Controle de caixa. Sao lidas pela TELA DE VENDAS, e nao so pela de
    # configuracoes: e por `controlar_caixa` que o PDV decide se mostra o botao
    # do caixa. Sem expor aqui, o frontend nao teria como saber e o caixa
    # apareceria para todo mundo.
    controlar_caixa: bool
    exigir_caixa_aberto: bool
    fechamento_cego: bool
    requer_pin_abrir_caixa: bool

    data_atualizacao: datetime

    model_config = {"from_attributes": True}


class ConfiguracaoVendasUpdate(BaseModel):
    permitir_desconto: Optional[bool] = None
    desconto_maximo_percent: Optional[int] = Field(None, ge=0, le=100)
    exigir_cliente_identificado: Optional[bool] = None
    valor_minimo_venda: Optional[int] = Field(None, ge=0)
    permitir_parcelamento: Optional[bool] = None
    parcelas_maximas: Optional[int] = Field(None, ge=1, le=48)

    controlar_caixa: Optional[bool] = None
    exigir_caixa_aberto: Optional[bool] = None
    fechamento_cego: Optional[bool] = None
    requer_pin_abrir_caixa: Optional[bool] = None
