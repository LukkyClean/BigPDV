# ---------------------------------------------------------------------------
# ARQUIVO: schemas/estoque.py
# DESCRIÇÃO: Schemas Pydantic para validação de dados de Estoque.
# ---------------------------------------------------------------------------

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

# =========================
# Schema Pydantic: EstoqueCreate (Criação)
# =========================
class EstoqueCreate(BaseModel):
    """
    Schema para validar os dados de ENTRADA ao criar um novo registro de Estoque.
    Estes dados são enviados separadamente (ou para um endpoint dedicado).
    """
    # Nota: Assumindo valores monetários em centavos (Integer)
    valor_varejo: int = Field(
        ...,
        description="Valor de venda no varejo (em centavos)."
    )
    quantidade: int = Field(
        default=0, # Define 0 como padrão se não for fornecido
        description="Quantidade inicial em estoque."
    )
    valor_entrada: Optional[int] = Field(
        None, 
        description="Valor de custo/entrada do produto (em centavos)."
    )
    valor_atacado: Optional[int] = Field(
        None, 
        description="Valor de venda no atacado (em centavos)."
    )
    quantidade_ideal: Optional[int] = Field(
        None, 
        description="Quantidade de estoque considerada ideal."
    )
    quantidade_minima: Optional[int] = Field(
        None, 
        description="Quantidade mínima para acionar alertas de reposição."
    )

# =========================
# Schema Pydantic: EstoqueRead (Leitura/Resposta)
# =========================
class EstoqueRead(EstoqueCreate):
    """
    Schema para formatar os dados de SAÍDA (resposta) do estoque.
    Herda os campos de EstoqueCreate e adiciona o ID do produto.
    """
    id: int = Field(
        ...,
        description="ID do produto (chave primária/estrangeira de Produto)"
    )
    # Somente leitura: é calculado pelo livro de estoque a cada compra, nunca
    # enviado pelo cliente. Editar o preço de custo de referência (valor_entrada)
    # não altera este número — é o que impede um reajuste de fornecedor de
    # reescrever o lucro já apurado.
    custo_medio: Optional[int] = Field(
        None,
        description="Custo médio ponderado calculado, base do CMV (em centavos)."
    )

class EstoqueUpdate(BaseModel):
    """
    Schema para ATUALIZAR um registro de Estoque.
    Todos os campos são opcionais.
    """
    valor_varejo: Optional[int] = Field(
        None,
        description="Novo valor de venda no varejo (em centavos)."
    )
    quantidade: Optional[int] = Field(
        None,
        description="Nova quantidade em estoque."
    )
    valor_entrada: Optional[int] = Field(
        None, 
        description="Novo valor de custo/entrada (em centavos)."
    )
    valor_atacado: Optional[int] = Field(
        None, 
        description="Novo valor de venda no atacado (em centavos)."
    )
    quantidade_ideal: Optional[int] = Field(
        None, 
        description="Nova quantidade de estoque ideal."
    )
    quantidade_minima: Optional[int] = Field(
        None, 
        description="Nova quantidade mínima para reposição."
    )

    # Permite que o Pydantic leia de um objeto ORM
    model_config = ConfigDict(from_attributes=True)