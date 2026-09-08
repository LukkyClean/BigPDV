# ---------------------------------------------------------------------------
# ARQUIVO: schemas/forma_pagamento.py
# DESCRICAO: Schemas Pydantic para o catálogo global de Formas de Pagamento.
#
# FormaPagamento é uma entidade do sistema (catálogo), não associada
# exclusivamente às OS. É usada por OSPagamento ao registrar pagamentos.
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional


# Um mes. Prazo maior que isso nao existe em maquininha nenhuma, e o limite
# protege o Fluxo de Caixa de um digito a mais transformar um recebimento de
# amanha numa entrada daqui a tres anos.
MAX_DIAS_PARA_RECEBER = 90


class FormaPagamentoBase(BaseModel):
    """Campos base de uma forma de pagamento."""
    nome: str = Field(..., min_length=2, max_length=50, description="Nome da forma de pagamento (ex: Dinheiro, PIX, Cartão)")
    ativo: bool = Field(True, description="Status ativo/inativo da forma de pagamento")
    codigo_sefaz: Optional[str] = Field(
        None, max_length=2,
        description="Código SEFAZ da forma de pagamento (01-99). Obrigatório para emissão fiscal.",
    )
    dias_para_receber: int = Field(
        0,
        ge=0,
        le=MAX_DIAS_PARA_RECEBER,
        description=(
            "Dias até o dinheiro cair na conta. 0 (padrão) = entra na hora, que "
            "é o comportamento de sempre. Com prazo, o recebimento vira conta a "
            "receber com vencimento em D+n e entra sozinho naquele dia"
        ),
    )
    conta_bancaria_id: Optional[int] = Field(
        None,
        description=(
            "Conta em que o dinheiro desta forma cai. NULL = a principal da "
            "loja -- cartão cai no banco, dinheiro fica na gaveta"
        ),
    )

    @field_validator("codigo_sefaz", mode="before")
    @classmethod
    def validar_codigo_sefaz(cls, v: str | None) -> str | None:
        # Campo em branco vindo da tela chega como "" e significa "nao informado",
        # nao "valor invalido" -- vira None em vez de reprovar o formulario.
        if v is None or v == "":
            return None
        v = v.strip()
        if not v.isdigit() or len(v) != 2:
            raise ValueError("codigo_sefaz deve ter exatamente 2 dígitos numéricos (ex: 01, 17)")
        return v



class FormaPagamentoCreate(FormaPagamentoBase):
    """Schema para criação de uma nova forma de pagamento."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nome": "PIX",
                "ativo": True
            }
        }
    )


class FormaPagamentoUpdate(BaseModel):
    """Schema para atualização parcial de uma forma de pagamento."""
    nome: Optional[str] = Field(None, min_length=2, max_length=50, description="Novo nome")
    ativo: Optional[bool] = Field(None, description="Novo status ativo/inativo")
    codigo_sefaz: Optional[str] = Field(None, max_length=2, description="Código SEFAZ (01-99)")
    dias_para_receber: Optional[int] = Field(
        None, ge=0, le=MAX_DIAS_PARA_RECEBER,
        description="Novo prazo em dias; 0 volta a entrar na hora",
    )
    # NAO vale para o passado. Mudar o prazo hoje muda as vendas de amanha; as
    # cobrancas ja geradas ficam com o vencimento que tinham, porque o dinheiro
    # delas ja esta a caminho pela regra antiga.
    conta_bancaria_id: Optional[int] = Field(
        None, description="Nova conta de destino; use 0 para voltar à principal",
    )

    model_config = ConfigDict(from_attributes=True)

    @field_validator("codigo_sefaz", mode="before")
    @classmethod
    def validar_codigo_sefaz(cls, v: str | None) -> str | None:
        # Campo em branco vindo da tela chega como "" e significa "nao informado",
        # nao "valor invalido" -- vira None em vez de reprovar o formulario.
        if v is None or v == "":
            return None
        v = v.strip()
        if not v.isdigit() or len(v) != 2:
            raise ValueError("codigo_sefaz deve ter exatamente 2 dígitos numéricos (ex: 01, 17)")
        return v



class FormaPagamentoRead(FormaPagamentoBase):
    """Schema de resposta completo de uma forma de pagamento."""
    id: int = Field(..., description="ID único da forma de pagamento")

    model_config = ConfigDict(from_attributes=True)
