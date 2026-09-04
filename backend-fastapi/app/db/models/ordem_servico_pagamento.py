# ---------------------------------------------------------------------------
# ARQUIVO: db/models/ordem_servico_pagamento.py
# DESCRICAO: Modelo SQLAlchemy para a tabela 'ordem_servico_pagamentos'.
# ---------------------------------------------------------------------------

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Date, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, TYPE_CHECKING
from datetime import date, datetime

from app.db.base import Base

if TYPE_CHECKING:
    from .forma_pagamento import FormaPagamento
    from .ordem_servico import OrdemServico


class OrdemServicoPagamento(Base):
    """Modelo ORM que representa um pagamento de uma Ordem de Servico."""

    __tablename__ = "ordem_servico_pagamentos"
    __table_args__ = (
        CheckConstraint("valor >= 0", name="ck_os_pagamento_valor_nao_negativo"),
        CheckConstraint("parcelas >= 1", name="ck_os_pagamento_parcelas_min_1"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, doc="ID unico do pagamento (PK)")

    ordem_servico_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ordens_servico.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID da OS (FK)"
    )

    forma_pagamento_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("formas_pagamento.id"),
        nullable=False,
        doc="ID da forma de pagamento"
    )
    valor: Mapped[int] = mapped_column(Integer, nullable=False, doc="Valor pago pelo cliente neste metodo (centavos)")
    juros_valor: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default="0",
        doc="Juros calculados neste pagamento (centavos). Ver juros_responsavel para saber quem paga."
    )
    juros_responsavel: Mapped[str] = mapped_column(
        String(10), default="CLIENTE", nullable=False, server_default="CLIENTE",
        doc="CLIENTE = juros repassado (embutido em valor); LOJA = juros absorvido pela loja (fora de valor)"
    )
    parcelas: Mapped[int] = mapped_column(Integer, default=1, nullable=False, doc="Numero de parcelas")
    bandeira_cartao: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, doc="Bandeira do cartao (VISA, MASTERCARD, etc)")
    vencimento: Mapped[Optional[date]] = mapped_column(Date, nullable=True, doc="Data de vencimento do pagamento (boletos ou combinado)")
    detalhes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, doc="Detalhes adicionais do pagamento")

    # Quando o pagamento foi REGISTRADO. Nao existia: a linha so tinha
    # `vencimento`, que e uma promessa, e nada dizia em que momento o dinheiro
    # entrou. Sem isso nao ha como saber em qual turno de caixa a OS foi paga --
    # e OS paga em dias diferentes (sinal na entrada, quitacao na retirada) e a
    # regra, nao a excecao.
    # Nullable por causa das linhas antigas: o instante delas nao e recuperavel,
    # e inventar um seria pior que admitir a lacuna.
    data_pagamento: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        default=func.now(),
        doc="Momento exato do registro do pagamento (UTC)",
    )

    # Ver a nota equivalente em venda_pagamento.py: conveniencia de consulta; o
    # fechamento le o livro do dinheiro, nao esta coluna.
    sessao_caixa_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("sessao_caixa.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Sessao de caixa em que o pagamento foi registrado",
    )

    # --- Relacionamentos ---
    ordem_servico: Mapped["OrdemServico"] = relationship(back_populates="pagamentos")
    forma_pagamento: Mapped["FormaPagamento"] = relationship("FormaPagamento", back_populates="pagamentos")
