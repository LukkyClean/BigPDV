# ---------------------------------------------------------------------------
# ARQUIVO: db/models/venda_pagamento.py
# DESCRICAO: Modelo SQLAlchemy para a tabela 'pagamentos_venda'.
#            Armazena multiplas formas de pagamento para uma unica venda.
# ---------------------------------------------------------------------------

from datetime import datetime, date
from sqlalchemy import Integer, Boolean, DateTime, Date, String, JSON, ForeignKey, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, TYPE_CHECKING

from app.db.base import Base

if TYPE_CHECKING:
    from .venda import Venda
    from .forma_pagamento import FormaPagamento


class PagamentoVenda(Base):
    """Modelo ORM que representa um pagamento de venda na tabela 'pagamentos_venda'."""

    __tablename__ = "pagamentos_venda"
    __table_args__ = (
        CheckConstraint("valor > 0", name="ck_pagamento_venda_valor_positivo"),
        # A vista: parcelado=0 e qtd_parcelas NULO. Parcelado: parcelado=1 e qtd_parcelas >= 1.
        # (A regra antiga exigia parcelado sempre FALSO, o que rejeitava qualquer parcelamento.)
        CheckConstraint(
            "(NOT parcelado AND qtd_parcelas IS NULL) OR (parcelado AND qtd_parcelas >= 1)",
            name="ck_pagamento_venda_parcelas_min_1",
        ),
    )

    # --- Identificacao ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, doc="ID unico da transacao (PK)")

    # --- Vinculos ---
    venda_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("vendas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Venda correspondente (FK)"
    )
    forma_pagamento_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("formas_pagamento.id"),
        nullable=False,
        doc="Forma de pagamento utilizada (FK)"
    )

    # --- Dados do Pagamento ---
    valor: Mapped[int] = mapped_column(Integer, nullable=False, doc="Fracao financeira paga pelo cliente neste metodo (centavos)")
    juros_valor: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default="0",
        doc="Juros calculados neste pagamento (centavos). Ver juros_responsavel para saber quem paga."
    )
    juros_responsavel: Mapped[str] = mapped_column(
        String(10), default="CLIENTE", nullable=False, server_default="CLIENTE",
        doc="CLIENTE = juros repassado (embutido em valor); LOJA = juros absorvido pela loja (fora de valor)"
    )
    parcelado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True, doc="Flag indicando compra a prazo")
    qtd_parcelas: Mapped[int] = mapped_column(Integer, nullable=True, doc="Quantidade de parcelas (1 = a vista)")
    bandeira_cartao: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, doc="Bandeira do cartao (VISA, MASTERCARD, etc)")
    vencimento: Mapped[Optional[date]] = mapped_column(Date, nullable=True, doc="Data de vencimento do pagamento (ex: boletos)")
    detalhes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, doc="Detalhes adicionais do pagamento (ex: banco/NSU de transferencia)")
    data_pagamento: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), doc="Momento exato do registro do pagamento")

    # Turno de caixa em que esta cobranca foi registrada. Conveniencia de
    # consulta -- o fechamento soma o LIVRO (movimentacoes_financeiras), nao
    # esta coluna, porque uma venda reaberta e refinalizada em outro dia mexeria
    # no caixa de ontem se a fonte fosse o documento.
    # NULL em toda loja que nao usa controle de caixa, como sempre foi.
    sessao_caixa_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("sessao_caixa.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Sessao de caixa em que o pagamento foi registrado",
    )

    # --- Relacionamentos ---
    venda: Mapped["Venda"] = relationship(back_populates="pagamentos")
    forma_pagamento: Mapped["FormaPagamento"] = relationship("FormaPagamento", back_populates="pagamentos_venda")
