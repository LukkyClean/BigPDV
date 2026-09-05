# ---------------------------------------------------------------------------
# ARQUIVO: schemas/conta_pagar.py
# DESCRIÇÃO: Schemas Pydantic das contas a pagar — cadastro, baixa e leitura.
# ---------------------------------------------------------------------------

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enum import ContaPagarStatus


# ===========================================================================
# CADASTRO
# ===========================================================================

class ContaPagarCreate(BaseModel):
    """Uma obrigação nova."""

    descricao: str = Field(..., min_length=1, max_length=255, description="Ex.: 'Aluguel de setembro'")
    valor: int = Field(..., gt=0, description="Valor devido (centavos)")
    # DATA PURA: chega como 'AAAA-MM-DD' e é guardada assim. Não converte fuso —
    # vencimento dia 10 é dia 10 em qualquer lugar (ver core/tempo.py).
    vencimento: date = Field(..., description="Quando vence")

    plano_conta_id: Optional[int] = Field(
        None, description="Categoria. Opcional: conta sem categoria é melhor que conta não lançada"
    )
    fornecedor_id: Optional[int] = Field(
        None, description="A quem se deve, quando for fornecedor cadastrado"
    )
    recorrente: bool = Field(
        False, description="Ao dar baixa, gera automaticamente a do mês seguinte"
    )
    # `valor` é o valor DE CADA parcela, não o total. É como a maquininha e a
    # fatura falam com o lojista ("10x de 100"), e mata o arredondamento: dividir
    # um total por 3 sobra centavo, e alguém teria que decidir em qual parcela
    # jogar a sobra.
    parcelas: int = Field(
        1, ge=1, le=360,
        description="Quantidade de parcelas. 1 = conta única. Cada uma vale `valor`",
    )
    observacao: Optional[str] = Field(None, description="Anotação livre")

    @model_validator(mode="after")
    def _parcelado_ou_recorrente(self) -> "ContaPagarCreate":
        """Os dois se excluem, e não é preciosismo.

        São mecanismos diferentes: parcelado é dívida única dividida, com fim
        conhecido; recorrente é repetição sem total. Uma compra em 10x não se
        repete para sempre — aceitar os dois juntos geraria dez parcelas e, na
        baixa de cada uma, mais uma conta "do mês seguinte", multiplicando a
        dívida a cada pagamento.
        """
        if self.parcelas > 1 and self.recorrente:
            raise ValueError(
                "Uma conta parcelada não pode repetir todo mês. "
                "Escolha parcelamento ou recorrência."
            )
        return self


class ContaPagarUpdate(BaseModel):
    """Alteração parcial. Campo ausente = não mexe.

    Toda mudança de valor ou vencimento vira linha em `historico_financeiro`:
    prorrogar boleto é legítimo, mas precisa deixar rastro de quem prorrogou.
    """

    descricao: Optional[str] = Field(None, min_length=1, max_length=255)
    valor: Optional[int] = Field(None, gt=0)
    vencimento: Optional[date] = None
    plano_conta_id: Optional[int] = None
    fornecedor_id: Optional[int] = None
    recorrente: Optional[bool] = None
    observacao: Optional[str] = None

    # --- Corrigir de uma vez o resto do parcelamento ---
    #
    # Errar a data de uma compra em 72x e ter de corrigir 72 telas, uma por uma,
    # nao e conserto: e motivo para o lojista desistir do modulo. O caso real
    # veio de um emprestimo em 30x cadastrado com o vencimento errado.
    #
    # SO PARA FRENTE, e so no que ainda esta PENDENTE. Parcela paga ja virou
    # lancamento no livro, e mexer nela faria o relatorio discordar do
    # movimento; parcela anterior a esta ja aconteceu e nao se reescreve.
    #
    # No vencimento a propagacao RE-ANCORA em vez de copiar: as proximas
    # recebem o mesmo DIA do novo vencimento, mes a mes, pela mesma conta que
    # criou o parcelamento (`_somar_meses`). Copiar a data faria as 63 parcelas
    # restantes vencerem todas no mesmo dia.
    aplicar_nas_proximas: bool = Field(
        False,
        description=(
            "Repete a alteração nas parcelas seguintes que ainda estão em "
            "aberto. Ignorado em conta não parcelada"
        ),
    )


# ===========================================================================
# BAIXA
# ===========================================================================

class ContaPagarBaixa(BaseModel):
    """O pagamento de uma conta: é isto que gera a linha no livro do dinheiro."""

    # Separado do `valor` da conta porque os dois divergem na vida real: juros
    # por atraso, desconto por antecipação, ou a conta de luz que veio diferente
    # do previsto. Omitir usa o valor da conta, que é o caso comum.
    valor_pago: Optional[int] = Field(
        None, gt=0, description="Quanto saiu de fato. Omitir usa o valor da conta"
    )
    # Também data pura: quem paga no fim do dia não quer ver a baixa cair no dia
    # seguinte por causa de fuso.
    pago_em: Optional[date] = Field(
        None, description="Dia do pagamento. Omitir usa hoje"
    )
    conta_bancaria_id: Optional[int] = Field(
        None, description="De onde o dinheiro saiu"
    )
    forma_pagamento_id: Optional[int] = Field(
        None, description="Como foi paga (PIX, dinheiro, transferência)"
    )
    observacao: Optional[str] = Field(
        None, description="Anotação sobre este pagamento"
    )


class ContaPagarEstorno(BaseModel):
    """Desfaz uma baixa lançada errado.

    NÃO apaga a linha do livro: gera um movimento CONTRÁRIO, com a data de HOJE,
    e devolve a conta para PENDENTE. Lançar o estorno na data original mexeria
    num turno de caixa já fechado, e a quebra de caixa gravada passaria a
    discordar da recalculada.
    """

    motivo: str = Field(
        ..., min_length=3,
        description="Por que está sendo estornado. Obrigatório: é o que a auditoria lê",
    )


# ===========================================================================
# LEITURA
# ===========================================================================

class ContaPagarRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    descricao: str
    valor: int
    vencimento: date
    status: str

    plano_conta_id: Optional[int] = None
    plano_conta_nome: Optional[str] = None
    fornecedor_id: Optional[int] = None
    fornecedor_nome: Optional[str] = None

    valor_pago: Optional[int] = None
    pago_em: Optional[datetime] = None
    conta_bancaria_id: Optional[int] = None
    conta_bancaria_nome: Optional[str] = None
    forma_pagamento_id: Optional[int] = None

    recorrente: bool
    parcelamento_id: Optional[int] = None
    parcela_numero: Optional[int] = Field(None, description="3, em '3 de 10'")
    parcela_total: Optional[int] = Field(None, description="10, em '3 de 10'")
    observacao: Optional[str] = None
    criado_em: datetime

    # Derivado, não guardado: "vencida" muda sozinha com a passagem do dia, e
    # uma coluna precisaria de alguém rodando para acertá-la todo dia à meia-noite.
    vencida: bool = Field(
        False, description="PENDENTE e com vencimento anterior a hoje"
    )
    dias_para_vencer: Optional[int] = Field(
        None, description="Negativo quando já venceu. NULL se a conta não está pendente"
    )


class ContaPagarListagem(BaseModel):
    """Lista com os totais do filtro aplicado.

    Os totais vêm do SERVIDOR e não da soma da página: com paginação, somar no
    frontend daria o total da página e não o do período — e a diferença só
    apareceria quando a loja tivesse contas o bastante para paginar.
    """

    itens: List[ContaPagarRead]
    total_itens: int
    total_pendente: int = Field(..., description="Soma dos valores PENDENTES (centavos)")
    total_pago: int = Field(..., description="Soma do que foi PAGO (centavos)")
    total_vencido: int = Field(..., description="Soma dos PENDENTES já vencidos (centavos)")


class HistoricoFinanceiroRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campo: str
    valor_antigo: Optional[str] = None
    valor_novo: Optional[str] = None
    funcionario_nome: Optional[str] = None
    criado_em: datetime
