# ---------------------------------------------------------------------------
# ARQUIVO: schemas/verificacao_fiscal.py
# DESCRIÇÃO: Schemas para o resultado da verificação de completude fiscal.
#            Usado pelo gate de emissão e pelo futuro painel de pendências.
# ---------------------------------------------------------------------------

from typing import Optional
from pydantic import BaseModel


class PendenciaFiscal(BaseModel):
    """Uma pendência individual que impede a emissão de documento fiscal."""
    categoria: str
    campo: str
    mensagem: str
    referencia_id: Optional[int] = None
    referencia_nome: Optional[str] = None


class ResultadoVerificacaoFiscal(BaseModel):
    """Resultado consolidado da verificação de completude fiscal."""
    completo: bool
    pendencias: list[PendenciaFiscal]
