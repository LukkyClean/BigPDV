# ---------------------------------------------------------------------------
# ARQUIVO: db/models/ordem_servico_item.py
# DESCRICAO: Modelo SQLAlchemy para a tabela 'ordem_servico_itens'.
# ---------------------------------------------------------------------------

from sqlalchemy import Integer, String, ForeignKey, Enum as SqlAlchemyEnum, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, TYPE_CHECKING

from app.db.base import Base

from app.core.enum import OrdemServicoItemTipo, UnidadeMedida, OrdemServicoItemAprovacao

if TYPE_CHECKING:
    from .ordem_servico import OrdemServico
    from .produto import Produto
    from .servico import Servico


class OrdemServicoItem(Base):
    """Modelo ORM que representa um item/servico dentro de uma Ordem de Servico."""

    __tablename__ = "ordem_servico_itens"
    __table_args__ = (
        CheckConstraint(
            "NOT (produto_id IS NOT NULL AND servico_id IS NOT NULL)",
            name="ck_os_item_referencia_unica"
        ),
        CheckConstraint("quantidade > 0", name="ck_os_item_quantidade_positiva"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, doc="ID unico do item (PK)")

    ordem_servico_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ordens_servico.id", ondelete="CASCADE"),
        nullable=False,
        doc="ID da OS (FK)"
    )

    produto_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("produtos.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID do produto do catalogo (FK, nullable para itens customizados)"
    )
    servico_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("servicos.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID do servico do catalogo (FK, nullable para itens customizados)"
    )

    tipo: Mapped[OrdemServicoItemTipo] = mapped_column(SqlAlchemyEnum(OrdemServicoItemTipo), nullable=False, doc="Tipo do item")
    nome: Mapped[str] = mapped_column(String(255), nullable=False, doc="Descricao do item/servico")
    unidade_medida: Mapped[UnidadeMedida] = mapped_column(SqlAlchemyEnum(UnidadeMedida), nullable=False, doc="Unidade de medida")
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False, doc="Quantidade")
    valor_unitario: Mapped[int] = mapped_column(Integer, nullable=False, doc="Valor unitario (centavos)")
    valor_total: Mapped[int] = mapped_column(Integer, nullable=False, doc="Valor total (centavos)")

    # --- Aprovacao (fluxo de orcamento) ---
    # Default APROVADO preserva o comportamento atual: itens contam no total.
    status_aprovacao: Mapped[OrdemServicoItemAprovacao] = mapped_column(
        SqlAlchemyEnum(OrdemServicoItemAprovacao),
        default=OrdemServicoItemAprovacao.APROVADO,
        server_default=OrdemServicoItemAprovacao.APROVADO.value,
        nullable=False,
        doc="Status de aprovacao do item (PENDENTE/APROVADO/REPROVADO). REPROVADO nao entra no total."
    )

    # --- Garantia por item (prazo em dias e/ou limite de KM) ---
    garantia_dias: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, doc="Prazo de garantia do item em dias (opcional)"
    )
    garantia_km: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, doc="Limite de garantia do item em KM, ex: oficina (opcional)"
    )

    # --- Relacionamentos ---
    ordem_servico: Mapped["OrdemServico"] = relationship(back_populates="itens")
    produtos: Mapped[Optional["Produto"]] = relationship(doc="Produto do catalogo associado")
    servico: Mapped[Optional["Servico"]] = relationship(doc="Servico do catalogo associado")
