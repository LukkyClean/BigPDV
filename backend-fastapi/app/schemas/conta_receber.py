# ---------------------------------------------------------------------------
# ARQUIVO: schemas/conta_receber.py
# DESCRIÇÃO: Schemas Pydantic das contas a receber — cadastro, baixa e leitura.
# ---------------------------------------------------------------------------

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.enum import JurosDestino


# ===========================================================================
# CADASTRO MANUAL
#
# A maioria das contas a receber NASCE SOZINHA, do fecho da venda ou da OS.
# Este cadastro existe para o que não passou pelo sistema: o cliente antigo que
# já devia antes do módulo existir, ou um acerto combinado fora do balcão.
# ===========================================================================

class ContaReceberCreate(BaseModel):
    descricao: str = Field(..., min_length=1, max_length=255, description="Ex.: 'Acerto de agosto'")
    valor: int = Field(..., gt=0, description="Valor a receber, líquido (centavos)")
    vencimento: date = Field(..., description="Quando o dinheiro entra")
    cliente_id: Optional[int] = Field(None, description="Quem deve, quando identificado")
    taxa: int = Field(
        0, ge=0,
        description="Retido pela operadora (centavos). Digitado à mão, do papel de taxas",
    )
    observacao: Optional[str] = None


class ContaReceberUpdate(BaseModel):
    """Alteração parcial. Campo ausente = não mexe.

    Mudar valor ou vencimento vira linha em `historico_financeiro`: renegociar
    prazo com o cliente é legítimo, mas precisa deixar rastro de quem renegociou.
    """

    descricao: Optional[str] = Field(None, min_length=1, max_length=255)
    valor: Optional[int] = Field(None, gt=0)
    vencimento: Optional[date] = None
    cliente_id: Optional[int] = None
    taxa: Optional[int] = Field(None, ge=0)
    observacao: Optional[str] = None


# ===========================================================================
# BAIXA
# ===========================================================================

class ContaReceberBaixa(BaseModel):
    """O recebimento: é isto que gera a ENTRADA no livro do dinheiro."""

    # Separado do `valor` porque os dois divergem: o cliente que devia R$ 100
    # trouxe R$ 90 e ficou de trazer o resto, ou pagou com juros de atraso.
    valor_recebido: Optional[int] = Field(
        None, gt=0,
        description="TOTAL que entrou, juros incluso. Omitir usa valor + juros",
    )
    # Separado do total porque juros de mora é RECEITA FINANCEIRA, não venda:
    # embutido no principal, inflaria o faturamento do mês com dinheiro que não
    # veio de mercadoria nem de serviço.
    juros: int = Field(0, ge=0, description="Juros cobrados do cliente (centavos)")
    juros_destino: JurosDestino = Field(
        JurosDestino.LOJA,
        description=(
            "LOJA = multa por atraso, entra no caixa. OPERADORA = juros da "
            "maquininha, o cliente paga mas a loja NÃO recebe"
        ),
    )
    recebido_em: Optional[date] = Field(
        None, description="Dia do recebimento. Omitir usa hoje"
    )
    conta_bancaria_id: Optional[int] = Field(None, description="Onde o dinheiro caiu")
    forma_pagamento_id: Optional[int] = Field(
        None, description="Como o cliente quitou"
    )
    observacao: Optional[str] = None


class ContaReceberEstorno(BaseModel):
    """Desfaz um recebimento lançado errado.

    Como no contas a pagar: gera um movimento CONTRÁRIO com a data de HOJE e
    devolve a conta para PENDENTE. Nada é apagado do livro.
    """

    motivo: str = Field(
        ..., min_length=3,
        description="Por que está sendo estornado. É o que a auditoria lê",
    )


# ===========================================================================
# LEITURA
# ===========================================================================

class ContaReceberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    descricao: str
    valor: int
    taxa: int
    juros: int
    juros_destino: str
    vencimento: date
    status: str

    cliente_id: Optional[int] = None
    cliente_nome: Optional[str] = None

    valor_recebido: Optional[int] = None
    recebido_em: Optional[datetime] = None
    conta_bancaria_id: Optional[int] = None
    conta_bancaria_nome: Optional[str] = None
    forma_pagamento_id: Optional[int] = None

    # De onde veio. A tela usa para dizer "nasceu da venda 42" e para não
    # oferecer edição livre do que é reflexo de um documento fechado.
    venda_pagamento_id: Optional[int] = None
    ordem_servico_pagamento_id: Optional[int] = None
    automatica: bool = Field(
        False, description="Nasceu do fecho de uma venda ou OS, não foi lançada à mão"
    )

    observacao: Optional[str] = None
    criado_em: datetime

    # Derivados na leitura, nunca guardados — ver a nota gêmea em conta_pagar.
    vencida: bool = Field(False, description="PENDENTE e com vencimento anterior a hoje")
    dias_para_vencer: Optional[int] = Field(
        None, description="Negativo quando já venceu. NULL se não está pendente"
    )


class ContaReceberListagem(BaseModel):
    """Lista com os totais do filtro aplicado, calculados no SERVIDOR."""

    itens: List[ContaReceberRead]
    total_itens: int
    total_pendente: int = Field(..., description="Soma do que ainda não entrou (centavos)")
    total_recebido: int = Field(..., description="Soma do que entrou (centavos)")
    total_vencido: int = Field(..., description="Pendente já vencido (centavos)")
