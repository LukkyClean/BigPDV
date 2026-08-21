# ---------------------------------------------------------------------------
# ARQUIVO: db/models/venda.py
# DESCRICAO: Modelo SQLAlchemy para a tabela 'vendas'.
#            Entidade central do fluxo transacional do PDV.
# ---------------------------------------------------------------------------

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Enum as SqlAlchemyEnum, ForeignKey, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List, TYPE_CHECKING

from app.db.base import Base
from app.core.enum import VendaStatus

if TYPE_CHECKING:
    from .cliente import Cliente
    from .funcionario import Funcionario
    from .sessao_caixa import SessaoCaixa
    from .venda_produto import ProdutoVenda
    from .venda_pagamento import PagamentoVenda
    from .log_produto import LogProduto


class Venda(Base):
    """Modelo ORM que representa uma venda na tabela 'vendas'."""

    __tablename__ = "vendas"
    __table_args__ = (
        CheckConstraint("subtotal >= 0", name="ck_venda_subtotal_nao_negativo"),
        CheckConstraint("entrega >= 0", name="ck_venda_entrega_nao_negativo"),
        CheckConstraint("total >= 0", name="ck_venda_total_nao_negativo"),
    )

    # --- Identificacao ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, doc="ID unico da venda (PK)")

    # --- Vinculos ---
    cliente_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("clientes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Cliente atrelado. Nulo para vendas rapidas de balcao (FK)"
    )
    funcionario_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("funcionarios.id"),
        nullable=False,
        index=True,
        doc="Vendedor responsavel pelo caixa (FK)"
    )
    sessao_caixa_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("sessao_caixa.id", ondelete="SET NULL"),
        nullable=True,
        doc="Vinculo com o turno/caixa atual (FK)"
    )

    # --- Status ---
    status: Mapped[VendaStatus] = mapped_column(
        SqlAlchemyEnum(VendaStatus),
        default=VendaStatus.ATIVA,
        nullable=False,
        doc="Status atual da venda"
    )
    observacao: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Campo livre para anotacoes ou observacoes sobre a venda"
    )
    observacao_interna: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Observacao interna (nao impressa no comprovante)"
    )

    # --- Cancelamento ---
    motivo_cancelamento: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Motivo informado ao cancelar uma venda finalizada",
    )

    # --- Numeração oficial (atribuída apenas ao finalizar) ---
    numero_venda: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        unique=True,
        doc="Número sequencial oficial da venda, atribuído somente ao finalizar",
    )

    # --- Financeiro (valores em centavos) ---
    subtotal: Mapped[int] = mapped_column(Integer, default=0, nullable=False, doc="Soma dos itens sem descontos e fretes (centavos)")
    entrega: Mapped[int] = mapped_column(Integer, default=0, nullable=False, doc="Valor do frete/motoboy (centavos)")
    acrescimo: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default="0", doc="Acrescimo de juros/cartao aplicado no checkout (centavos)")
    @property
    def total_bruto(self):
        total_itens = sum(item.subtotal for item in self.itens)
        return total_itens + (self.entrega or 0)
    @property
    def descontos(self):
        return sum(item.desconto for item in self.itens)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False, doc="(subtotal + entrega) - (descontos) + acrescimo (centavos)")
    @property
    def troco(self):
        total_pago = sum(pagamento.valor for pagamento in self.pagamentos)
        return max(0, total_pago - self.total)
    
    # --- Datas ---
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False, doc="Data de criacao do rascunho")
    # A FILA DO CAIXA. NULL = em montagem; preenchida = o atendente entregou.
    #
    # E uma COLUNA e nao um valor novo em `VendaStatus` de proposito. O modulo
    # compara status por igualdade em varios lugares -- a listagem e o
    # `get_sales_status`, que alimenta os cards ATIVAS/FINALIZADAS/CANCELADAS.
    # Um `AGUARDANDO_PAGAMENTO` obrigaria a revisar toda comparacao, e uma
    # esquecida faz a venda sumir de uma contagem SEM ERRO NENHUM -- com tres
    # lojas em producao nessas telas. Aqui o status continua ATIVA nos dois
    # casos e nada que filtra status muda.
    #
    # E SINAL DE LISTA, NAO REGRA DE NEGOCIO: `finish_sale` ignora esta coluna
    # por completo. O caixa pode finalizar venda que nunca entrou na fila, e
    # pode editar uma que entrou. Nenhuma regra de dinheiro depende dela.
    #
    # Timestamp e nao booleano: custa o mesmo e da a ordem da fila de graca --
    # quem esperou mais aparece primeiro.
    enviada_ao_caixa_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True,
        doc="Quando o atendente mandou a venda para a fila do caixa. NULL = em montagem",
    )
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, doc="Ultima alteracao no carrinho")

    # --- Relacionamentos ---
    cliente: Mapped[Optional["Cliente"]] = relationship(
        "Cliente",
        back_populates="vendas",
        doc="Cliente associado a esta venda"
    )
    funcionario: Mapped["Funcionario"] = relationship(
        "Funcionario",
        back_populates="vendas",
        doc="Funcionario responsavel pela venda"
    )
    sessao_caixa: Mapped[Optional["SessaoCaixa"]] = relationship(
        "SessaoCaixa",
        back_populates="vendas",
        doc="Sessao de caixa em que a venda foi realizada"
    )
    itens: Mapped[List["ProdutoVenda"]] = relationship(
        "ProdutoVenda",
        back_populates="venda",
        cascade="all, delete-orphan",
        doc="Itens do carrinho desta venda"
    )
    pagamentos: Mapped[List["PagamentoVenda"]] = relationship(
        "PagamentoVenda",
        back_populates="venda",
        cascade="all, delete-orphan",
        doc="Pagamentos desta venda"
    )
    logs_produto: Mapped[List["LogProduto"]] = relationship(
        "LogProduto",
        back_populates="venda",
        doc="Logs de movimentacao de estoque desta venda"
    )
