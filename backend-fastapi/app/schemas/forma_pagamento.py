# ---------------------------------------------------------------------------
# ARQUIVO: schemas/forma_pagamento.py
# DESCRICAO: Schemas Pydantic para o catálogo global de Formas de Pagamento.
#
# FormaPagamento é uma entidade do sistema (catálogo), não associada
# exclusivamente às OS. É usada por OSPagamento ao registrar pagamentos.
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional


class FormaPagamentoBase(BaseModel):
    """Campos base de uma forma de pagamento."""
    nome: str = Field(..., min_length=2, max_length=50, description="Nome da forma de pagamento (ex: Dinheiro, PIX, Cartão)")
    ativo: bool = Field(True, description="Status ativo/inativo da forma de pagamento")
    codigo_sefaz: Optional[str] = Field(
        None, max_length=2,
        description="Código SEFAZ da forma de pagamento (01-99). Obrigatório para emissão fiscal.",
    )

    @field_validator("codigo_sefaz", mode="before")
    @classmethod
    def validar_codigo_sefaz(cls, v: str | None) -> str | None:
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
                "ativo": True,
                "codigo_sefaz": "17"
            }
        }
    )


class FormaPagamentoUpdate(BaseModel):
    """Schema para atualização parcial de uma forma de pagamento."""
    nome: Optional[str] = Field(None, min_length=2, max_length=50, description="Novo nome")
    ativo: Optional[bool] = Field(None, description="Novo status ativo/inativo")
    codigo_sefaz: Optional[str] = Field(None, max_length=2, description="Código SEFAZ (01-99)")

    @field_validator("codigo_sefaz", mode="before")
    @classmethod
    def validar_codigo_sefaz(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        v = v.strip()
        if not v.isdigit() or len(v) != 2:
            raise ValueError("codigo_sefaz deve ter exatamente 2 dígitos numéricos (ex: 01, 17)")
        return v

    model_config = ConfigDict(from_attributes=True)


class FormaPagamentoRead(FormaPagamentoBase):
    """Schema de resposta completo de uma forma de pagamento."""
    id: int = Field(..., description="ID único da forma de pagamento")

    model_config = ConfigDict(from_attributes=True)
