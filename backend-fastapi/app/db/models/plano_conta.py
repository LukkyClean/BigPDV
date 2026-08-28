# ---------------------------------------------------------------------------
# ARQUIVO: db/models/plano_conta.py
# DESCRIÇÃO: Modelo SQLAlchemy para a tabela 'planos_conta'.
#            As categorias que classificam cada despesa e cada receita.
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enum import PlanoContaTipo
from app.db.base import Base

if TYPE_CHECKING:
    from .conta_pagar import ContaPagar


class PlanoConta(Base):
    """Uma categoria do plano de contas: 'Aluguel', 'Mercadoria', 'Salários'.

    Deliberadamente PLANO, sem hierarquia de níveis. Plano de contas contábil de
    verdade é uma árvore com códigos (3.1.02.001), e nenhum dono de loja de
    bairro preenche isso -- ele quer marcar "isto foi aluguel" e ver quanto
    gastou de aluguel no mês. Hierarquia entra no dia em que um cliente pedir, e
    entra como coluna `pai_id` nesta mesma tabela, sem migrar dado nenhum.

    O `tipo` separa o que soma do que subtrai no resultado. Não é enfeite: sem
    ele, somar tudo daria um número que não significa nada.
    """

    __tablename__ = "planos_conta"
    __table_args__ = (
        # Duas categorias "Aluguel" na mesma loja só geram dúvida na hora de
        # classificar, e dividem o total em dois lugares no relatório.
        UniqueConstraint("empresa_id", "nome", name="uq_plano_conta_empresa_nome"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    empresa_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Empresa dona da categoria",
    )

    nome: Mapped[str] = mapped_column(String(100), nullable=False, doc="Ex.: 'Aluguel', 'Energia'")

    tipo: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=PlanoContaTipo.DESPESA.value,
        index=True,
        doc="DESPESA ou RECEITA (ver PlanoContaTipo)",
    )

    # Categoria semeada pelo sistema no primeiro acesso. Serve para uma coisa
    # só: não semear de novo depois que o lojista apagar as que não usa. Sem
    # esta marca, "a lista está vazia" seria indistinguível de "instalação nova"
    # e as categorias ressuscitariam sozinhas.
    padrao: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0",
        doc="Veio do conjunto semeado pelo sistema",
    )

    # Desativa em vez de apagar: a categoria pode estar amarrada a contas
    # antigas, e apagá-la deixaria o histórico sem classificação.
    ativo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1",
        doc="Categoria disponível para novos lançamentos",
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
        doc="Instante de criação, em UTC (ver app/core/tempo.py)",
    )

    contas_pagar: Mapped[List["ContaPagar"]] = relationship(
        "ContaPagar", back_populates="plano_conta"
    )

    def __repr__(self) -> str:
        return f"<PlanoConta(id={self.id}, {self.tipo} '{self.nome}')>"
