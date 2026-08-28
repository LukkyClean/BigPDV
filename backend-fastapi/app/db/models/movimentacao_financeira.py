# ---------------------------------------------------------------------------
# ARQUIVO: movimentacao_financeira.py
# DESCRIÇÃO: Modelo SQLAlchemy para a tabela 'movimentacoes_financeiras'.
#            Livro-razão ÚNICO do dinheiro: tudo que entra e sai passa por aqui.
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enum import MovimentacaoFinanceiraOrigem, MovimentacaoFinanceiraTipo
from app.db.base import Base


class MovimentacaoFinanceira(Base):
    """Um movimento de dinheiro. Imutável por design: só se insere.

    É o gêmeo de `movimentacoes_estoque` do lado do caixa — mesmo papel, mesmo
    formato (uma coluna `origem` mais FKs opcionais para a causa). Antes dele o
    sistema sabia quanto tinha vendido, mas não quanto TINHA QUE ESTAR na gaveta:
    faltava lugar para o troco da abertura, a sangria e o suprimento, que são
    dinheiro sem venda nenhuma por trás.

    COBRANÇA NÃO É MOVIMENTO. As tabelas `pagamentos_venda` e
    `ordem_servico_pagamentos` guardam o que foi COMBINADO (forma, parcelas,
    juros, vencimento). Esta guarda o dinheiro que ANDOU. Enquanto tudo é à
    vista as duas coisas coincidem e a distinção parece burocracia; no dia em
    que a loja vender fiado, a cobrança nasce sem movimento e só o movimento
    pode responder pelo fechamento do caixa.
    """

    __tablename__ = "movimentacoes_financeiras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # --- Direção e natureza ---
    # O valor é sempre POSITIVO; quem diz se soma ou subtrai é o `tipo`. Guardar
    # negativo no valor convida a somar tudo sem filtrar e a errar o sinal.
    tipo: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
        doc="ENTRADA ou SAIDA (ver MovimentacaoFinanceiraTipo)",
    )
    origem: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=MovimentacaoFinanceiraOrigem.VENDA.value,
        index=True,
        doc="Quem causou: VENDA, ORDEM_SERVICO, ABERTURA, SANGRIA, SUPRIMENTO, "
            "RECEBIMENTO ou DESPESA",
    )
    valor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Valor movimentado, sempre positivo (centavos)",
    )

    # --- Onde caiu ---
    # NULL tem significado: o dinheiro não passou por gaveta nenhuma. É o caso da
    # loja que não usa controle de caixa (continua como sempre foi) e também do
    # boleto pago pelo banco, que é movimento real mas não encosta no caixa.
    sessao_caixa_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("sessao_caixa.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Turno de caixa em que o movimento caiu; NULL se não passou pela gaveta",
    )

    # Onde o dinheiro está DEPOIS do movimento. Complementa `sessao_caixa_id`,
    # que só sabe dizer "passou por um turno de gaveta ou não" -- e isso responde
    # por uma gaveta, não por uma loja que também tem conta no banco.
    #
    # NULL nas linhas antigas e em tudo que a Onda 1 não alcançar. É o mesmo
    # tipo de lacuna admitida em `ordem_servico_pagamentos.data_pagamento`:
    # inventar a conta de origem de um movimento passado seria pior que
    # reconhecer que não se sabe.
    conta_bancaria_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("contas_bancarias.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Conta de onde o dinheiro saiu ou para onde entrou",
    )

    # --- A cobrança que causou (quando houve uma) ---
    # SET NULL em tudo, nunca CASCADE: linha de dinheiro não pode desaparecer
    # porque o documento que a originou foi apagado.
    venda_pagamento_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("pagamentos_venda.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Pagamento de venda que originou (quando origem = VENDA)",
    )
    ordem_servico_pagamento_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("ordem_servico_pagamentos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Pagamento de OS que originou (quando origem = ORDEM_SERVICO)",
    )
    forma_pagamento_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("formas_pagamento.id", ondelete="SET NULL"),
        nullable=True,
        doc="Forma do movimento — é por ela que o fechamento confere dinheiro, "
            "cartão e PIX separadamente",
    )

    # --- Quem fez ---
    funcionario_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("funcionarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Funcionário responsável pelo movimento",
    )
    # Nome desnormalizado, mesma razão do `usuario_nome` no livro de estoque:
    # "quem tirou os R$ 200" precisa sobreviver ao desligamento do funcionário.
    funcionario_nome: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Nome do funcionário no momento do movimento",
    )

    # Obrigatório em SANGRIA e SUPRIMENTO — é o que transforma "sumiu dinheiro"
    # em "saiu R$ 200 às 14h para o cofre". A regra é do serviço, não da coluna:
    # aqui fica nullable porque venda e abertura não têm motivo a declarar.
    motivo: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Motivo declarado (obrigatório em sangria e suprimento)",
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        index=True,
        doc="Instante do movimento, em UTC (ver app/core/tempo.py)",
    )

    # --- Relacionamentos (leitura/auditoria) ---
    sessao_caixa = relationship("SessaoCaixa", back_populates="movimentacoes")
    forma_pagamento = relationship("FormaPagamento")
    funcionario = relationship("Funcionario")

    def __repr__(self) -> str:
        return (
            f"<MovimentacaoFinanceira(id={self.id}, {self.tipo} {self.origem} "
            f"valor={self.valor})>"
        )
