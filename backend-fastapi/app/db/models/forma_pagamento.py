from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, List, Optional

from app.db.base import Base

if TYPE_CHECKING:
    from .ordem_servico_pagamento import OrdemServicoPagamento
    from .venda_pagamento import PagamentoVenda


class FormaPagamento(Base):
    """Catalogo de formas de pagamento aceitas para OS."""

    __tablename__ = "formas_pagamento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, doc="ID unico da forma de pagamento (PK)")
    nome: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, doc="Nome da forma de pagamento")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, doc="Status ativo/inativo")
    codigo_sefaz: Mapped[Optional[str]] = mapped_column(
        String(2), nullable=True,
        doc="Código SEFAZ da forma de pagamento (01-99). Obrigatório para emissão fiscal."
    )
    tipo_integracao: Mapped[Optional[str]] = mapped_column(
        String(15), nullable=True,
        doc=(
            "TEF, POS ou NAO_SE_APLICA — como a maquininha conversa com o PDV. "
            "Só faz sentido em cartão; ver TipoIntegracaoPagamento."
        )
    )

    # --- Quando e onde o dinheiro DESTA forma cai ---
    #
    # Dinheiro de cartao nao esta na conta no dia da venda: a maquininha
    # deposita depois. Ate 02/09/2026 o sistema tratava todo recebimento como
    # dinheiro que ja entrou, e o saldo mostrava na conta um valor que so
    # chegaria amanha.
    #
    # ZERO E O PADRAO, e zero e exatamente o comportamento antigo: entra na
    # hora. Nada muda em loja nenhuma enquanto o dono nao declarar um prazo.
    #
    # Com prazo declarado, o recebimento vira CONTA A RECEBER com vencimento em
    # D+n -- reusando o caminho que ja existia para o fiado. O Fluxo de Caixa o
    # mostra em "Vai entrar" no dia certo, e a Conciliacao (que ja agrupa por
    # dia, porque "a operadora nao deposita venda a venda") acerta a taxa.
    dias_para_receber: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        doc="Dias ate o dinheiro cair na conta. 0 = entra na hora",
    )

    # Cartao cai no banco, dinheiro fica na gaveta. Sem esta coluna TODO
    # recebimento caia na conta principal, porque nao havia onde dizer outra
    # coisa. NULL = a principal da loja, que continua sendo o padrao.
    conta_bancaria_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("contas_bancarias.id", ondelete="SET NULL"),
        nullable=True,
        doc="Conta em que o dinheiro desta forma cai; NULL = a principal",
    )

    pagamentos: Mapped[List["OrdemServicoPagamento"]] = relationship(
        "OrdemServicoPagamento",
        back_populates="forma_pagamento",
        doc="Pagamentos de OS associados a esta forma de pagamento"
    )

    pagamentos_venda: Mapped[List["PagamentoVenda"]] = relationship(
        "PagamentoVenda",
        back_populates="forma_pagamento",
        doc="Pagamentos de venda associados a esta forma de pagamento"
    )
