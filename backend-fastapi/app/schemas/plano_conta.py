# ---------------------------------------------------------------------------
# ARQUIVO: schemas/plano_conta.py
# DESCRIÇÃO: Schemas Pydantic das categorias de despesa e receita.
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.enum import PlanoContaTipo


class PlanoContaCreate(BaseModel):
    """Nova categoria."""

    nome: str = Field(
        ..., min_length=1, max_length=100, description="Ex.: 'Aluguel', 'Energia'"
    )
    tipo: PlanoContaTipo = Field(
        PlanoContaTipo.DESPESA,
        description=(
            "DESPESA (gasto para a loja existir), CUSTO (compra de mercadoria "
            "para revender) ou RECEITA. A diferença entre os dois primeiros é a "
            "conta do lucro -- ver PlanoContaTipo"
        ),
    )


class PlanoContaUpdate(BaseModel):
    """Alteração parcial. Campo ausente = não mexe."""

    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    # `tipo` ENTROU em 02/09/2026, e com trava. Ficava de fora porque trocar a
    # natureza de uma categoria já lançada viraria despesa em receita no
    # relatório sem ninguém tocar numa conta -- e isso continua valendo.
    #
    # O que mudou é que DESPESA <-> CUSTO deixou de ser detalhe: é ela que diz
    # se a compra sai do lucro no dia da compra ou no dia da venda. Sem poder
    # corrigir, a loja que criou "Compra de peças" à mão fica com o lucro errado
    # para sempre. As duas são SAÍDA -- o que muda é quando saem do lucro.
    #
    # RECEITA continua trancada em categoria já em uso: essa troca inverte o
    # sinal do dinheiro, e o serviço recusa (ver `atualizar_plano_conta`).
    tipo: Optional[PlanoContaTipo] = Field(
        None, description="Só entre DESPESA e CUSTO quando a categoria já está em uso"
    )
    ativo: Optional[bool] = Field(
        None, description="Desativar tira dos novos lançamentos e preserva o histórico"
    )


class PlanoContaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    tipo: str
    padrao: bool = Field(..., description="Veio do conjunto semeado pelo sistema")
    ativo: bool
    criado_em: datetime
    em_uso: bool = Field(
        False,
        description=(
            "Há conta lançada nesta categoria. A tela usa para explicar por que "
            "excluir não é oferecido — só desativar."
        ),
    )
