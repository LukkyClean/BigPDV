# ---------------------------------------------------------------------------
# ARQUIVO: app/schemas/venda_nota_fiscal.py
# DESCRIÇÃO: Schemas Pydantic para leitura e atualização de nota fiscal por venda.
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VendaNotaFiscalUpdate(BaseModel):
    """Campos editáveis pelo usuário antes da emissão."""

    natureza_operacao: Optional[str] = Field(None, max_length=60)
    # 1=Normal, 2=Complementar, 3=Ajuste, 4=Devolução/Retorno
    finalidade_emissao: Optional[int] = Field(None, ge=1, le=4)
    consumidor_final: Optional[bool] = None
    # 1=Presencial, 2=Internet, 3=Teleatendimento, 4=Entrega domiciliar, 9=Outros
    indicador_presenca: Optional[int] = None

    @field_validator("indicador_presenca", mode="before")
    @classmethod
    def validar_indicador_presenca(cls, v):
        if v is None:
            return v
        if v not in (1, 2, 3, 4, 9):
            raise ValueError("indicador_presenca deve ser 1, 2, 3, 4 ou 9")
        return v


class VendaNotaFiscalRead(VendaNotaFiscalUpdate):
    """Inclui os campos de resultado da emissão (somente leitura via API)."""

    id: int
    venda_id: int
    # Resultados Focus NFe — preenchidos ao emitir (fase futura)
    status_nota: Optional[str] = None
    chave_acesso: Optional[str] = None
    numero_nota: Optional[int] = None
    serie: Optional[int] = None
    protocolo_autorizacao: Optional[str] = None
    data_autorizacao: Optional[datetime] = None
    url_danfe: Optional[str] = None
    mensagem_sefaz: Optional[str] = None
    qrcode: Optional[str] = None
    data_atualizacao: datetime

    model_config = ConfigDict(from_attributes=True)
