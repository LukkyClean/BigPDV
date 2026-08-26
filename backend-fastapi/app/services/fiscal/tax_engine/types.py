# ---------------------------------------------------------------------------
# ARQUIVO: app/services/fiscal/tax_engine/types.py
# DESCRIÇÃO: DTOs puros (Pydantic) do motor de cálculo tributário.
#            SEM imports de modelos ORM ou frameworks web.
# ---------------------------------------------------------------------------

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


# ========================
# ENTRADA
# ========================

class ItemEntrada(BaseModel):
    """Dados de um item da venda para cálculo tributário."""

    numero_item: int
    produto_id: Optional[int] = None
    descricao: str

    quantidade: Decimal
    valor_unitario: Decimal       # reais
    valor_bruto: Decimal          # reais (quantidade × valor_unitario)
    desconto_item: Decimal        # reais (desconto do item)

    # Dados fiscais do produto
    ncm: Optional[str] = None
    cfop: Optional[str] = None
    origem_mercadoria: int = 0
    cst_icms: Optional[str] = None    # regime normal
    csosn: Optional[str] = None       # simples nacional

    # Alíquotas já resolvidas (produto override > UF default)
    aliquota_icms: Decimal = Decimal("0")
    reducao_base_icms: Decimal = Decimal("0")
    codigo_beneficio_fiscal: Optional[str] = None

    aliquota_pis: Decimal = Decimal("0")
    aliquota_cofins: Decimal = Decimal("0")
    cst_pis: str = "01"
    cst_cofins: str = "01"


class DadosNota(BaseModel):
    """Dados globais da nota para rateio e configuração."""

    uf_emitente: str
    simples_nacional: bool

    frete: Decimal = Decimal("0")
    seguro: Decimal = Decimal("0")
    outras_despesas: Decimal = Decimal("0")
    desconto_nota: Decimal = Decimal("0")

    excluir_icms_base_pis_cofins: bool = False  # STF Tema 69


# ========================
# SAÍDA
# ========================

class ImpostosItem(BaseModel):
    """Resultado do cálculo tributário para um item."""

    numero_item: int

    # Rateio
    valor_frete: Decimal
    valor_seguro: Decimal
    valor_outras_despesas: Decimal
    valor_desconto: Decimal         # item + rateio da nota

    # ICMS
    icms_origem: int
    icms_situacao_tributaria: str
    icms_modalidade_base_calculo: int = 0  # 0 = Margem Valor Agregado (%)
    icms_base_calculo: Decimal
    icms_aliquota: Decimal
    icms_valor: Decimal
    icms_reducao_base: Optional[Decimal] = None
    icms_codigo_beneficio_fiscal: Optional[str] = None

    # CSOSN 101 específico
    icms_aliquota_credito_simples: Optional[Decimal] = None
    icms_valor_credito_simples: Optional[Decimal] = None

    # PIS
    pis_situacao_tributaria: str
    pis_base_calculo: Decimal
    pis_aliquota: Decimal
    pis_valor: Decimal

    # COFINS
    cofins_situacao_tributaria: str
    cofins_base_calculo: Decimal
    cofins_aliquota: Decimal
    cofins_valor: Decimal

    # IPI (não calculado — comércio/serviços)
    ipi_situacao_tributaria: str
    ipi_codigo_enquadramento: str


class TotaisNota(BaseModel):
    """Totais consolidados do cabeçalho da NF-e."""

    base_calculo_icms: Decimal
    valor_icms: Decimal
    valor_pis: Decimal
    valor_cofins: Decimal

    valor_frete: Decimal
    valor_seguro: Decimal
    valor_desconto: Decimal
    valor_outras_despesas: Decimal

    valor_total_produtos: Decimal
    valor_total_nota: Decimal


class ResultadoCalculo(BaseModel):
    """Resultado completo do cálculo tributário."""

    itens: list[ImpostosItem]
    totais: TotaisNota
