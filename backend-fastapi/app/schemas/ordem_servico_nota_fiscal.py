# ---------------------------------------------------------------------------
# ARQUIVO: app/schemas/ordem_servico_nota_fiscal.py
# DESCRIÇÃO: Schemas Pydantic para nota fiscal por OS.
#
# A OS pode gerar dois documentos:
# - NFe/NFCe para peças (itens de produto)
# - NFSe para mão de obra (itens de serviço)
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrdemServicoNotaFiscalUpdate(BaseModel):
    """Campos editáveis pelo usuário antes da emissão."""

    natureza_operacao: Optional[str] = Field(None, max_length=60)
    # 1=Normal, 2=Complementar, 3=Ajuste, 4=Devolução/Retorno
    finalidade_emissao: Optional[int] = Field(None, ge=1, le=4)
    consumidor_final: Optional[bool] = None
    # 1=Presencial, 2=Internet, 3=Teleatendimento, 4=Entrega domiciliar, 9=Outros
    indicador_presenca: Optional[int] = None
    emitir_nfe: Optional[bool] = None
    emitir_nfse: Optional[bool] = None

    @field_validator("indicador_presenca", mode="before")
    @classmethod
    def validar_indicador_presenca(cls, v):
        if v is None:
            return v
        if v not in (1, 2, 3, 4, 9):
            raise ValueError("indicador_presenca deve ser 1, 2, 3, 4 ou 9")
        return v


class OrdemServicoNotaFiscalRead(OrdemServicoNotaFiscalUpdate):
    """Inclui os campos de resultado da emissão (somente leitura via API)."""

    id: int
    os_id: int

    # Resultados NFe (peças — Focus NFe, fase futura)
    status_nfe: Optional[str] = None
    chave_acesso_nfe: Optional[str] = None
    numero_nfe: Optional[int] = None
    serie_nfe: Optional[int] = None
    protocolo_nfe: Optional[str] = None
    data_autorizacao_nfe: Optional[datetime] = None
    url_danfe: Optional[str] = None
    mensagem_nfe: Optional[str] = None
    qrcode_nfe: Optional[str] = None

    # Resultados NFSe (mão de obra — Focus NFe, fase futura)
    status_nfse: Optional[str] = None
    numero_nfse: Optional[str] = None
    codigo_verificacao_nfse: Optional[str] = None
    data_emissao_nfse: Optional[datetime] = None
    url_nfse: Optional[str] = None
    mensagem_nfse: Optional[str] = None

    data_atualizacao: datetime

    model_config = ConfigDict(from_attributes=True)
