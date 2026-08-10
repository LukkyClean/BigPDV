# ---------------------------------------------------------------------------
# ARQUIVO: estoque.py
# DESCRIÇÃO: Modelo SQLAlchemy para a tabela 'estoque', representando
#            os dados de estoque de um produto (Relação 1-para-1 com Produto).
# ---------------------------------------------------------------------------

from sqlalchemy import Float, Integer, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base

# ---------------------------------------------------------------------------
# QUANTIDADE FRACIONADA (Float) -- e por que NAO houve migracao
#
# A serigrafia vende sacola por quilo, e quilo quebrado (2,5 kg) e escolha do
# cliente na hora do pedido. Isso exige quantidade fracionada.
#
# O SQLite guarda 2.5 numa coluna declarada INTEGER: a afinidade so converte
# quando e sem perda, entao o valor fica armazenado como `real` e SUM/produto
# saem corretos. A declaracao de tipo no SQLite e orientativa, nao uma trava.
#
# Por isso o tipo mudou aqui e NAO existe migration: um `batch_alter_table`
# recriaria a tabela inteira no banco vivo de duas lojas em producao, sem
# backup automatico antes, para obter um comportamento que o banco JA tem.
# Instalacao nova cria REAL, instalacao antiga segue INTEGER, e as duas se
# comportam igual. Coberto por teste que grava 2,5 num banco criado com o
# schema antigo.
# ---------------------------------------------------------------------------

class Estoque(Base):
    """
    Representa a tabela 'estoque', contendo os dados de
    controle de estoque (quantidade, valores) de um Produto.
    """
    __tablename__ = "estoque"

    # Chave primária da tabela 'estoque' que também é chave estrangeira
    # referenciando 'produtos.id'. Isso estabelece a relação 1-para-1.
    id: Mapped[int] = mapped_column(Integer, ForeignKey("produtos.id"), primary_key=True, index=True, nullable=False, doc="ID do produto (Chave primária/estrangeira de 'produtos')")
    
    # Campos de controle de estoque
    quantidade: Mapped[float] = mapped_column(Float, default=0, doc="Quantidade atual em estoque (fracionada para unidades de peso)")
    quantidade_ideal: Mapped[float | None] = mapped_column(Float, nullable=True, doc="Quantidade de estoque considerada ideal")
    quantidade_minima: Mapped[float | None] = mapped_column(Float, nullable=True, doc="Quantidade mínima para acionar alertas de reposição")
    
    # Valores (assumindo armazenamento em centavos)
    # ATENÇÃO: `valor_entrada` e `custo_medio` NÃO são a mesma coisa, e confundir
    # os dois é o caminho mais curto para um relatório de lucro mentiroso.
    #   valor_entrada → último preço de compra. É referência, digitada à mão no
    #                   cadastro, e serve para o usuário se orientar.
    #   custo_medio   → custo contábil calculado (média ponderada), recalculado
    #                   só em ENTRADA de compra e usado para congelar o CMV nas
    #                   saídas. Editar o preço de referência não pode reescrever
    #                   o custo do que já saiu.
    # Enquanto `custo_medio` for NULL (produto cadastrado antes da média existir),
    # o sistema cai para `valor_entrada` — ver services/movimentacao_estoque.custo_atual.
    valor_entrada: Mapped[int | None] = mapped_column(Integer, nullable=True, doc="Último preço de compra, referência do cadastro (em centavos)")
    custo_medio: Mapped[int | None] = mapped_column(Integer, nullable=True, doc="Custo médio ponderado calculado, base do CMV (em centavos)")
    valor_varejo: Mapped[int] = mapped_column(Integer, nullable=False, doc="Valor de venda no varejo (em centavos)")
    valor_atacado: Mapped[int | None] = mapped_column(Integer, nullable=True, doc="Valor de venda no atacado (em centavos)")

    # Relação Lado "Um" (Estoque) para "Um" (Produto)
    produto = relationship(
        "Produto",
        back_populates="estoque",
        uselist=False, # Define a relação como 1-para-1
        doc="Relacionamento reverso Um-para-Um para o Produto"
    )