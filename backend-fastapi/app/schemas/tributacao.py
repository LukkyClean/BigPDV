# ---------------------------------------------------------------------------
# ARQUIVO: schemas/tributacao.py
# MÓDULO: Schemas Pydantic — Tributação padrão e regras por NCM
# ---------------------------------------------------------------------------
"""
DTOs da tributação da loja.

Nenhum campo é obrigatório: o vazio tem significado na cascata ("não decido
isto"). A obrigatoriedade continua onde sempre esteve — no gate de emissão,
que olha o resultado EFETIVO e não cada nível isolado.
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _digitos(valor: Optional[str], nome: str, tamanho: int) -> Optional[str]:
    if valor is None or valor == "":
        return None
    limpo = re.sub(r"\D", "", valor)
    if len(limpo) != tamanho:
        raise ValueError(f"{nome} deve conter exatamente {tamanho} dígitos (recebido: {valor!r})")
    return limpo


class CamposTributacaoBase(BaseModel):
    """Os campos que descem pela cascata."""

    cfop_padrao: Optional[str] = Field(None, max_length=4)
    origem_mercadoria: Optional[int] = Field(None, ge=0, le=8)

    cst_icms: Optional[str] = Field(None, max_length=3)
    csosn: Optional[str] = Field(None, max_length=3)
    aliquota_icms: Optional[int] = Field(None, ge=0, description="Centésimos de ponto (1800 = 18%)")
    reducao_base_icms: Optional[int] = Field(None, ge=0)
    codigo_beneficio_fiscal: Optional[str] = Field(None, max_length=10)

    cst_pis: Optional[str] = Field(None, max_length=2)
    cst_cofins: Optional[str] = Field(None, max_length=2)
    aliquota_pis: Optional[int] = Field(None, ge=0)
    aliquota_cofins: Optional[int] = Field(None, ge=0)

    c_class_trib: Optional[str] = Field(None, max_length=20)
    cst_ibs_cbs: Optional[str] = Field(None, max_length=3)
    aliquota_ibs: Optional[int] = Field(None, ge=0)
    aliquota_cbs: Optional[int] = Field(None, ge=0)
    c_benef: Optional[str] = Field(None, max_length=10)

    @field_validator("cfop_padrao")
    @classmethod
    def _valida_cfop(cls, v):
        return _digitos(v, "CFOP", 4)

    model_config = ConfigDict(from_attributes=True)


class TributacaoPadraoUpdate(CamposTributacaoBase):
    """Entrada da tela de tributação padrão da loja."""


class TributacaoPadraoRead(CamposTributacaoBase):
    id: int
    empresa_id: int
    confirmado_em: Optional[datetime] = None
    confirmado_por: Optional[str] = None
    data_atualizacao: Optional[datetime] = None


class RegraNcmUpsert(CamposTributacaoBase):
    """Entrada de uma regra por NCM. O NCM vem na URL, não no corpo."""

    cest: Optional[str] = Field(None, max_length=7)
    descricao: Optional[str] = Field(None, max_length=120)

    @field_validator("cest")
    @classmethod
    def _valida_cest(cls, v):
        return _digitos(v, "CEST", 7)


class RegraNcmRead(RegraNcmUpsert):
    id: int
    empresa_id: int
    ncm: str
    data_atualizacao: Optional[datetime] = None


class FiscalEfetivoRead(BaseModel):
    """
    A tributação que vale para um produto, com a procedência de cada campo.

    `procedencia` é o que permite a tela dizer "CSOSN 102, da tributação padrão
    da loja" — campo preenchido sem explicação, num formulário fiscal, é pior
    que campo vazio.
    """

    model_config = ConfigDict(from_attributes=True)

    ncm: Optional[str] = None
    cest: Optional[str] = None
    cfop_padrao: Optional[str] = None
    origem_mercadoria: Optional[int] = None
    unidade_tributavel: Optional[str] = None
    gtin_tributavel: Optional[str] = None
    cst_icms: Optional[str] = None
    csosn: Optional[str] = None
    aliquota_icms: Optional[int] = None
    reducao_base_icms: Optional[int] = None
    codigo_beneficio_fiscal: Optional[str] = None
    cst_pis: Optional[str] = None
    cst_cofins: Optional[str] = None
    aliquota_pis: Optional[int] = None
    aliquota_cofins: Optional[int] = None
    c_class_trib: Optional[str] = None
    cst_ibs_cbs: Optional[str] = None
    aliquota_ibs: Optional[int] = None
    aliquota_cbs: Optional[int] = None
    c_benef: Optional[str] = None

    procedencia: dict[str, str] = Field(default_factory=dict)
