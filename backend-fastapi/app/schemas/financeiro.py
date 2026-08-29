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
