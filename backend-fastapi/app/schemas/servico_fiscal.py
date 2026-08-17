# ---------------------------------------------------------------------------
# ARQUIVO: app/schemas/servico_fiscal.py
# DESCRIÇÃO: Schemas Pydantic para dados fiscais de serviço (tabela servico_fiscal).
#
# Validações de formato (Camada 1) — garantem que somente dados com estrutura
# correta cheguem ao banco. A obrigatoriedade dos campos para emissão fiscal
# é verificada na service layer, apenas no momento de emissão.
# ---------------------------------------------------------------------------

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _apenas_digitos(v: str) -> str:
    return re.sub(r"\D", "", v)


class ServicoFiscalBase(BaseModel):
    # --- Campos NFSe ---
    codigo_servico_lc116: Optional[str] = Field(
        None,
        max_length=10,
        description="Item da Lista de Serviços LC 116/2003 (ex: '1401' ou '14.01')",
    )
    cnae: Optional[str] = Field(
        None,
        max_length=7,
        description="Código CNAE com 7 dígitos numéricos (ex: '9512600')",
    )
    aliquota_iss: Optional[int] = Field(
        None,
        ge=0,
        le=10000,
        description="Alíquota ISS em centésimos de ponto percentual (500 = 5,00%)",
    )
    codigo_tributacao_municipio: Optional[str] = Field(
        None,
        max_length=20,
        description="Código de tributação no município (varia por prefeitura)",
    )

    # --- Campos NF-e ---
    cfop_padrao: Optional[str] = Field(
        None,
        max_length=4,
        description="CFOP para NF-e que inclua serviço (ex: '3307')",
    )
    cst_icms: Optional[str] = Field(
        None,
        max_length=3,
        description="CST ICMS para regime Normal",
    )
    csosn: Optional[str] = Field(
        None,
        max_length=3,
        description="CSOSN para Simples Nacional",
    )
    unidade_tributavel: Optional[str] = Field(
        None,
        max_length=6,
        description="Unidade tributável (ex: 'UN', 'H')",
    )

    # --- Reforma Tributária (IBS/CBS) ---
    c_class_trib: Optional[str] = Field(
        None, max_length=20,
        description="Código de Classificação Tributária IBS/CBS.",
    )
    cst_ibs_cbs: Optional[str] = Field(
        None, max_length=3,
        description="CST IBS/CBS (2 ou 3 dígitos).",
    )
    aliquota_ibs: Optional[int] = Field(
        None, ge=0, le=10000,
        description="Alíquota IBS em centésimos de ponto percentual (500 = 5,00%)",
    )
    aliquota_cbs: Optional[int] = Field(
        None, ge=0, le=10000,
        description="Alíquota CBS em centésimos de ponto percentual (500 = 5,00%)",
    )
    c_benef: Optional[str] = Field(
        None, max_length=10,
        description="Código de Benefício Fiscal IBS/CBS.",
    )

    @field_validator("codigo_servico_lc116", mode="before")
    @classmethod
    def validar_codigo_lc116(cls, v):
        """Remove pontos (aceita '14.01'), valida 2–5 dígitos numéricos."""
        if v is None or v == "":
            return v
        digitos = _apenas_digitos(str(v))
        if not (2 <= len(digitos) <= 5):
            raise ValueError("Código LC 116 deve ter entre 2 e 5 dígitos numéricos (ex: '1401' ou '14.01')")
        return digitos

    @field_validator("cnae", mode="before")
    @classmethod
    def validar_cnae(cls, v):
        """Exatamente 7 dígitos numéricos."""
        if v is None or v == "":
            return v
        digitos = _apenas_digitos(str(v))
        if len(digitos) != 7:
            raise ValueError(f"CNAE deve ter exatamente 7 dígitos numéricos (recebido: {len(digitos)})")
        return digitos

    @field_validator("cfop_padrao", mode="before")
    @classmethod
    def validar_cfop(cls, v):
        """Exatamente 4 dígitos numéricos."""
        if v is None or v == "":
            return v
        digitos = _apenas_digitos(str(v))
        if len(digitos) != 4:
            raise ValueError(f"CFOP deve ter exatamente 4 dígitos numéricos (recebido: {len(digitos)})")
        return digitos

    @field_validator("cst_icms", mode="before")
    @classmethod
    def validar_cst_icms(cls, v):
        """2 ou 3 dígitos — zero-pad para 3."""
        if v is None or v == "":
            return v
        digitos = _apenas_digitos(str(v))
        if len(digitos) == 2:
            return digitos.zfill(3)
        if len(digitos) == 3:
            return digitos
        raise ValueError("CST ICMS deve ter 2 ou 3 dígitos numéricos")

    @field_validator("csosn", mode="before")
    @classmethod
    def validar_csosn(cls, v):
        """Exatamente 3 dígitos numéricos."""
        if v is None or v == "":
            return v
        digitos = _apenas_digitos(str(v))
        if len(digitos) != 3:
            raise ValueError(f"CSOSN deve ter exatamente 3 dígitos numéricos (recebido: {len(digitos)})")
        return digitos

    @field_validator("c_class_trib", mode="before")
    @classmethod
    def validar_c_class_trib(cls, v):
        if v is None or v == "":
            return None
        return str(v).strip()

    @field_validator("cst_ibs_cbs", mode="before")
    @classmethod
    def validar_cst_ibs_cbs(cls, v):
        if v is None or v == "":
            return None
        digitos = _apenas_digitos(str(v))
        if len(digitos) not in (2, 3):
            raise ValueError(f"CST IBS/CBS deve ter 2 ou 3 dígitos numéricos (recebido: {v!r})")
        return digitos.zfill(3)

    @field_validator("c_benef", mode="before")
    @classmethod
    def validar_c_benef(cls, v):
        if v is None or v == "":
            return None
        return str(v).strip()


class ServicoFiscalCreate(ServicoFiscalBase):
    pass


class ServicoFiscalUpdate(ServicoFiscalBase):
    pass


class ServicoFiscalRead(ServicoFiscalBase):
    id: int
    servico_id: int
    data_atualizacao: datetime

    model_config = ConfigDict(from_attributes=True)
