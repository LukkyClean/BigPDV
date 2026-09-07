# ---------------------------------------------------------------------------
# ARQUIVO: app/db/models/documento_fiscal_item.py
# DESCRIÇÃO: Snapshot dos itens no momento da emissão fiscal.
# ---------------------------------------------------------------------------

from typing import Optional, TYPE_CHECKING

from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.documento_fiscal import DocumentoFiscal


class DocumentoFiscalItem(Base):
    """
    O que foi REALMENTE enviado à SEFAZ, item a item, congelado na emissão.

    POR QUE ESTA TABELA EXISTE
    --------------------------
    Até 05/09/2026 o `DocumentoFiscal` não guardava nada dos itens: a tela de
    detalhes reconstruía NCM e CFOP ao vivo, lendo `item.produto.fiscal` a cada
    abertura. Isso significa que trocar o NCM de um produto mudava o que uma
    nota JÁ AUTORIZADA exibia — o lojista abria a nota, conferia, e via um
    documento diferente do XML que está na SEFAZ.

    O problema é latente hoje e vira grave assim que a derivação automática de
    campos entrar: uma rotina que recalcula CFOP em lote reescreveria a
    exibição de todo o histórico fiscal. Por isso o snapshot é pré-requisito
    da derivação, não um complemento dela.

    Os valores vêm do PAYLOAD, não do cadastro: é o payload que foi transmitido,
    e é com ele que a nota autorizada tem que bater.

    `produto_id` é referência frouxa de propósito — sem FK. O produto pode ser
    excluído do catálogo anos depois e a nota continua tendo que se explicar
    sozinha. Nome, NCM e CFOP ficam aqui como texto por essa mesma razão.
    """

    __tablename__ = "documento_fiscal_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    documento_fiscal_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documento_fiscal.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Documento a que este item pertence",
    )

    numero_item: Mapped[int] = mapped_column(
        Integer, nullable=False, doc="Ordem do item na nota (nItem)"
    )
    produto_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        doc="Referência ao produto — SEM FK: a nota sobrevive à exclusão dele"
    )

    # --- Identificação, como saiu na nota ---
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    codigo_produto: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    codigo_barras: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    unidade: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)

    # --- Classificação fiscal, congelada ---
    ncm: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    cfop: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    cest: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    origem_mercadoria: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    situacao_tributaria: Mapped[Optional[str]] = mapped_column(
        String(3), nullable=True, doc="CST (regime normal) ou CSOSN (Simples)"
    )

    # --- Valores em CENTAVOS, como todo dinheiro no sistema ---
    quantidade_milesimos: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        doc="Quantidade × 1000 — a NF-e admite 4 casas, e int evita float em dado fiscal"
    )
    valor_unitario: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valor_bruto: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valor_desconto: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # --- Tributos destacados ---
    base_icms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valor_icms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    aliquota_icms_centesimos: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, doc="1800 = 18,00%"
    )

    documento: Mapped["DocumentoFiscal"] = relationship(
        "DocumentoFiscal", back_populates="itens",
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentoFiscalItem(doc={self.documento_fiscal_id}, "
            f"item={self.numero_item}, ncm={self.ncm!r}, cfop={self.cfop!r})>"
        )
