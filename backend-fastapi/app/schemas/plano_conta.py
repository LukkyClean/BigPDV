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
        description="DESPESA ou RECEITA. A Onda 1 só usa DESPESA na prática",
    )


class PlanoContaUpdate(BaseModel):
    """Alteração parcial. Campo ausente = não mexe."""

    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    # `tipo` fica de fora de propósito: trocar a natureza de uma categoria que já
    # classifica contas lançadas viraria despesa em receita no relatório, sem
    # que ninguém tivesse tocado numa conta sequer.
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
