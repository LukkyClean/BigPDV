# ---------------------------------------------------------------------------
# ARQUIVO: schemas/sessao_caixa.py
# DESCRIÇÃO: Schemas Pydantic do turno de caixa (abertura, movimentos e
#            fechamento) e do resumo que o operador confere.
# ---------------------------------------------------------------------------

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.enum import SessaoCaixaStatus


# ===========================================================================
# ABERTURA
# ===========================================================================

class SessaoCaixaAbrir(BaseModel):
    """Dados para abrir o turno."""

    saldo_inicial: int = Field(
        ...,
        ge=0,
        description="Dinheiro de troco colocado na gaveta na abertura (centavos)",
    )
    # O HWID identifica a máquina e é o que permite dois caixas operando ao
    # mesmo tempo. Vem do cliente porque o token não o carrega — e não vale
    # mexer no login, que as três lojas em produção usam todo dia.
    terminal_hwid: Optional[str] = Field(
        None,
        max_length=255,
        description="HWID do terminal. Omitir só faz sentido em loja de um PC só",
    )


# ===========================================================================
# SANGRIA E SUPRIMENTO
# ===========================================================================

class MovimentoCaixaCreate(BaseModel):
    """Dinheiro entrando ou saindo da gaveta sem que haja venda por trás."""

    valor: int = Field(..., gt=0, description="Valor movimentado (centavos)")
    # Obrigatório e sem default: é o que transforma "sumiu dinheiro" em
    # "saiu R$ 200 às 14h para o cofre". Um motivo opcional viraria motivo vazio.
    motivo: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Por que o dinheiro entrou ou saiu",
    )
    # Preenchido quando a sangria exige autorização e quem opera não é gerente:
    # o supervisor digita o PIN ali na hora e libera aquela retirada, sem trocar
    # o operador do caixa. Reusa o mesmo PIN que já protege cancelamento,
    # reabertura e desconto (configuracoes_seguranca.pin_gerente) — inventar um
    # segundo segredo seria mais uma coisa para o lojista esquecer.
    codigo_gerente: Optional[str] = Field(
        None, description="PIN do gerente, quando a sangria exigir autorização"
    )


# ===========================================================================
# FECHAMENTO
# ===========================================================================

class SessaoCaixaFechar(BaseModel):
    """Conferência da gaveta no fim do turno."""

    saldo_contado: int = Field(
        ...,
        ge=0,
        description="Dinheiro efetivamente contado na gaveta (centavos)",
    )
    observacao: Optional[str] = Field(
        None, max_length=500, description="Observação do fechamento"
    )


# ===========================================================================
# LEITURA
# ===========================================================================

class MovimentoCaixaRead(BaseModel):
    """Uma linha do livro do dinheiro, como o extrato do turno mostra."""

    id: int
    tipo: str
    origem: str
    valor: int
    motivo: Optional[str] = None
    forma_pagamento_id: Optional[int] = None
    funcionario_nome: Optional[str] = None
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class TotalPorForma(BaseModel):
    """Quanto entrou por cada forma de pagamento no turno.

    O fechamento confere forma a forma, e não só o total: dinheiro é o único que
    se conta na mão, e juntar tudo num número só esconde a diferença que importa.
    """

    forma_pagamento_id: Optional[int] = None
    forma_pagamento_nome: str
    total: int


class SessaoCaixaResumo(BaseModel):
    """O espelho do turno: o que entrou, o que saiu e o que tem que estar lá."""

    sessao_id: int
    status: SessaoCaixaStatus
    funcionario_id: int
    funcionario_nome: Optional[str] = None
    terminal_hwid: Optional[str] = None
    terminal_nome: Optional[str] = None

    data_abertura: datetime
    data_fechamento: Optional[datetime] = None

    saldo_inicial: int
    total_vendas: int = Field(..., description="Tudo que entrou por venda/OS, em qualquer forma")
    total_suprimentos: int
    total_sangrias: int

    # A conta da gaveta:
    #   saldo_inicial + entradas em DINHEIRO + suprimentos - sangrias
    # Cartão e PIX não entram aqui de propósito: eles não estão na gaveta.
    #
    # `None` significa OCULTO, não vazio. No fechamento cego o operador não pode
    # ver este número antes de contar — mas mandar `0` no lugar fazia a barra do
    # PDV anunciar "Em dinheiro na gaveta: R$ 0,00" com a gaveta cheia, e o que
    # chega para quem está no balcão é "o sistema não está somando minhas
    # vendas". Esconder é legítimo; mentir um valor não é.
    saldo_esperado_dinheiro: Optional[int] = Field(
        None, description="Dinheiro esperado na gaveta. None = oculto pelo fechamento cego"
    )

    # Só preenchidos depois do fechamento. Antes dele, no modo cego, nem o
    # esperado é devolvido ao operador (ver `fechamento_cego`).
    saldo_contado: Optional[int] = None
    diferenca: Optional[int] = Field(
        None, description="contado - esperado. Negativo = falta dinheiro"
    )

    por_forma: List[TotalPorForma] = []
    movimentos: List[MovimentoCaixaRead] = []

    model_config = ConfigDict(from_attributes=True)


class SessaoCaixaHistoricoItem(BaseModel):
    """Uma linha do histórico de turnos, na visão do dono.

    Responde as duas perguntas que ele faz: **quem fechou faltando dinheiro** e
    **quem fechou sobrando**. As duas saem do mesmo campo — `diferenca` negativa
    é falta, positiva é sobra — e as duas importam: sobra costuma ser troco não
    registrado ou venda não lançada, que é problema tanto quanto a falta.

    Os valores de fechamento são LIDOS da sessão, não recalculados: foram
    congelados no momento em que o operador conferiu. Recalcular depois faria o
    passado mudar quando um lançamento atrasado entrasse.
    """

    sessao_id: int
    status: SessaoCaixaStatus

    funcionario_id: int
    funcionario_nome: Optional[str] = None
    terminal_hwid: Optional[str] = None
    terminal_nome: Optional[str] = None

    data_abertura: datetime
    data_fechamento: Optional[datetime] = None

    saldo_inicial: int
    saldo_esperado: Optional[int] = Field(
        None, description="O que o sistema calculou que deveria estar na gaveta"
    )
    saldo_contado: Optional[int] = Field(
        None, description="O que o operador declarou ter contado"
    )
    diferenca: Optional[int] = Field(
        None, description="contado - esperado. Negativo = faltou; positivo = sobrou"
    )

    model_config = ConfigDict(from_attributes=True)


class SessaoCaixaRead(BaseModel):
    """A sessão em si, sem o resumo financeiro."""

    id: int
    status: SessaoCaixaStatus
    funcionario_id: int
    terminal_hwid: Optional[str] = None
    saldo_inicial: int
    saldo_final_esperado: Optional[int] = None
    saldo_final_informado: Optional[int] = None
    data_abertura: datetime
    data_fechamento: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
