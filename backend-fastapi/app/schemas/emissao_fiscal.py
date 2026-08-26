# ---------------------------------------------------------------------------
# ARQUIVO: app/schemas/emissao_fiscal.py
# DESCRIÇÃO: Schemas Pydantic para emissão de NF-e (request/response).
# ---------------------------------------------------------------------------

from typing import Optional

from pydantic import BaseModel, field_validator, model_validator


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
