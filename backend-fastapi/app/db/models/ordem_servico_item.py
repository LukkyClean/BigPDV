# ---------------------------------------------------------------------------
# ARQUIVO: db/models/ordem_servico_item.py
# DESCRICAO: Modelo SQLAlchemy para a tabela 'ordem_servico_itens'.
# ---------------------------------------------------------------------------

from sqlalchemy import Float, Integer, String, Boolean, ForeignKey, Enum as SqlAlchemyEnum, CheckConstraint
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
    # Fracionada para unidades de peso: a serigrafia vende sacola por quilo, e
    # quilo quebrado (2,5 kg) é escolha do cliente. Ver a nota em
    # db/models/estoque.py sobre por que isso não exigiu migration.
    quantidade: Mapped[float] = mapped_column(Float, nullable=False, doc="Quantidade")
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

    # --- Custo declarado a mao (gasto sem produto de estoque) ---
    # Na OS o comum e nao cadastrar peca: lanca-se so o servico ("Troca de
    # conector — R$ 150"). Mas o conector custou R$ 40, e sem registrar isso em
    # algum lugar o relatorio de lucro do mes fica errado para mais.
    #
    # Este campo e esse lugar. E INTERNO: nao sai em NENHUMA via impressa, por
    # decisao explicita da loja — o cliente nunca deve ver quanto foi pago pela
    # peca. Nao confundir com `valor_unitario`, que e o que o cliente paga.
    #
    # So vale para item SEM `produto_id`. Quando a peca vem do catalogo, o custo
    # e o do livro de estoque (congelado na baixa) e contar os dois dobraria o
    # CMV — ver crud/relatorio.get_custo_manual_os.
    custo_unitario: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Custo unitario que a loja teve com este item, em centavos. Interno: nunca impresso."
    )

    # --- Visibilidade na via do cliente ---
    # False = peça EMBUTIDA no serviço. Ela existe para a loja em tudo que
    # importa — dá baixa no estoque, congela custo e entra no CMV do relatório —
    # mas não é listada nas vias impressas. O caso real: cobrar R$ 150 pelo
    # serviço sem expor que a peça usada custou R$ 40.
    #
    # Invariante: item embutido vale ZERO. As vias imprimem as linhas visíveis e
    # o total da OS; uma linha escondida com valor faria as duas coisas
    # divergirem, e o cliente receberia um documento que não fecha. O dinheiro
    # fica na linha do serviço. Validado em schemas/ordem_servico.py e no
    # serviço, na atualização parcial.
    visivel_cliente: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="1",
        nullable=False,
        doc="Se False, a peca esta embutida no servico e nao sai nas vias do cliente"
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
