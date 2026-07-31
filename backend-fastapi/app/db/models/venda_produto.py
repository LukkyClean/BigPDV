# ---------------------------------------------------------------------------
# ARQUIVO: db/models/venda_produto.py
# DESCRICAO: Modelo SQLAlchemy para a tabela 'produtos_venda'.
#            Tabela pivo do carrinho. Congela precos e aceita itens avulsos.
# ---------------------------------------------------------------------------

from sqlalchemy import Integer, String, ForeignKey, CheckConstraint, Enum as SqlAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, TYPE_CHECKING
from app.core.enum import TipoProdutoVenda

from app.db.base import Base

if TYPE_CHECKING:
    from .venda import Venda
    from .produto import Produto


class ProdutoVenda(Base):
    """Modelo ORM que representa um item do carrinho na tabela 'produtos_venda'."""

    __tablename__ = "produtos_venda"
    __table_args__ = (
        CheckConstraint("quantidade > 0", name="ck_produto_venda_qtd_positiva"),
        CheckConstraint("valor_unitario >= 0", name="ck_produto_venda_valor_unitario_nao_negativo"),
        CheckConstraint("desconto >= 0", name="ck_produto_venda_desconto_nao_negativo"),
        CheckConstraint(
            "(produto_id IS NOT NULL) OR (descricao_avulsa IS NOT NULL)",
            name="ck_produto_venda_referencia_obrigatoria"
        ),
        CheckConstraint(
            "((tipo_produto = 'CADASTRADO') AND (produto_id IS NOT NULL)) OR "
            "((tipo_produto = 'AVULSO') AND (descricao_avulsa IS NOT NULL) AND (produto_id IS NULL))",
            name="ck_produto_venda_tipo_referencia_consistente"
        ),
    )

    # --- Identificacao ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, doc="ID da linha do carrinho (PK)")

    # --- Vinculos ---
    venda_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("vendas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Referencia a venda matriz (FK)"
    )
    produto_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("produtos.id", ondelete="SET NULL"),
        nullable=True,
        doc="Item de estoque. Nulo se for item avulso (FK)"
    )

    # --- Dados do Item ---
    tipo_produto: Mapped[TipoProdutoVenda] = mapped_column(
        SqlAlchemyEnum(TipoProdutoVenda),
        nullable=False,
        doc="Tipo do produto vendido"
    )
    @property
    def nome(self):
        if self.tipo_produto == TipoProdutoVenda.CADASTRADO and self.produto:
            return self.produto.nome
        return self.descricao_avulsa
    @property
    def sku(self):
        if self.tipo_produto == TipoProdutoVenda.CADASTRADO and self.produto:
            return self.produto.codigo_produto
        return None
    descricao_avulsa: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Descricao obrigatoria se produto_id for nulo"
    )
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False, doc="Quantidade do item vendido")
    valor_unitario: Mapped[int] = mapped_column(Integer, nullable=False, doc="Preco unitario congelado no ato da inclusao (centavos)")
    # Custo declarado a mao, so faz sentido em item AVULSO. Produto CADASTRADO
    # da baixa no estoque e tem o custo congelado no livro (movimentacoes_estoque);
    # o avulso nao passa por la, entao sem este campo ele entrava no relatorio
    # como receita sem custo nenhum e inflava o lucro.
    #
    # E INTERNO: nao sai em nenhuma via impressa, igual ao equivalente na OS.
    custo_unitario: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Custo unitario que a loja teve com este item avulso (centavos). Interno: nunca impresso."
    )
    desconto: Mapped[int] = mapped_column(Integer, default=0, nullable=False, doc="Desconto especifico deste item (centavos)")
    subtotal: Mapped[int] = mapped_column(Integer, nullable=False, doc="Subtotal calculado (quantidade * valor_unitario)")
    @property
    def total(self):
        return self.subtotal - self.desconto
    @property
    def imagem_url(self):
        if self.tipo_produto == TipoProdutoVenda.CADASTRADO and self.produto:
            return self.produto.imagem_url
        return None

    @property
    def unidade_medida(self):
        if self.tipo_produto == TipoProdutoVenda.CADASTRADO and self.produto:
            return self.produto.unidade_medida
        return None

    @property
    def estoque_disponivel(self):
        if self.tipo_produto == TipoProdutoVenda.CADASTRADO and self.produto and self.produto.estoque:
            return self.produto.estoque.quantidade
        return None

    # --- Relacionamentos ---
    venda: Mapped["Venda"] = relationship(back_populates="itens")
    produto: Mapped[Optional["Produto"]] = relationship(doc="Produto do catalogo associado")
