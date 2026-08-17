# ---------------------------------------------------------------------------
# ARQUIVO: app/db/models/produto_fiscal.py
# DESCRIÇÃO: Tabela satélite com dados fiscais de um produto.
#            Relação 1:1 opcional com 'produtos' — não existe para quem
#            não tem o módulo fiscal ativo. NENHUM campo fiscal é NOT NULL.
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.produto import Produto


class ProdutoFiscal(Base):
    """
    Dados fiscais de um produto para emissão de NFe/NFCe via Focus NFe.

    Regra de armazenamento (doc. de design §5.3):
    - Nenhum campo fiscal possui NOT NULL — a obrigatoriedade é verificada
      na camada de serviço apenas no momento da tentativa de emissão.
    - O registro só existe para empresas com fiscal_settings ativo.
    """
    __tablename__ = "produto_fiscal"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        doc="ID único do registro fiscal do produto"
    )
    produto_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("produtos.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        doc="FK para o produto (1:1 opcional — o produto existe sem esse registro)"
    )

    # --- Campos fiscais (todos nullable no banco) ---

    ncm: Mapped[Optional[str]] = mapped_column(
        String(8),
        nullable=True,
        doc="NCM — Nomenclatura Comum do Mercosul (8 dígitos numéricos). Obrigatório na emissão."
    )
    cest: Mapped[Optional[str]] = mapped_column(
        String(7),
        nullable=True,
        doc="CEST — Código Especificador da Substituição Tributária (7 dígitos). Condicional."
    )
    cfop_padrao: Mapped[Optional[str]] = mapped_column(
        String(4),
        nullable=True,
        doc="CFOP padrão do produto (4 dígitos). Obrigatório na emissão."
    )
    origem_mercadoria: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Código de origem da mercadoria (0=Nacional, 1-8=importado). Obrigatório na emissão."
    )
    unidade_tributavel: Mapped[Optional[str]] = mapped_column(
        String(6),
        nullable=True,
        doc="Unidade tributável (pode diferir da unidade comercial). Obrigatório na emissão."
    )
    gtin_tributavel: Mapped[Optional[str]] = mapped_column(
        String(14),
        nullable=True,
        doc="GTIN tributável — EAN-8 (8 dígitos) ou EAN-13/14 (13-14 dígitos). Condicional."
    )
    cst_icms: Mapped[Optional[str]] = mapped_column(
        String(3),
        nullable=True,
        doc="CST de ICMS (3 dígitos) — para empresas no regime normal (Lucro Presumido/Real)."
    )
    csosn: Mapped[Optional[str]] = mapped_column(
        String(3),
        nullable=True,
        doc="CSOSN (3 dígitos) — para empresas no Simples Nacional."
    )

    # --- Reforma Tributária (IBS/CBS) ---

    c_class_trib: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        doc="Código de Classificação Tributária IBS/CBS"
    )
    cst_ibs_cbs: Mapped[Optional[str]] = mapped_column(
        String(3), nullable=True,
        doc="CST IBS/CBS — situação tributária do item na reforma"
    )
    aliquota_ibs: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        doc="Alíquota IBS em centésimos de ponto percentual (500 = 5,00%)"
    )
    aliquota_cbs: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        doc="Alíquota CBS em centésimos de ponto percentual (500 = 5,00%)"
    )
    c_benef: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True,
        doc="Código de Benefício Fiscal IBS/CBS"
    )

    # --- Metadados ---

    data_atualizacao: Mapped[datetime] = mapped_column(
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
        doc="Data da última atualização dos dados fiscais"
    )

    # --- Relacionamento ---

    produto: Mapped["Produto"] = relationship(
        "Produto",
        back_populates="fiscal",
        doc="Produto ao qual estes dados fiscais pertencem"
    )

    def __repr__(self) -> str:
        return f"<ProdutoFiscal(id={self.id}, produto_id={self.produto_id}, ncm={self.ncm!r})>"
