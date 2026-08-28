# ---------------------------------------------------------------------------
# ARQUIVO: schemas/conta_bancaria.py
# DESCRIÇÃO: Schemas Pydantic das contas onde o dinheiro da loja fica.
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.enum import ContaBancariaTipo


class ContaBancariaCreate(BaseModel):
    nome: str = Field(
        ..., min_length=1, max_length=100,
        description="Ex.: 'Caixa da loja', 'Itaú c/c 1234'",
    )
    tipo: ContaBancariaTipo = Field(
        ContaBancariaTipo.BANCO, description="CAIXA (espécie) ou BANCO"
    )
    principal: bool = Field(
        False, description="Vem pré-selecionada nos lançamentos"
    )


class ContaBancariaUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    tipo: Optional[ContaBancariaTipo] = None
    principal: Optional[bool] = None
    ativo: Optional[bool] = None


class ContaBancariaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    tipo: str
    principal: bool
    ativo: bool
    criado_em: datetime
