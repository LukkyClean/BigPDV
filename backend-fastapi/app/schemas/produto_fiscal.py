# ---------------------------------------------------------------------------
# ARQUIVO: schemas/produto_fiscal.py
# MÓDULO: Schemas Pydantic — Dados Fiscais de Produto
# DESCRIÇÃO: DTOs para leitura e escrita da tabela satélite 'produto_fiscal'.
#
# Camada 1 de validação (doc. de design §5.2):
#   Valida formato dos campos fiscais em todo save, independente de emissão.
#   A obrigatoriedade condicional (produto sem NCM bloqueando emissão) fica
#   na service layer — aqui todos os campos são opcionais.
# ---------------------------------------------------------------------------

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Helpers de validação de formato
# ---------------------------------------------------------------------------

def _apenas_digitos(valor: str, nome: str, tamanho: int) -> str:
    """Garante que o valor contém exatamente `tamanho` dígitos numéricos."""
    limpo = re.sub(r"\D", "", valor)
    if len(limpo) != tamanho:
        raise ValueError(f"{nome} deve conter exatamente {tamanho} dígitos numéricos (recebido: {valor!r})")
    return limpo


def _digitos_entre(valor: str, nome: str, minimo: int, maximo: int) -> str:
    """Garante que o valor contém entre `minimo` e `maximo` dígitos numéricos."""
    limpo = re.sub(r"\D", "", valor)
    if not (minimo <= len(limpo) <= maximo):
        raise ValueError(f"{nome} deve conter entre {minimo} e {maximo} dígitos numéricos (recebido: {valor!r})")
    return limpo


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ProdutoFiscalBase(BaseModel):
    """Campos fiscais compartilhados entre criação e atualização."""

    ncm: Optional[str] = Field(
        None,
        max_length=8,
        description="NCM — Nomenclatura Comum do Mercosul (8 dígitos numéricos).",
        examples=["09012100"],
    )
    cest: Optional[str] = Field(
        None,
        max_length=7,
        description="CEST — Código Especificador da Substituição Tributária (7 dígitos).",
        examples=["0300400"],
    )
    cfop_padrao: Optional[str] = Field(
        None,
        max_length=4,
        description="CFOP padrão da operação (4 dígitos).",
        examples=["5102"],
    )
    origem_mercadoria: Optional[int] = Field(
        None,
        ge=0,
        le=8,
        description=(
            "Código de origem da mercadoria: "
            "0=Nacional, 1=Estrangeira-importação direta, 2=Estrangeira-adquirida no mercado interno, "
            "3=Nacional com > 40% de conteúdo estrangeiro, 4=Nacional produção conforme Decreto 6006, "
            "5=Nacional com < 40% de conteúdo estrangeiro, 6=Estrangeira importação direta sem similar, "
            "7=Estrangeira adquirida no mercado interno sem similar, 8=Nacional com produção na ZFM."
        ),
    )
    unidade_tributavel: Optional[str] = Field(
        None,
        max_length=6,
        description="Unidade tributável (ex: UN, KG, LT). Pode diferir da unidade comercial.",
        examples=["UN"],
    )
    gtin_tributavel: Optional[str] = Field(
        None,
        max_length=14,
        description="GTIN tributável — EAN-8 (8 dígitos) ou EAN-13/EAN-14 (13-14 dígitos).",
        examples=["7891000315507"],
    )
    cst_icms: Optional[str] = Field(
        None,
        max_length=3,
        description="CST de ICMS (3 dígitos) — para regime Normal (Lucro Presumido/Real).",
        examples=["000"],
    )
    csosn: Optional[str] = Field(
        None,
        max_length=3,
        description="CSOSN (3 dígitos) — para Simples Nacional.",
        examples=["102"],
    )

    # --- Alíquotas (overrides — nullable = usa padrão da UF) ---

    aliquota_icms: Optional[int] = Field(
        None, ge=0, le=10000,
        description="Alíquota ICMS em centésimos de pp (1800 = 18,00%). Override do padrão da UF.",
    )
    reducao_base_icms: Optional[int] = Field(
        None, ge=0, le=10000,
        description="Percentual de redução da base de cálculo ICMS em centésimos (4112 = 41,12%). Usado com CST 20.",
    )
    codigo_beneficio_fiscal: Optional[str] = Field(
        None, max_length=10,
        description="Código de Benefício Fiscal (cBenef). Obrigatório com CST 20 em SP, PR, RS, SC, GO.",
        examples=["SP000001"],
    )
    aliquota_pis: Optional[int] = Field(
        None, ge=0, le=10000,
        description="Alíquota PIS em centésimos de pp (165 = 1,65%). Override do padrão da UF.",
    )
    aliquota_cofins: Optional[int] = Field(
        None, ge=0, le=10000,
        description="Alíquota COFINS em centésimos de pp (760 = 7,60%). Override do padrão da UF.",
    )
    cst_pis: Optional[str] = Field(
        None, max_length=2,
        description="CST PIS (2 dígitos). Ex: 01=Tributável, 04=Não tributável, 06=Alíquota zero.",
        examples=["01"],
    )
    cst_cofins: Optional[str] = Field(
        None, max_length=2,
        description="CST COFINS (2 dígitos). Ex: 01=Tributável, 04=Não tributável, 06=Alíquota zero.",
        examples=["01"],
    )

    # --- Reforma Tributária (IBS/CBS) ---

    c_class_trib: Optional[str] = Field(
        None, max_length=20,
        description="Código de Classificação Tributária IBS/CBS.",
        examples=["01"],
    )
    cst_ibs_cbs: Optional[str] = Field(
        None, max_length=3,
        description="CST IBS/CBS (2 ou 3 dígitos).",
        examples=["000"],
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
        examples=["IBS12345"],
    )

    # -----------------------------------------------------------------------
    # Validadores de formato (Camada 1)
    # -----------------------------------------------------------------------

    @field_validator("ncm", mode="before")
    @classmethod
    def validar_ncm(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        return _apenas_digitos(v, "NCM", 8)

    @field_validator("cest", mode="before")
    @classmethod
    def validar_cest(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        return _apenas_digitos(v, "CEST", 7)

    @field_validator("cfop_padrao", mode="before")
    @classmethod
    def validar_cfop(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        return _apenas_digitos(v, "CFOP", 4)

    @field_validator("gtin_tributavel", mode="before")
    @classmethod
    def validar_gtin(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        limpo = re.sub(r"\D", "", v)
        # EAN-8, EAN-13 ou EAN-14
        if len(limpo) not in (8, 13, 14):
            raise ValueError(
                f"GTIN tributável deve ter 8, 13 ou 14 dígitos numéricos (recebido: {v!r})"
            )
        return limpo

    @field_validator("cst_icms", mode="before")
    @classmethod
    def validar_cst_icms(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        limpo = re.sub(r"\D", "", v)
        if len(limpo) not in (2, 3):
            raise ValueError(f"CST ICMS deve ter 2 ou 3 dígitos numéricos (recebido: {v!r})")
        return limpo.zfill(3)

    @field_validator("csosn", mode="before")
    @classmethod
    def validar_csosn(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        limpo = re.sub(r"\D", "", v)
        if len(limpo) not in (3,):
            raise ValueError(f"CSOSN deve ter 3 dígitos numéricos (recebido: {v!r})")
        return limpo

    @field_validator("cst_pis", mode="before")
    @classmethod
    def validar_cst_pis(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        return _apenas_digitos(v, "CST PIS", 2)

    @field_validator("cst_cofins", mode="before")
    @classmethod
    def validar_cst_cofins(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        return _apenas_digitos(v, "CST COFINS", 2)

    @field_validator("codigo_beneficio_fiscal", mode="before")
    @classmethod
    def validar_codigo_beneficio_fiscal(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        return v.strip()

    @field_validator("c_class_trib", mode="before")
    @classmethod
    def validar_c_class_trib(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        return v.strip()

    @field_validator("cst_ibs_cbs", mode="before")
    @classmethod
    def validar_cst_ibs_cbs(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        limpo = re.sub(r"\D", "", v)
        if len(limpo) not in (2, 3):
            raise ValueError(f"CST IBS/CBS deve ter 2 ou 3 dígitos numéricos (recebido: {v!r})")
        return limpo.zfill(3)

    @field_validator("c_benef", mode="before")
    @classmethod
    def validar_c_benef(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        return v.strip()


class ProdutoFiscalCreate(ProdutoFiscalBase):
    """Payload para criar dados fiscais de um produto."""
    pass


class ProdutoFiscalUpdate(ProdutoFiscalBase):
    """Payload para atualizar dados fiscais de um produto (todos os campos são opcionais)."""
    pass


class ProdutoFiscalRead(ProdutoFiscalBase):
    """Resposta da API com dados fiscais de um produto."""

    id: int
    produto_id: int
    data_atualizacao: datetime

    model_config = ConfigDict(from_attributes=True)
