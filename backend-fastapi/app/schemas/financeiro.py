# ---------------------------------------------------------------------------
# ARQUIVO: schemas/financeiro.py
# DESCRIÇÃO: Schemas do resumo do módulo financeiro (a Visão Geral).
# ---------------------------------------------------------------------------

from datetime import date
from typing import List

from pydantic import BaseModel, Field

from app.schemas.conta_pagar import ContaPagarRead


class DespesaPorCategoria(BaseModel):
    """Quanto saiu em cada categoria, no período."""

    plano_conta_id: int | None = Field(None, description="NULL agrupa as contas sem categoria")
    nome: str = Field(..., description="Nome da categoria, ou 'Sem categoria'")
    total: int = Field(..., description="Soma do que foi PAGO na categoria (centavos)")


class ResumoFinanceiro(BaseModel):
    """O resultado do mês, em regime de CAIXA.

    NÃO é DRE, e o nome importa: DRE é regime de competência, e um contador que
    comparasse os dois números acharia diferença legítima e abriria chamado. Aqui
    a pergunta é a que o dono de loja faz — "entrou quanto, saiu quanto, sobrou
    quanto" — e a resposta considera o dinheiro que ANDOU no período.

    O custo da mercadoria NÃO é subtraído à parte, de propósito: a compra do
    fornecedor entra como conta a pagar e já está em `despesas_pagas`. Descontar
    o CMV por cima contaria a mesma mercadoria duas vezes. Lucro por regime de
    competência é assunto do módulo de Relatórios, que tem o custo congelado no
    livro de estoque.
    """

    periodo_inicio: date
    periodo_fim: date

    faturamento: int = Field(
        ..., description="Vendas + OS finalizadas no período (centavos)"
    )
    despesas_pagas: int = Field(
        ..., description="O que saiu de fato no período (centavos)"
    )
    resultado: int = Field(
        ..., description="faturamento - despesas_pagas (centavos). Pode ser negativo"
    )

    a_pagar_pendente: int = Field(
        ...,
        description=(
            "Em aberto com vencimento ATÉ o fim do período (centavos). Inclui o "
            "atrasado de meses anteriores, que continua devido; exclui o que só "
            "vence depois — senão o card somaria outubro na visão de agosto."
        ),
    )
    a_pagar_vencido: int = Field(
        ..., description="Parte do pendente que já passou do vencimento (centavos)"
    )

    a_receber_pendente: int = Field(
        ...,
        description=(
            "TODA cobrança em aberto, de qualquer vencimento (centavos) — a única "
            "coisa nesta tela que não respeita o mês visto, e de propósito. O teto "
            "do a pagar existe por causa da recorrência, que não existe aqui; e "
            "fiado quase sempre vence no mês seguinte, então com teto o card "
            "mostraria zero justamente quando importa (a Visão Geral nem deixa "
            "avançar de mês). É dinheiro já contado em `faturamento` que ainda não "
            "passou pelo caixa — por isso não entra no resultado."
        ),
    )
    a_receber_vencido: int = Field(
        ..., description="Parte do a receber que já passou do vencimento (centavos)"
    )

    despesas_por_categoria: List[DespesaPorCategoria] = Field(
        default_factory=list, description="Onde o dinheiro foi, no período"
    )
    proximas_a_vencer: List[ContaPagarRead] = Field(
        default_factory=list,
        description="Contas pendentes vencendo nos próximos dias, das mais urgentes",
    )


# ===========================================================================
# FLUXO DE CAIXA (Onda 3)
# ===========================================================================

class FluxoLancamento(BaseModel):
    """Um documento previsto para um dia. Não é movimento: nada disso andou."""

    conta_id: int
    tipo: str = Field(..., description="ENTRADA (a receber) ou SAIDA (a pagar)")
    descricao: str
    valor: int = Field(..., description="Sempre positivo (centavos); o sinal é o `tipo`")


class FluxoDia(BaseModel):
    """Um dia com movimento previsto.

    Dias vazios NÃO entram na lista: sessenta linhas de zero escondem as cinco
    que importam. Quem desenha a régua do tempo é a tela.
    """

    data: date
    entradas: int
    saidas: int
    saldo: int = Field(..., description="Saldo previsto ao FIM do dia (centavos)")
    lancamentos: List[FluxoLancamento] = Field(default_factory=list)


class FluxoCaixa(BaseModel):
    """A projeção dos próximos N dias, a partir do saldo DECLARADO pelo dono.

    NÃO é o extrato do que aconteceu — é o que está agendado para acontecer.
    Cada linha nasce de um documento em aberto (conta a pagar ou a receber) na
    data do vencimento, e a régua acumula o saldo dia a dia.

    O saldo de partida é declarado, nunca calculado: ver o comentário em
    `ContaBancaria.saldo_informado`. Enquanto ninguém declarar, a projeção sai
    com `saldo_declarado=False` e a tela pede o número antes de desenhar — uma
    linha que parte de zero fingindo ser saldo é pior que nenhuma linha.

    O ATRASADO fica FORA da régua, num balde só dele. Conta vencida não tem
    data futura para ocupar, e empurrá-la para hoje inventaria um dia de aperto
    que talvez nunca aconteça (o fiado atrasado pode nunca chegar). Ela aparece
    como aviso, para o dono decidir o que fazer com ela.
    """

    inicio: date
    fim: date
    dias: int

    saldo_inicial: int = Field(
        ..., description="Soma do saldo declarado nas contas ATIVAS (centavos)"
    )
    saldo_declarado: bool = Field(
        ..., description="Se alguma conta já teve saldo informado alguma vez"
    )
    saldo_informado_em: date | None = Field(
        None,
        description=(
            "A data MAIS ANTIGA entre as contas com saldo declarado — é a que "
            "envelhece o número, e por isso é ela que a tela mostra"
        ),
    )

    total_entradas: int
    total_saidas: int
    saldo_final: int = Field(..., description="Saldo previsto no último dia do período")

    primeiro_dia_negativo: date | None = Field(
        None, description="O dia em que o dinheiro acaba, se acabar no período"
    )
    menor_saldo: int = Field(..., description="O fundo do poço previsto (centavos)")
    menor_saldo_em: date | None = None

    atrasado_a_receber: int = Field(
        ..., description="Vencido e não recebido, fora da régua (centavos)"
    )
    atrasado_a_pagar: int = Field(
        ..., description="Vencido e não pago, fora da régua (centavos)"
    )

    linha: List[FluxoDia] = Field(
        default_factory=list, description="Só os dias com movimento previsto"
    )
