# ---------------------------------------------------------------------------
# ARQUIVO: app/schemas/emissao_fiscal.py
# DESCRIÇÃO: Schemas Pydantic para emissão de NF-e (request/response).
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    certificado_status: Optional[str] = None
    certificado_cnpj: Optional[str] = None
    serie_nfe: Optional[int] = 1
    ultimo_numero_nfe: Optional[int] = 0
    serie_nfce: Optional[int] = 1
    ultimo_numero_nfce: Optional[int] = 0
    csc_token: Optional[str] = None
    csc_id: Optional[str] = None


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


# ===========================================================================
# INUTILIZAÇÃO DE NUMERAÇÃO
# ===========================================================================

class GapNumeracao(BaseModel):
    """Faixa de numeração reservada que nunca virou nota autorizada."""

    serie: int
    numero_inicial: int
    numero_final: int
    quantidade: int


class InutilizacaoRequest(BaseModel):
    """Pedido de inutilização de uma faixa de numeração."""

    serie: int = Field(..., ge=0, description="Série da NF-e")
    numero_inicial: int = Field(..., ge=1)
    numero_final: int = Field(..., ge=1)
    justificativa: str = Field(..., description="Motivo declarado à SEFAZ")

    @field_validator("justificativa")
    @classmethod
    def validar_justificativa(cls, v: str) -> str:
        v = (v or "").strip()
        if len(v) < 15:
            raise ValueError("A justificativa deve ter ao menos 15 caracteres.")
        return v


class InutilizacaoRead(BaseModel):
    """Registro de inutilização já solicitado."""

    id: int
    serie: int
    ano: int
    numero_inicial: int
    numero_final: int
    justificativa: str
    status: str
    protocolo: Optional[str] = None
    mensagem_sefaz: Optional[str] = None
    url_xml: Optional[str] = None
    data_solicitacao: Optional[datetime] = None
    data_homologacao: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
