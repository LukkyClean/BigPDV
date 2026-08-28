# ---------------------------------------------------------------------------
# ARQUIVO: db/models/conta_bancaria.py
# DESCRIÇÃO: Modelo SQLAlchemy para a tabela 'contas_bancarias'.
#            Onde o dinheiro da loja fica parado.
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enum import ContaBancariaTipo
from app.db.base import Base


class ContaBancaria(Base):
    """Uma conta onde o dinheiro da loja fica: a gaveta, o Itaú, o Nubank.

    POR QUE JÁ NA PRIMEIRA ONDA, se contas a pagar funcionaria sem ela: porque
    `movimentacoes_financeiras` só sabia responder "passou pela gaveta ou não"
    (`sessao_caixa_id` nulo ou não), e isso resolve UMA gaveta. Um fluxo de caixa
    que não sabe se os R$ 8 mil estão no caixa ou na conta corrente não consegue
    dizer se dá para pagar o fornecedor amanhã -- que é a única pergunta que o
    módulo existe para responder.

    Acrescentar a coluna agora custa uma migration numa tabela quase vazia.
    Acrescentar depois custa a mesma migration com lançamento de loja dentro, e
    todo lançamento antigo sem saber de onde saiu.

    NÃO é integração bancária: ninguém se conecta a banco nenhum aqui. É só o
    nome do lugar, para o dinheiro ter endereço.
    """

    __tablename__ = "contas_bancarias"
    __table_args__ = (
        UniqueConstraint("empresa_id", "nome", name="uq_conta_bancaria_empresa_nome"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    empresa_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Empresa dona da conta",
    )

    nome: Mapped[str] = mapped_column(
        String(100), nullable=False, doc="Ex.: 'Caixa da loja', 'Itaú c/c 1234'"
    )

    tipo: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=ContaBancariaTipo.BANCO.value,
        doc="CAIXA (espécie na loja) ou BANCO (ver ContaBancariaTipo)",
    )

    # A conta que a tela já vem preenchendo. Evita o lojista escolher a mesma
    # coisa dezenas de vezes por semana.
    principal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0",
        doc="Conta sugerida por padrão nos lançamentos",
    )

    ativo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1",
        doc="Conta disponível para novos lançamentos",
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
        doc="Instante de criação, em UTC (ver app/core/tempo.py)",
    )

    def __repr__(self) -> str:
        return f"<ContaBancaria(id={self.id}, {self.tipo} '{self.nome}')>"
