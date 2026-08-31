# ---------------------------------------------------------------------------
# ARQUIVO: app/schemas/emissao_fiscal.py
# DESCRIÇÃO: Schemas Pydantic para emissão de NF-e (request/response).
# ---------------------------------------------------------------------------

from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class EmissaoNFeRequest(BaseModel):
    """Request para emitir NF-e a partir de uma venda ou OS."""

    venda_id: Optional[int] = None
    numero_os: Optional[str] = None

    @model_validator(mode="after")
    def validar_origem(self):
        if not self.venda_id and not self.numero_os:
            raise ValueError("Informe venda_id ou numero_os.")
        if self.venda_id and self.numero_os:
            raise ValueError("Informe apenas venda_id OU numero_os, não ambos.")
        return self


class CancelamentoRequest(BaseModel):
    """Request para cancelar documento fiscal autorizado."""

    justificativa: str

    @field_validator("justificativa")
    @classmethod
    def validar_justificativa(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 15:
            raise ValueError("Justificativa deve ter no mínimo 15 caracteres (exigência SEFAZ).")
        if len(v) > 255:
            raise ValueError("Justificativa deve ter no máximo 255 caracteres.")
        return v


class EmissaoResponse(BaseModel):
    """Response padrão de operações de emissão/consulta/cancelamento."""

    documento_id: int
    ref_api: Optional[str] = None
    status: str
    mensagem: str
    ambiente: int


class FiscalConfiguracao(BaseModel):
    """Configuração atual do ambiente fiscal."""

    ambiente: int
    ambiente_label: str
    mock_ativo: bool
    certificado_configurado: bool
    certificado_valido: bool


class EmissaoPreviewItem(BaseModel):
    numero_item: int
    produto_id: Optional[int] = None
    nome: str
    quantidade: float
    valor_unitario: float
    valor_total: float
    cfop: str
    ncm: str
    cst_csosn: str = ""


class EmissaoPreviewTotais(BaseModel):
    valor_produtos: float
    descontos: float
    frete: float
    valor_nota: float
    total_tributos: int


class EmissaoPreviewDestinatario(BaseModel):
    nome: str
    documento: str


class EmissaoPreviewPagamento(BaseModel):
    nome: str
    codigo_sefaz: str
    valor: int


class EmissaoPreviewResponse(BaseModel):
    """Dados retornados para a tela de pré-visualização no frontend."""
    destinatario: EmissaoPreviewDestinatario
    totais: EmissaoPreviewTotais
    itens: list[EmissaoPreviewItem]
    formas_pagamento: list[EmissaoPreviewPagamento] = []


# --- Batch ---

class EmissaoNFeBatchRequest(BaseModel):
    """Request para emissão em lote de NF-e."""
    venda_ids: list[int] = Field(..., min_length=1, max_length=20)

    @field_validator("venda_ids")
    @classmethod
    def deduplicar(cls, v: list[int]) -> list[int]:
        return list(dict.fromkeys(v))


class EmissaoBatchItemResult(BaseModel):
    venda_id: int
    documento_id: Optional[int] = None
    status: str
    mensagem: str


class EmissaoBatchResponse(BaseModel):
    resultados: list[EmissaoBatchItemResult]
    total: int
    sucesso: int
    falha: int
