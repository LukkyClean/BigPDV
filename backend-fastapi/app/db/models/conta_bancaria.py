# ---------------------------------------------------------------------------
# ARQUIVO: db/models/conta_bancaria.py
# DESCRIÇÃO: Modelo SQLAlchemy para a tabela 'contas_bancarias'.
#            Onde o dinheiro da loja fica parado.
# ---------------------------------------------------------------------------

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
)
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

    # --- Saldo: DECLARADO uma vez, e daí em diante ANDA com o livro ---
    #
    # Este número é a ÂNCORA, não o saldo. É o mesmo desenho do "saldo inicial"
    # do Conta Azul e do Omie: o dono diz quanto tem no dia em que começa a usar
    # o sistema, e a partir dali quem move o saldo são os lançamentos. O saldo
    # de hoje é calculado (ver `financeiro_visao.saldo_atual_das_contas`), e
    # nunca é lido direto daqui.
    #
    # ERA UMA FOTO PARADA ATÉ 02/09/2026, e o motivo original morreu: dizia-se
    # que derivar o saldo daria um número fundo negativo porque o livro só
    # recebia venda e OS com `controlar_caixa` ligado E turno aberto. Desde
    # 29/08/2026 `registrar_pagamentos_de_venda` e a gêmea da OS lançam SEMPRE
    # (com `sessao_caixa_id` nulo quando não há turno), então a receita inteira
    # está no livro e a objeção caiu junto. O sintoma que sobrou era o dono
    # vendendo o dia todo e vendo o Fluxo de Caixa parado no mesmo número.
    #
    # Pode ser NEGATIVO: conta corrente no vermelho é saldo, não erro.
    saldo_informado: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        doc="Âncora declarada pelo dono (centavos, pode ser negativa)",
    )

    # O DIA da declaração, para a tela dizer "informado há 12 dias, confira".
    # NULL = nunca informado, e aí o Fluxo de Caixa pede antes de desenhar
    # qualquer linha.
    saldo_informado_em: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True,
        doc="Dia (data local) em que a âncora foi declarada; NULL = nunca foi",
    )

    # O INSTANTE da declaração, que é o corte de verdade: só entra no saldo o
    # movimento posterior a ele.
    #
    # POR QUE NÃO BASTA O DIA. O dono declara "tenho R$ 500" às 15h, depois de
    # ter vendido R$ 200 de manhã. Contando o dia inteiro, esses R$ 200 entram
    # duas vezes -- já estavam dentro dos R$ 500 que ele contou na gaveta. O
    # Conta Azul contorna isso pedindo o saldo de ONTEM; aqui o dono digita o
    # saldo de AGORA (é o que ele tem na mão) e o instante resolve, com a
    # vantagem de a venda das 16h já aparecer hoje mesmo.
    #
    # NULL nas contas declaradas antes desta coluna existir: aí o corte cai no
    # fim do dia declarado, que é a convenção conservadora do Conta Azul --
    # perde-se o movimento daquele dia, mas nunca se conta nada duas vezes.
    saldo_informado_instante: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True,
        doc="Instante UTC da declaração; é o corte do que entra no saldo derivado",
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
        doc="Instante de criação, em UTC (ver app/core/tempo.py)",
    )

    def __repr__(self) -> str:
        return f"<ContaBancaria(id={self.id}, {self.tipo} '{self.nome}')>"
