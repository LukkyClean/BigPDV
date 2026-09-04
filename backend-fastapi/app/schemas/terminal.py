from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


PapelTerminal = Literal["PDV", "RETAGUARDA"]


class TerminalRead(BaseModel):
    """Um terminal como a tela de configuração mostra."""

    id: int
    hwid: str
    nome: Optional[str] = None
    papel: Optional[PapelTerminal] = Field(
        None, description="'PDV' ou 'RETAGUARDA'. None comporta-se como PDV"
    )
    criado_em: datetime
    atualizado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class TerminalEsteRead(TerminalRead):
    """O terminal DESTA máquina, com o que a tela precisa saber sobre ele.

    Existe separado do `TerminalRead` porque a pergunta é outra: a lista responde
    "quais máquinas a loja tem"; esta responde "eu sou qual delas, e me comporto
    como caixa?". A segunda é consultada pela tela de vendas a cada abertura, e
    ela não deveria ter que varrer a lista para descobrir a si mesma.
    """

    e_retaguarda: bool = Field(
        ..., description="True só com papel RETAGUARDA explícito. NULL = caixa"
    )


class TerminalUpdate(BaseModel):
    """O que o dono pode mudar: como a máquina se chama e o que ela é."""

    nome: Optional[str] = Field(None, max_length=60)
    papel: Optional[PapelTerminal] = None

    @field_validator("nome")
    @classmethod
    def _nome_vazio_e_nulo(cls, valor: Optional[str]) -> Optional[str]:
        """Espaço em branco não é nome.

        Sem isto, salvar o campo vazio gravaria `"  "` e a coluna Terminal do
        relatório mostraria um espaço — que parece preenchido e não é. Vazio
        volta a ser NULL, que é "ainda não batizado" e aparece como tal.
        """
        if valor is None:
            return None
        limpo = valor.strip()
        return limpo or None
