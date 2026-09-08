# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/tax_engine/exceptions.py
# DESCRIÇÃO: Exceções customizadas do motor de cálculo tributário.
#            Cada exceção carrega mensagem explícita, campo e item afetado.
# ---------------------------------------------------------------------------

from typing import Optional


class FiscalTaxError(Exception):
    """Exceção base do motor fiscal."""

    def __init__(
        self,
        mensagem: str,
        campo: Optional[str] = None,
        item: Optional[int] = None,
    ):
        self.mensagem = mensagem
        self.campo = campo
        self.item = item
        super().__init__(mensagem)

    def __repr__(self) -> str:
        partes = [f"mensagem={self.mensagem!r}"]
        if self.campo:
            partes.append(f"campo={self.campo!r}")
        if self.item is not None:
            partes.append(f"item={self.item}")
        return f"{self.__class__.__name__}({', '.join(partes)})"


class CSTNaoSuportadoError(FiscalTaxError):
    """CST ou CSOSN não suportado pelo motor fiscal nesta versão."""
    pass


class AliquotaNaoEncontradaError(FiscalTaxError):
    """Nenhuma alíquota encontrada (nem override no produto, nem default da UF)."""
    pass


class DadosFiscaisAusentesError(FiscalTaxError):
    """Produto não possui dados fiscais (ProdutoFiscal) preenchidos."""
    pass


class RateioError(FiscalTaxError):
    """Erro no rateio proporcional (ex: valor bruto total zero, desconto excede total)."""
    pass


class ConsolidacaoError(FiscalTaxError):
    """Divergência entre soma dos itens e totais do cabeçalho."""
    pass


class OperacaoInterestadualError(FiscalTaxError):
    """Operação interestadual detectada — DIFAL/FCP não implementado nesta versão."""
    pass
