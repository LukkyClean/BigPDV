# ---------------------------------------------------------------------------
# ARQUIVO: db/models/conta_pagar.py
# DESCRIÇÃO: Modelo SQLAlchemy para a tabela 'contas_pagar'.
#            O que a loja DEVE: aluguel, fornecedor, salário, imposto.
# ---------------------------------------------------------------------------

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enum import ContaPagarStatus
from app.db.base import Base

if TYPE_CHECKING:
    from .conta_bancaria import ContaBancaria
    from .fornecedor import Fornecedor
    from .plano_conta import PlanoConta


class ContaPagar(Base):
    """Uma obrigação da loja, com valor e data de vencimento.

    DOCUMENTO, NÃO LANÇAMENTO -- e a diferença é a regra mais importante deste
    módulo. Esta linha MUDA: prorrogar vencimento, corrigir valor digitado
    errado e cancelar são rotina, e cada alteração deixa rastro em
    `historico_financeiro`. O livro do dinheiro (`movimentacoes_financeiras`) é
    o oposto: só insere, e erro se corrige por estorno.

    Confundir as duas camadas é o que faz ERP virar planilha com senha. Uma
    conta que ainda não venceu não é dinheiro que saiu; só a BAIXA gera
    movimento, e é por isso que `movimentacao_financeira_id` nasce nulo.
    """

    __tablename__ = "contas_pagar"
    __table_args__ = (
        CheckConstraint("valor > 0", name="ck_conta_pagar_valor_positivo"),
        # Conta PAGA tem que dizer quando e quanto; PENDENTE e CANCELADA não
        # podem ter pagamento nenhum pendurado. Sem isto, um estorno malfeito
        # deixaria a conta "pendente" com data de pagamento antiga, e o relatório
        # contaria a despesa duas vezes.
        CheckConstraint(
            "(status = 'PAGA' AND pago_em IS NOT NULL AND valor_pago IS NOT NULL)"
            " OR (status <> 'PAGA' AND pago_em IS NULL AND valor_pago IS NULL)",
            name="ck_conta_pagar_baixa_coerente",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    empresa_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Empresa dona da conta",
    )

    # --- O que é ---
    descricao: Mapped[str] = mapped_column(
        String(255), nullable=False, doc="Ex.: 'Aluguel de setembro'"
    )

    # Nullable porque classificar é bom, não obrigatório: travar o cadastro por
    # falta de categoria faria o lojista desistir de registrar a conta -- e uma
    # despesa não registrada é pior que uma despesa mal classificada.
    plano_conta_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("planos_conta.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Categoria da despesa",
    )

    # Reusa o cadastro que já existe. Nem toda conta tem fornecedor (energia,
    # aluguel e salário não têm), então é opcional.
    fornecedor_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("fornecedores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="A quem se deve, quando for um fornecedor cadastrado",
    )

    # --- Quanto e quando ---
    valor: Mapped[int] = mapped_column(
        Integer, nullable=False, doc="Valor devido, em centavos"
    )
    vencimento: Mapped[date] = mapped_column(
        Date, nullable=False, index=True,
        doc="Data de vencimento. DATA PURA: não converte fuso (ver core/tempo.py)",
    )

    status: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=ContaPagarStatus.PENDENTE.value,
        server_default=ContaPagarStatus.PENDENTE.value,
        index=True,
        doc="PENDENTE, PAGA ou CANCELADA (ver ContaPagarStatus)",
    )

    # --- A baixa (nulo enquanto não pagou) ---
    # `valor_pago` é separado de `valor` porque os dois divergem na vida real:
    # juros por atraso, desconto por antecipação, ou a conta de luz que veio
    # diferente do previsto. O relatório soma o que SAIU, não o que se previa.
    valor_pago: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, doc="Valor efetivamente pago, em centavos"
    )
    pago_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, doc="Instante da baixa, em UTC"
    )
    conta_bancaria_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("contas_bancarias.id", ondelete="SET NULL"),
        nullable=True,
        doc="De onde o dinheiro saiu",
    )
    forma_pagamento_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("formas_pagamento.id", ondelete="SET NULL"),
        nullable=True,
        doc="Como foi paga (PIX, dinheiro, transferência)",
    )
    # SET NULL e nunca CASCADE: a conta não pode sumir porque alguém mexeu no
    # livro -- e o livro não deveria ser mexido de todo jeito.
    movimentacao_financeira_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("movimentacoes_financeiras.id", ondelete="SET NULL"),
        nullable=True,
        doc="Lançamento no livro do dinheiro gerado pela baixa",
    )

    # --- Recorrência ---
    # A loja paga aluguel todo mês, e redigitar isso doze vezes por ano é o tipo
    # de atrito que faz o módulo ser abandonado. Modelado como "ao dar baixa,
    # nasce a do mês que vem" em vez de gerar doze contas de uma vez: assim o
    # valor pode mudar (a luz nunca vem igual) e ninguém precisa apagar as onze
    # restantes quando o contrato acaba.
    recorrente: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0",
        doc="Ao dar baixa, gera automaticamente a ocorrência do mês seguinte",
    )

    observacao: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, doc="Anotação livre do lojista"
    )

    # --- Rastro ---
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True,
        doc="Instante de criação, em UTC",
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False,
        doc="Última alteração, em UTC",
    )

    # --- Relacionamentos ---
    plano_conta: Mapped[Optional["PlanoConta"]] = relationship(
        "PlanoConta", back_populates="contas_pagar"
    )
    fornecedor: Mapped[Optional["Fornecedor"]] = relationship("Fornecedor")
    conta_bancaria: Mapped[Optional["ContaBancaria"]] = relationship("ContaBancaria")

    def __repr__(self) -> str:
        return (
            f"<ContaPagar(id={self.id}, '{self.descricao}', "
            f"{self.valor} venc={self.vencimento} {self.status})>"
        )
