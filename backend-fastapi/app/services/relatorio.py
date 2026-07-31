# ---------------------------------------------------------------------------
# ARQUIVO: services/relatorio.py
# DESCRICAO: Regras do modulo de Relatorios. Monta o relatorio de faturamento
#            reusando as agregacoes do dashboard e a serie por dia do crud proprio.
# ---------------------------------------------------------------------------

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.enum import SituacaoEquipamento, MovimentacaoTipo
from app.db.crud import dashboard as dashboard_crud
from app.db.crud import relatorio as relatorio_crud
from app.schemas.relatorio import (
    RelatorioFaturamento,
    FaturamentoDiaItem,
    FormaPagamentoResumo,
    RelatorioRanking,
    RankingFuncionarioItem,
    RelatorioComissao,
    ComissaoFuncionarioItem,
    RelatorioEstoque,
    EstoqueAbcItem,
    EstoqueReposicaoItem,
    EstoqueParadoItem,
    RelatorioOSPerformance,
    OSReparoResumo,
    OSStatusItem,
    OSTecnicoItem,
)


def get_faturamento(db: Session, inicio: date, fim: date, empresa_id: int) -> RelatorioFaturamento:
    """
    Faturamento (vendas + OS finalizadas) no intervalo [inicio, fim]:
    KPIs, serie por dia e formas de pagamento.

    Os KPIs reusam get_stats_agregados (mesma base do dashboard), entao a soma da
    serie por dia bate com o faturamento_total.
    """
    dt_inicio = datetime.combine(inicio, datetime.min.time())
    dt_fim = datetime.combine(fim, datetime.max.time())

    stats = dashboard_crud.get_stats_agregados(db, dt_inicio, dt_fim, empresa_id)
    faturamento_vendas = stats.vendas_total
    faturamento_os = stats.os_soma
    faturamento_total = faturamento_vendas + faturamento_os
    qtd_transacoes = stats.vendas_count + stats.os_finalizadas_count
    ticket_medio = int(faturamento_total / qtd_transacoes) if qtd_transacoes else 0

    # Juros de cartao: sempre fica com a operadora — o que muda e quem pagou.
    # Repassado, ja inflou o faturamento_total (esta dentro do total da venda/OS).
    # Absorvido, nunca entrou no total, mas saiu do caixa da loja.
    # Os dois saem do liquido; so o segundo pode deixar o liquido menor que o bruto
    # sem que nenhuma linha de venda tenha mudado.
    juros = {"CLIENTE": 0, "LOJA": 0}
    for linha in relatorio_crud.get_juros_vendas_por_responsavel(db, dt_inicio, dt_fim, empresa_id):
        juros[linha.responsavel or "CLIENTE"] = juros.get(linha.responsavel or "CLIENTE", 0) + (linha.total or 0)
    for linha in relatorio_crud.get_juros_os_por_responsavel(db, dt_inicio, dt_fim, empresa_id):
        juros[linha.responsavel or "CLIENTE"] = juros.get(linha.responsavel or "CLIENTE", 0) + (linha.total or 0)

    juros_repassado = juros.get("CLIENTE", 0)
    juros_absorvido = juros.get("LOJA", 0)
    faturamento_liquido = faturamento_total - juros_repassado - juros_absorvido

    # CMV: o custo das pecas que sairam, congelado no livro de estoque no dia em
    # que sairam. Saida soma, entrada (estorno) subtrai — assim uma venda
    # cancelada ou uma OS reaberta devolve o custo sozinha, sem ninguem caçar
    # estorno na mao.
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

    # Gasto declarado a mao, nos dois fluxos que nao passam pelo livro de estoque:
    #   OS    -> o servico e lancado sem cadastrar a peca (o normal na oficina)
    #   Venda -> item AVULSO, digitado na hora, fora do catalogo
    # Sem estes dois, a receita entrava e o custo nao, inflando o lucro.
    cmv += relatorio_crud.get_custo_manual_os(db, dt_inicio, dt_fim, empresa_id)
    cmv += relatorio_crud.get_custo_manual_vendas(db, dt_inicio, dt_fim, empresa_id)
    cmv = max(0, cmv)

    lucro_bruto = faturamento_liquido - cmv
    margem_percentual = (lucro_bruto / faturamento_total * 100) if faturamento_total else 0.0

    # Serie por dia — preenche dias sem movimento com zero para o grafico ficar continuo.
    vendas_dia = {
        str(r.dia): (r.total or 0)
        for r in relatorio_crud.get_faturamento_vendas_por_dia(db, dt_inicio, dt_fim, empresa_id)
    }
    os_dia = {
        str(r.dia): (r.total or 0)
        for r in relatorio_crud.get_faturamento_os_por_dia(db, dt_inicio, dt_fim, empresa_id)
    }

    por_dia: list[FaturamentoDiaItem] = []
    dia = inicio
    while dia <= fim:
        chave = dia.isoformat()
        tv = vendas_dia.get(chave, 0)
        to = os_dia.get(chave, 0)
        por_dia.append(
            FaturamentoDiaItem(dia=dia, total_vendas=tv, total_os=to, total_geral=tv + to)
        )
        dia += timedelta(days=1)

    # Formas de pagamento — reusa o crud do dashboard e mescla vendas + OS.
    totais: dict[str, int] = {}
    for r in dashboard_crud.get_formas_pagamento_vendas(db, dt_inicio, dt_fim, empresa_id):
        totais[r.nome] = totais.get(r.nome, 0) + (r.total or 0)
    for r in dashboard_crud.get_formas_pagamento_os(db, dt_inicio, dt_fim, empresa_id):
        totais[r.nome] = totais.get(r.nome, 0) + (r.total or 0)
    formas = [
        FormaPagamentoResumo(nome=nome, valor_total=valor)
        for nome, valor in sorted(totais.items(), key=lambda x: x[1], reverse=True)
    ]

    return RelatorioFaturamento(
        inicio=inicio,
        fim=fim,
        faturamento_total=faturamento_total,
        faturamento_vendas=faturamento_vendas,
        faturamento_os=faturamento_os,
        juros_repassado=juros_repassado,
        juros_absorvido=juros_absorvido,
        faturamento_liquido=faturamento_liquido,
        cmv=cmv,
        lucro_bruto=lucro_bruto,
        margem_percentual=round(margem_percentual, 2),
        saidas_sem_custo=saidas_sem_custo,
        ticket_medio=ticket_medio,
        qtd_vendas=stats.vendas_count,
        qtd_os=stats.os_finalizadas_count,
        por_dia=por_dia,
        formas_pagamento=formas,
    )


def get_ranking(db: Session, inicio: date, fim: date, empresa_id: int) -> RelatorioRanking:
    """Ranking de funcionarios por faturamento (vendas + OS finalizadas) no periodo.

    Só entram funcionarios que faturaram algo (total > 0), ja ordenados desc pelo crud.
    """
    dt_inicio = datetime.combine(inicio, datetime.min.time())
    dt_fim = datetime.combine(fim, datetime.max.time())

    rows = relatorio_crud.get_ranking_faturamento(db, dt_inicio, dt_fim, empresa_id)
    itens: list[RankingFuncionarioItem] = []
    for r in rows:
        vendas = r.vendas_valor or 0
        os = r.os_valor or 0
        total = vendas + os
        if total <= 0:
            continue
        itens.append(
            RankingFuncionarioItem(
                funcionario_id=r.id,
                nome=r.nome,
                faturamento_vendas=vendas,
                faturamento_os=os,
                faturamento_total=total,
                qtd_vendas=r.vendas_qtd or 0,
                qtd_os=r.os_qtd or 0,
            )
        )

    return RelatorioRanking(inicio=inicio, fim=fim, itens=itens)


def get_comissao(db: Session, inicio: date, fim: date, empresa_id: int) -> RelatorioComissao:
    """
    Comissao apurada por funcionario no periodo.

    Base LIQUIDA (Venda.total e OS.valor_total ja sao pos-desconto), só FINALIZADO.
    Taxa e modo resolvidos por cascata funcionario -> cargo (no crud).

    Modo (F3c):
      - 'direto' (padrao; tambem quando o modo vem NULL): comissao = base * taxa.
      - 'meta'  : gatilho — só paga se o faturamento_total atingir a meta; abaixo
                  da meta a comissao é ZERO. Sem meta definida nao ha como travar,
                  entao cai em 'direto' (nao zera ninguem em silencio).
    Taxa em basis points (500 = 5,00% -> divide por 10000).
    """
    dt_inicio = datetime.combine(inicio, datetime.min.time())
    dt_fim = datetime.combine(fim, datetime.max.time())

    rows = relatorio_crud.get_comissao_base(db, dt_inicio, dt_fim, empresa_id)
    itens: list[ComissaoFuncionarioItem] = []
    total_comissao = 0
    for r in rows:
        vendas = r.vendas_valor or 0
        os = r.os_valor or 0
        fat_total = vendas + os
        if fat_total <= 0:
            continue  # só quem faturou entra na apuração

        rate_v = r.rate_venda  # basis points ou None
        rate_s = r.rate_servico
        meta = r.meta
        modo = r.modo or "direto"

        # Gatilho por meta: modo 'meta' COM meta definida trava a comissao ate bater.
        # Sem meta, o gatilho nao tem referencia -> comporta como 'direto'.
        bloqueada_por_meta = modo == "meta" and bool(meta) and fat_total < meta
        comissao_liberada = not bloqueada_por_meta

        if comissao_liberada:
            comissao_vendas = round(vendas * (rate_v or 0) / 10000)
            comissao_servico = round(os * (rate_s or 0) / 10000)
        else:
            comissao_vendas = 0
            comissao_servico = 0
        comissao_total = comissao_vendas + comissao_servico
        total_comissao += comissao_total

        meta_pct = round(fat_total / meta * 100, 1) if meta else None

        itens.append(
            ComissaoFuncionarioItem(
                funcionario_id=r.id,
                nome=r.nome,
                faturamento_vendas=vendas,
                faturamento_os=os,
                faturamento_total=fat_total,
                percentual_venda=rate_v,
                percentual_servico=rate_s,
                comissao_vendas=comissao_vendas,
                comissao_servico=comissao_servico,
                comissao_total=comissao_total,
                meta_mensal=meta,
                meta_atingida_percentual=meta_pct,
                comissao_modo=modo,
                comissao_liberada=comissao_liberada,
            )
        )

    return RelatorioComissao(inicio=inicio, fim=fim, total_comissao=total_comissao, itens=itens)


# ---------------------------------------------------------------------------
# ESTOQUE / CURVA ABC (Fase 4a)
# ---------------------------------------------------------------------------

# Cortes clássicos da Curva ABC sobre o % ACUMULADO de faturamento.
_ABC_CORTE_A = 80.0   # até 80% acumulado -> classe A
_ABC_CORTE_B = 95.0   # de 80% a 95% -> classe B; acima -> classe C


def _classe_abc(acumulado_pct: float) -> str:
    if acumulado_pct <= _ABC_CORTE_A:
        return "A"
    if acumulado_pct <= _ABC_CORTE_B:
        return "B"
    return "C"


def get_estoque(db: Session, inicio: date, fim: date, empresa_id: int) -> RelatorioEstoque:
    """
    Relatório de estoque: Curva ABC (por faturamento no período) + KPIs de valor
    imobilizado (posição ATUAL) + reposição (abaixo do mínimo) + parados (sem venda).

    ABC classifica pelo % ACUMULADO de faturamento: A ≤ 80%, B ≤ 95%, C o resto.
    Só entram produtos que venderam. "Parados" são o complemento: ativos com estoque
    e sem nenhuma venda no período. Valor imobilizado é a foto de agora (independe do
    período) — custo usa o custo médio ponderado e cai para valor_entrada enquanto a
    média não existir; sem nenhum dos dois, conta como 0 (não estima).
    """
    dt_inicio = datetime.combine(inicio, datetime.min.time())
    dt_fim = datetime.combine(fim, datetime.max.time())

    vendas = relatorio_crud.get_vendas_por_produto(db, dt_inicio, dt_fim, empresa_id)
    faturamento_total = sum((r.faturamento or 0) for r in vendas)
    vendidos_ids: set[int] = set()

    curva: list[EstoqueAbcItem] = []
    acumulado = 0
    for r in vendas:
        fat = r.faturamento or 0
        if fat <= 0:
            continue  # sem receita não classifica (evita divisão por zero / ruído)
        vendidos_ids.add(r.produto_id)
        acumulado += fat
        participacao = round(fat / faturamento_total * 100, 2) if faturamento_total else 0.0
        acumulado_pct = round(acumulado / faturamento_total * 100, 2) if faturamento_total else 0.0
        curva.append(
            EstoqueAbcItem(
                produto_id=r.produto_id,
                nome=r.nome,
                sku=r.sku,
                categoria=r.categoria,
                faturamento=fat,
                quantidade=r.quantidade or 0,
                participacao_pct=participacao,
                acumulado_pct=acumulado_pct,
                classe=_classe_abc(acumulado_pct),
            )
        )

    # Posição de estoque (global) -> KPIs, abaixo do mínimo e parados.
    produtos = relatorio_crud.get_produtos_estoque(db)
    valor_custo_total = 0
    valor_venda_total = 0
    abaixo: list[EstoqueReposicaoItem] = []
    parados: list[EstoqueParadoItem] = []

    for p in produtos:
        qtd = p.quantidade or 0
        # Capital imobilizado vale pelo custo contábil, não pelo último preço
        # digitado no cadastro. A média só assume quando existe; até lá o
        # comportamento é o de antes.
        custo = p.custo_medio if p.custo_medio is not None else (p.valor_entrada or 0)
        valor_custo_total += qtd * custo
        valor_venda_total += qtd * (p.valor_varejo or 0)

        # Abaixo do mínimo: zerado, ou com mínimo definido e atingido.
        if qtd == 0 or (p.quantidade_minima is not None and qtd <= p.quantidade_minima):
            abaixo.append(
                EstoqueReposicaoItem(
                    produto_id=p.produto_id,
                    nome=p.nome,
                    sku=p.sku,
                    quantidade=qtd,
                    quantidade_minima=p.quantidade_minima,
                    quantidade_ideal=p.quantidade_ideal,
                )
            )

        # Parado: tem estoque e não vendeu nada no período.
        if qtd > 0 and p.produto_id not in vendidos_ids:
            parados.append(
                EstoqueParadoItem(
                    produto_id=p.produto_id,
                    nome=p.nome,
                    sku=p.sku,
                    quantidade=qtd,
                    valor_custo=qtd * custo,
                )
            )

    # Parados: maior capital imobilizado primeiro (prioriza a decisão do dono).
    parados.sort(key=lambda x: x.valor_custo, reverse=True)

    return RelatorioEstoque(
        inicio=inicio,
        fim=fim,
        valor_custo_total=valor_custo_total,
        valor_venda_total=valor_venda_total,
        skus_ativos=len(produtos),
        itens_abaixo_minimo=len(abaixo),
        itens_parados=len(parados),
        curva_abc=curva,
        abaixo_minimo=abaixo,
        parados=parados,
    )


# ---------------------------------------------------------------------------
# OS-PERFORMANCE (Fase 4b)
# ---------------------------------------------------------------------------

def _duracao_horas(criacao: datetime, finalizacao: datetime) -> float:
    """(finalização - criação) em horas, com piso em 0.

    Hoje as duas são UTC. Mas as OS finalizadas ANTES da correção do fuso têm
    data_finalizacao em horário local (UTC-3), o que dá diferença negativa em
    conclusões rápidas. Clampar em 0 evita média negativa nesses registros
    antigos sem mascarar OS realmente longas.
    """
    segundos = (finalizacao - criacao).total_seconds()
    return max(segundos, 0) / 3600


def get_os_performance(db: Session, inicio: date, fim: date, empresa_id: int) -> RelatorioOSPerformance:
    """
    Desempenho de OS no período: throughput (abertas × finalizadas), tempo médio de
    conclusão, taxa de reparo (desfecho) e desempenho por técnico, mais o snapshot do
    backlog por status atual.

    Finalizadas são ancoradas em data_finalizacao dentro do período; abertas em
    data_criacao. Tempo médio usa _duracao_horas (piso 0). Por técnico só entra OS
    com funcionário atribuído.
    """
    dt_inicio = datetime.combine(inicio, datetime.min.time())
    dt_fim = datetime.combine(fim, datetime.max.time())

    rows = relatorio_crud.get_os_finalizadas_periodo(db, dt_inicio, dt_fim, empresa_id)
    finalizadas = len(rows)
    faturamento_total = sum((r.valor_total or 0) for r in rows)

    # Tempo médio geral + acumuladores por técnico e desfecho.
    duracoes: list[float] = []
    reparado = sem_reparo = condenado = nao_informado = 0
    tecnicos: dict[int, dict] = {}

    for r in rows:
        if r.data_criacao and r.data_finalizacao:
            dur = _duracao_horas(r.data_criacao, r.data_finalizacao)
            duracoes.append(dur)
        else:
            dur = None

        situ = r.situacao_equipamento
        if situ == SituacaoEquipamento.REPARADO:
            reparado += 1
        elif situ == SituacaoEquipamento.SEM_REPARO:
            sem_reparo += 1
        elif situ == SituacaoEquipamento.CONDENADO:
            condenado += 1
        else:
            nao_informado += 1

        if r.funcionario_id is not None:
            t = tecnicos.setdefault(
                r.funcionario_id,
                {"nome": r.funcionario_nome or "—", "qtd": 0, "faturamento": 0, "duracoes": []},
            )
            t["qtd"] += 1
            t["faturamento"] += r.valor_total or 0
            if dur is not None:
                t["duracoes"].append(dur)

    tempo_medio = round(sum(duracoes) / len(duracoes), 1) if duracoes else None
    taxa_reparo = round(reparado / finalizadas * 100, 1) if finalizadas else 0.0

    por_tecnico = [
        OSTecnicoItem(
            funcionario_id=fid,
            nome=t["nome"],
            finalizadas=t["qtd"],
            tempo_medio_horas=round(sum(t["duracoes"]) / len(t["duracoes"]), 1) if t["duracoes"] else None,
            faturamento=t["faturamento"],
        )
        for fid, t in tecnicos.items()
    ]
    por_tecnico.sort(key=lambda x: x.finalizadas, reverse=True)

    abertas = relatorio_crud.get_os_abertas_count_periodo(db, dt_inicio, dt_fim, empresa_id)

    por_status = [
        OSStatusItem(status=r.status.value if hasattr(r.status, "value") else str(r.status), quantidade=r.quantidade)
        for r in relatorio_crud.get_os_por_status(db, empresa_id)
    ]

    return RelatorioOSPerformance(
        inicio=inicio,
        fim=fim,
        abertas=abertas,
        finalizadas=finalizadas,
        tempo_medio_horas=tempo_medio,
        faturamento_total=faturamento_total,
        reparo=OSReparoResumo(
            reparado=reparado,
            sem_reparo=sem_reparo,
            condenado=condenado,
            nao_informado=nao_informado,
            taxa_reparo_pct=taxa_reparo,
        ),
        por_status=por_status,
        por_tecnico=por_tecnico,
    )
