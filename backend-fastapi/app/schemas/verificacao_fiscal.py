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


class DocumentoAtivoResumo(BaseModel):
    """Resumo de um documento fiscal ativo associado a uma venda."""
    documento_id: int
    status: str
    numero_documento: Optional[int] = None
    serie: Optional[int] = None
    chave_acesso: Optional[str] = None


class VerificacaoBatchItem(BaseModel):
    """Resultado de verificação fiscal para uma única venda dentro do batch."""
    venda_id: int
    numero_venda: Optional[int] = None
    completo: bool
    pendencias: list[PendenciaFiscal]
    documento_ativo: Optional[DocumentoAtivoResumo] = None


class ResultadoVerificacaoBatch(BaseModel):
    """Resultado consolidado da verificação batch de múltiplas vendas."""
    resultados: list[VerificacaoBatchItem]
    total: int
    total_aptas: int
    total_com_pendencias: int
    total_com_documento: int
