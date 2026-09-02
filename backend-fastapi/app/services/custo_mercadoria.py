# ---------------------------------------------------------------------------
# ARQUIVO: services/custo_mercadoria.py
# DESCRIÇÃO: O CMV — quanto custou, para a loja, aquilo que ela vendeu.
# ---------------------------------------------------------------------------
"""
Uma função só, e num arquivo só, porque DOIS módulos precisam da mesma resposta:
Relatórios (lucro bruto do período) e Financeiro (o lucro da Visão Geral).

Estava dentro de `services/relatorio.py` e saiu de lá quando o Financeiro passou
a descontar o custo. Copiar as quatro somas para o outro módulo era o caminho
curto, e é exatamente o caminho que faz duas telas mostrarem lucros diferentes
para o mesmo mês -- o tipo de divergência que o dono descobre na frente do
cliente e que ninguém consegue explicar depois.
"""

from datetime import datetime
from typing import Tuple

from sqlalchemy.orm import Session

from app.core.enum import MovimentacaoTipo
from app.db.crud import relatorio as relatorio_crud


def calcular_cmv(
    db: Session, dt_inicio: datetime, dt_fim: datetime, empresa_id: int
) -> Tuple[int, int]:
    """(cmv, saidas_sem_custo) do período. Datas já em UTC.

    QUATRO PARCELAS, e cada uma existe porque sem ela o lucro saía maior do que
    foi:

      1. peça de venda   custo CONGELADO no livro de estoque, no dia da saída
      2. peça de OS      idem
      3. custo manual da OS   o "Custo para a loja" digitado no item -- na
                              oficina o normal é lançar só o serviço e nunca
                              cadastrar a peça, então esse gasto não passa pelo
                              livro de estoque e precisa de um lugar próprio
      4. custo do avulso da venda   item digitado na hora, fora do catálogo

    SAÍDA SOMA, ENTRADA SUBTRAI (1 e 2). É o que faz uma venda cancelada ou uma
    OS reaberta devolverem o custo sozinhas, sem ninguém caçar estorno na mão.

    `saidas_sem_custo` conta as saídas cujo custo era desconhecido: é a medida
    da confiança do número, e a tela avisa quando ela não é zero. Um CMV
    subestimado em silêncio vira lucro inventado.

    O piso em zero existe para o período que só tem estorno (mais entrada que
    saída): CMV negativo viraria lucro do nada.
    """
    cmv = 0
    saidas_sem_custo = 0

    for linhas in (
        relatorio_crud.get_cmv_vendas(db, dt_inicio, dt_fim, empresa_id),
        relatorio_crud.get_cmv_os(db, dt_inicio, dt_fim, empresa_id),
    ):
        for linha in linhas:
            valor = linha.total or 0
            cmv += valor if linha.tipo == MovimentacaoTipo.SAIDA else -valor
            saidas_sem_custo += linha.sem_custo or 0

    cmv += relatorio_crud.get_custo_manual_os(db, dt_inicio, dt_fim, empresa_id)
    cmv += relatorio_crud.get_custo_manual_vendas(db, dt_inicio, dt_fim, empresa_id)

    return max(0, cmv), saidas_sem_custo
