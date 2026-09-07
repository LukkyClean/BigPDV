from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, TYPE_CHECKING, List

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
