# ---------------------------------------------------------------------------
# ARQUIVO: db/models/conta_receber.py
# DESCRIÇÃO: Modelo SQLAlchemy para a tabela 'contas_receber'.
#            O que o cliente ainda deve, e o que a operadora tem para repassar.
# ---------------------------------------------------------------------------

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enum import ContaReceberStatus
from app.db.base import Base

if TYPE_CHECKING:
    from .cliente import Cliente
    from .conta_bancaria import ContaBancaria


class ContaReceber(Base):
    """Dinheiro prometido que ainda não entrou.

    Vale aqui a MESMA regra que rege o contas a pagar: documento muda,
    lançamento não. Esta linha é DOCUMENTO -- prorrogar e corrigir são rotina, e
    deixam rastro em `historico_financeiro`. Só a BAIXA escreve no livro, com
    origem RECEBIMENTO.

    NASCE DE UMA PROMESSA QUE JÁ EXISTIA. O sistema sempre soube separar
    dinheiro de promessa: `registrar_pagamentos_de_venda` e a gêmea da OS pulam
    o pagamento com vencimento futuro, com a regra escrita lá -- "promessa: é
    conta a receber, não gaveta". O que faltava era a conta a receber nascer
    dessa promessa. Por isso esta tabela é puramente aditiva: nenhum fluxo de
    venda ou de OS muda de comportamento, só passa a deixar um registro.
    """

    __tablename__ = "contas_receber"
    __table_args__ = (
        CheckConstraint("valor > 0", name="ck_conta_receber_valor_positivo"),
        CheckConstraint("taxa >= 0", name="ck_conta_receber_taxa_nao_negativa"),
        CheckConstraint("juros >= 0", name="ck_conta_receber_juros_nao_negativo"),
        # Mesma coerência exigida no contas a pagar: recebida diz quando e
        # quanto; pendente e cancelada não carregam recebimento nenhum. Sem
        # isto, um estorno malfeito deixaria a conta "pendente" com data antiga
        # e o relatório contaria a receita duas vezes.
        CheckConstraint(
            "(status = 'RECEBIDA' AND recebido_em IS NOT NULL AND valor_recebido IS NOT NULL)"
            " OR (status <> 'RECEBIDA' AND recebido_em IS NULL AND valor_recebido IS NULL)",
            name="ck_conta_receber_baixa_coerente",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    empresa_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # --- O que é ---
    descricao: Mapped[str] = mapped_column(
        String(255), nullable=False, doc="Ex.: 'Venda 42 — João da Silva'"
    )
    # Nullable: venda de balcão sem cliente identificado também pode ficar
    # fiada, e recusar o registro por falta de cadastro deixaria a dívida
    # invisível -- que é justamente o que o módulo veio resolver.
    cliente_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("clientes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Quem deve, quando identificado",
    )

    # --- Quanto e quando ---
    # `valor` é o LÍQUIDO -- o que de fato vai entrar. Num fiado é o que o
    # cliente deve; num recebível de cartão é o que a operadora repassa, já sem
    # a taxa dela. Guardar o bruto aqui faria o fluxo de caixa projetar dinheiro
    # que nunca vai chegar.
    valor: Mapped[int] = mapped_column(
        Integer, nullable=False, doc="Valor a receber, líquido (centavos)"
    )
    # O que a operadora retém. Zero no fiado e no boleto. Digitado à mão, do
    # papel de taxas que a loja recebe da credenciadora -- não há tabela de
    # taxas no sistema, e taxas mudam de contrato.
    taxa: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        doc="Retido pela operadora (centavos). bruto = valor + taxa",
    )
    vencimento: Mapped[date] = mapped_column(
        Date, nullable=False, index=True,
        doc="Quando o dinheiro entra. DATA PURA: não converte fuso",
    )

    # Juros/multa por atraso, cobrados do cliente na hora de quitar.
    #
    # Coluna própria e não embutida em `valor_recebido` porque juros de mora é
    # RECEITA FINANCEIRA, não venda: somado ao principal, ele inflaria o
    # faturamento do mês com dinheiro que não veio de mercadoria nem de serviço.
    # Sem a separação, "recebi R$ 110 de uma dívida de R$ 100" seria
    # indistinguível de "o cliente pagou errado".
    juros: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        doc="Juros/multa recebidos por atraso (centavos). valor_recebido inclui",
    )

    status: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=ContaReceberStatus.PENDENTE.value,
        server_default=ContaReceberStatus.PENDENTE.value,
        index=True,
        doc="PENDENTE, RECEBIDA ou CANCELADA",
    )

    # --- A baixa (nulo enquanto não entrou) ---
    valor_recebido: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, doc="Quanto entrou de fato (centavos)"
    )
    recebido_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, doc="Instante da baixa, em UTC"
    )
    conta_bancaria_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("contas_bancarias.id", ondelete="SET NULL"),
        nullable=True,
        doc="Onde o dinheiro caiu",
    )
    forma_pagamento_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("formas_pagamento.id", ondelete="SET NULL"),
        nullable=True,
        doc="Como o cliente pagou na hora de quitar",
    )
    movimentacao_financeira_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("movimentacoes_financeiras.id", ondelete="SET NULL"),
        nullable=True,
        doc="Lançamento no livro gerado pela baixa",
    )

    # --- De onde veio ---
    # SET NULL e nunca CASCADE: apagar a venda não pode levar junto a dívida do
    # cliente. Um dos dois é preenchido quando a conta nasce de um fecho; os
    # dois ficam nulos quando ela foi lançada à mão.
    venda_pagamento_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("pagamentos_venda.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Pagamento de venda que originou a promessa",
    )
    ordem_servico_pagamento_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("ordem_servico_pagamentos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Pagamento de OS que originou a promessa",
    )

    observacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    cliente: Mapped[Optional["Cliente"]] = relationship("Cliente")
    conta_bancaria: Mapped[Optional["ContaBancaria"]] = relationship("ContaBancaria")

    def __repr__(self) -> str:
        return (
            f"<ContaReceber(id={self.id}, '{self.descricao}', "
            f"{self.valor} venc={self.vencimento} {self.status})>"
        )
