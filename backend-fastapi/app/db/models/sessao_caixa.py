# ---------------------------------------------------------------------------
# ARQUIVO: db/models/sessao_caixa.py
# DESCRICAO: Modelo SQLAlchemy para a tabela 'sessao_caixa'.
#            Garante a integridade do dinheiro fisico e agrupamento de turnos.
# ---------------------------------------------------------------------------

from datetime import datetime
from sqlalchemy import (
    Integer, String, DateTime, Enum as SqlAlchemyEnum, ForeignKey, CheckConstraint,
    Index, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List, TYPE_CHECKING

from app.db.base import Base
from app.core.enum import SessaoCaixaStatus

if TYPE_CHECKING:
    from .funcionario import Funcionario
    from .venda import Venda
    from .movimentacao_financeira import MovimentacaoFinanceira


class SessaoCaixa(Base):
    """Modelo ORM que representa uma sessao/turno de caixa na tabela 'sessao_caixa'."""

    __tablename__ = "sessao_caixa"
    __table_args__ = (
        CheckConstraint("saldo_inicial >= 0", name="ck_sessao_caixa_saldo_inicial_nao_negativo"),
        # UMA sessao aberta por terminal, garantida pelo BANCO e nao pela tela.
        # Dois caixas operando juntos sao duas sessoes abertas -- uma em cada
        # terminal. Deixar essa trava so na interface convidaria a corrida entre
        # dois cliques simultaneos na mesma maquina.
        Index(
            "ix_sessao_caixa_aberta_por_terminal",
            "terminal_hwid",
            unique=True,
            sqlite_where=text("status = 'ABERTO'"),
        ),
    )

    # --- Identificacao ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, doc="ID unico da sessao de caixa (PK)")

    # --- Vinculos ---
    funcionario_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("funcionarios.id"),
        nullable=False,
        index=True,
        doc="ID do funcionario que assumiu o caixa (FK)"
    )

    # --- Status ---
    status: Mapped[SessaoCaixaStatus] = mapped_column(
        SqlAlchemyEnum(SessaoCaixaStatus),
        default=SessaoCaixaStatus.ABERTO,
        nullable=False,
        doc="Status atual da sessao de caixa"
    )

    # --- Terminal ---
    # Identidade da maquina, o mesmo HWID de `terminais_conectados`. E o que
    # permite dois caixas operando ao mesmo tempo: cada sessao sabe ONDE foi
    # aberta, nao so por quem.
    #
    # Nullable porque o campo nasce depois da tabela e porque a loja de um PC so
    # pode nao ter terminal nomeado -- ausencia significa "o unico caixa".
    terminal_hwid: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True,
        doc="HWID do terminal em que a sessao foi aberta"
    )

    # --- Financeiro (valores em centavos) ---
    saldo_inicial: Mapped[int] = mapped_column(Integer, nullable=False, doc="Dinheiro de troco na abertura (centavos)")
    saldo_final_esperado: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, doc="Soma automatica ao encerrar (centavos)")
    # O que o operador CONTOU, ao lado do que o sistema ESPERAVA. Os dois juntos
    # sao a quebra de caixa; guardar so a diferenca perderia de vista qual dos
    # dois lados estava errado.
    saldo_final_informado: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        doc="Dinheiro efetivamente contado na gaveta ao fechar (centavos)"
    )

    # --- Datas ---
    data_abertura: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False, doc="Inicio do expediente")
    data_fechamento: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, doc="Encerramento do expediente")

    # --- Relacionamentos ---
    funcionario: Mapped["Funcionario"] = relationship(
        "Funcionario",
        back_populates="sessoes_caixa",
        doc="Funcionario responsavel pelo caixa"
    )
    vendas: Mapped[List["Venda"]] = relationship(
        "Venda",
        back_populates="sessao_caixa",
        doc="Vendas realizadas nesta sessao de caixa"
    )
    movimentacoes: Mapped[List["MovimentacaoFinanceira"]] = relationship(
        "MovimentacaoFinanceira",
        back_populates="sessao_caixa",
        doc="Todo dinheiro que entrou e saiu neste turno (o que o fechamento le)"
    )
