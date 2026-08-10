# ---------------------------------------------------------------------------
# ARQUIVO: movimentacao_estoque.py
# DESCRIÇÃO: Modelo SQLAlchemy para a tabela 'movimentacoes_estoque'.
#            Registra todo histórico de entradas, saídas e ajustes de estoque.
# ---------------------------------------------------------------------------

from sqlalchemy import Float, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql.sqltypes import Enum as SQLAlchemyEnum
from datetime import datetime
from typing import Optional

from app.db.base import Base
from app.core.enum import MovimentacaoTipo, MovimentacaoOrigem


class MovimentacaoEstoque(Base):
    """
    Registra cada movimentação de estoque (entrada, saída ou ajuste).
    Imutável por design: nunca deve ser editada ou excluída, apenas inserida.
    """
    __tablename__ = "movimentacoes_estoque"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Referência ao produto
    #
    # ATENÇÃO ao CASCADE: apagar um produto apagaria junto todo o histórico de
    # estoque dele — e, desde que este livro passou a carregar custo, também o
    # lucro já apurado do período. Isso contradiz o `produto_nome` logo abaixo,
    # que existe justamente para a linha sobreviver ao cadastro.
    #
    # Por que continua CASCADE: não existe delete de produto no sistema (a
    # exclusão é lógica, via `ativo`), então a bomba não tem estopim. Trocar por
    # RESTRICT no SQLite exige RECRIAR esta tabela, e uma migração que falha
    # impede o backend de subir (ver db/migrations.py) — ou seja, loja parada.
    # Não vale correr um risco real hoje para desarmar um risco que não existe.
    # A guarda de verdade é o teste que falha se um hard delete aparecer:
    # test_movimentacao_estoque.py::test_produto_nao_tem_delete_fisico.
    produto_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("produtos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID do produto movimentado"
    )
    # Nome desnormalizado: preserva o histórico mesmo se o produto for renomeado
    produto_nome: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Nome do produto no momento da movimentação"
    )

    # Referência ao usuário que realizou a movimentação
    usuario_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID do usuário que realizou a movimentação"
    )
    # Nome desnormalizado: preserva o histórico mesmo se o usuário for removido
    usuario_nome: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Nome do usuário no momento da movimentação"
    )

    # Tipo e quantidades
    tipo: Mapped[MovimentacaoTipo] = mapped_column(
        SQLAlchemyEnum(MovimentacaoTipo),
        nullable=False,
        doc="Tipo da movimentação: ENTRADA, SAIDA ou AJUSTE"
    )
    # Fracionadas para unidades de peso (2,5 kg). Ver a nota em db/models/estoque.py
    # sobre por que a mudança de tipo não exigiu migration.
    quantidade: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Quantidade movimentada (sempre positivo)"
    )
    quantidade_anterior: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Quantidade em estoque antes da movimentação"
    )
    quantidade_posterior: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Quantidade em estoque após a movimentação"
    )

    # --- Origem (de onde veio a movimentação) ---
    # Esta tabela é o livro-razão ÚNICO do estoque. `origem` diz quem causou a
    # movimentação e os dois FKs abaixo apontam para o documento correspondente,
    # de forma consultável — antes o vínculo só existia em texto na observação.
    origem: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=MovimentacaoOrigem.LEGADO.value,
        default=MovimentacaoOrigem.MANUAL.value,
        index=True,
        doc="Origem: LEGADO, MANUAL, CADASTRO, VENDA ou ORDEM_SERVICO"
    )
    venda_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("vendas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Venda que causou a movimentação (quando origem = VENDA)"
    )
    ordem_servico_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("ordens_servico.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="OS que causou a movimentação (quando origem = ORDEM_SERVICO)"
    )

    # --- Custo (o que torna este livro capaz de responder sobre lucro) ---
    # Numa ENTRADA de compra é o valor efetivamente PAGO por unidade; numa SAÍDA
    # é o custo médio no instante em que a peça saiu — ou seja, o CMV daquela
    # venda/OS. Congelado aqui de propósito: se o relatório fosse perguntar o
    # custo ao cadastro do produto, todo reajuste do fornecedor reescreveria o
    # lucro do passado. NULL nas linhas anteriores a este campo — o custo delas
    # não é recuperável, e estimar seria inventar.
    custo_unitario: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Custo unitário congelado no momento da movimentação (centavos)"
    )

    observacao: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Observação/motivo da movimentação"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        doc="Data e hora da movimentação"
    )

    # Relacionamentos (somente leitura para auditoria)
    produto = relationship("Produto", doc="Produto movimentado")
    usuario = relationship("Usuario", doc="Usuário que realizou a movimentação")
