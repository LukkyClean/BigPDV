# ---------------------------------------------------------------------------
# ARQUIVO: db/models/log_produto.py
# DESCRICAO: Modelo SQLAlchemy para a tabela 'logs_produto'.
#            Historico de auditoria imutavel para movimentacoes de estoque.
# ---------------------------------------------------------------------------

from datetime import datetime
from sqlalchemy import Integer, DateTime, Enum as SqlAlchemyEnum, ForeignKey, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, TYPE_CHECKING

from app.db.base import Base
from app.core.enum import TipoTransacaoEstoque

if TYPE_CHECKING:
    from .produto import Produto
    from .venda import Venda
    from .funcionario import Funcionario


class LogProduto(Base):
    """LEGADO — nao recebe mais escritas. Mantido apenas pelos dados historicos.

    Era o log de estoque exclusivo da venda: o CHECK abaixo exige `venda_id` em
    toda saida, o que estruturalmente impedia registrar saida de OS ou ajuste
    manual. O resultado era um historico de estoque partido em dois, e a tela de
    movimentacoes nunca mostrava venda.

    Desde a migration a4b5c6d7e8f9, `movimentacoes_estoque` e o livro-razao unico:
    venda, OS, cadastro e ajuste manual gravam todos la, com a coluna `origem`
    dizendo de onde veio. As linhas antigas daqui foram preservadas de proposito
    (nada foi migrado nem apagado), mas nenhuma linha nova e criada.
    """

    __tablename__ = "logs_produto"
    __table_args__ = (
        CheckConstraint("quantidade != 0", name="ck_log_produto_quantidade_nao_zero"),\
        CheckConstraint("(tipo_transacao == 'ENTRADA') OR (venda_id IS NOT NULL)", name="ck_log_produto_tipo_transacao_valida")
    )

    # --- Identificacao ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, doc="ID do log (PK)")

    # --- Vinculos ---
    produto_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("produtos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Produto movimentado (FK)"
    )
    venda_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("vendas.id", ondelete="SET NULL"),
        nullable=True,
        doc="Venda que causou saida ou estorno (FK)"
    )
    funcionario_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("funcionarios.id"),
        nullable=False,
        doc="Responsavel pela acao (FK)"
    )

    # --- Dados da Movimentacao ---
    tipo_transacao: Mapped[TipoTransacaoEstoque] = mapped_column(
        SqlAlchemyEnum(TipoTransacaoEstoque),
        nullable=False,
        doc="Tipo da transacao de estoque"
    )
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False, doc="Quantidade movimentada (+ ou -)")
    data_registro: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False, doc="Data exata da movimentacao no sistema")

    # --- Relacionamentos ---
    produto: Mapped["Produto"] = relationship(back_populates="logs")
    venda: Mapped[Optional["Venda"]] = relationship(back_populates="logs_produto")
    funcionario: Mapped["Funcionario"] = relationship(doc="Funcionario responsavel pela movimentacao")
