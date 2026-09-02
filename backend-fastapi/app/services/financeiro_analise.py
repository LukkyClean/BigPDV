# ---------------------------------------------------------------------------
# ARQUIVO: services/financeiro_analise.py
# DESCRIÇÃO: A leitura de DIREÇÃO do módulo financeiro — série mensal, alertas
#            de tendência e projeção de 12 meses. A tela de Análise.
# ---------------------------------------------------------------------------
"""
O resto do módulo responde "como está agora"; este arquivo responde "para onde
está indo". É o papel que o dono pagaria a um consultor para cumprir.

POR QUE É UM ARQUIVO À PARTE, e não mais uma seção de `services/financeiro.py`:
o serviço passou de 94 KB e o PyArmor (licença trial) recusou ofuscar acima de
~90 KB, quebrando a geração do sidecar. O corte podia ter sido em qualquer
lugar; foi aqui porque este bloco é o único que não tem uma linha de
acoplamento com o resto -- ele lê CRUD e devolve schema, e ninguém do outro
lado chama nada daqui além de `alertas_de_tendencia`.

Ou seja: o limite da ferramenta obrigou um corte que já devia ter sido feito
por tamanho. O arquivo de origem tinha 2.298 linhas.

AS TRÊS REGRAS QUE ATRAVESSAM TUDO AQUI:

  MÊS FECHADO. O mês corrente não entra em série, média nem projeção — comparar
  oito dias com um mês inteiro acusaria queda todo início de mês.

  PORTÃO DE HISTÓRICO. Cada leitura declara quantos meses fechados exige, e
  abaixo disso não sai torta: não sai. Dois pontos fazem qualquer reta.

  RETA, NÃO TENDÊNCIA. A projeção repete a média e NÃO extrapola inclinação. Com
  seis pontos, uma regressão prometeria uma data de falência que o dado não
  sustenta.
"""

from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.tempo import fim_do_dia_utc, hoje_local, inicio_do_dia_utc
from app.db.crud import dashboard as dashboard_crud
from app.db.crud import financeiro as financeiro_crud
from app.services import custo_mercadoria
from app.schemas.financeiro import (
    AlertaFinanceiro,
    Projecao,
    ProjecaoMes,
    Serie,
    SerieMes,
    SerieOrigem,
)


# ---------------------------------------------------------------------------
# LIMIARES DE TENDÊNCIA
#
# Alerta de tendência erra mais que alerta de estado: "vencido" é fato, "caindo"
# é leitura. Por isso todos os números abaixo são folgados de propósito -- um
# limiar apertado dispara com o sobe-desce normal de loja pequena, e um painel
# que grita todo mês deixa de ser lido.
# ---------------------------------------------------------------------------

MESES_DE_QUEDA_PARA_ALERTAR = 3      # queda em fila, não um mês ruim
QUEDA_GRAVE_ACUMULADA = 0.30         # 30% do primeiro mês da fila
QUEDA_DE_ORIGEM = 0.30               # uma perna encolhendo contra a média
FATIA_DE_DEPENDENCIA = 0.80          # uma origem virou o negócio inteiro
CUSTO_CRESCE_VEZES_MAIS = 2.0        # despesa subindo ao dobro da receita
PRAZO_LENTO_ACIMA_DE = 1.5           # 50% mais devagar que a média


# ===========================================================================
# SÉRIE MENSAL (Análise — Fase 1)
# ===========================================================================

# Rótulo de cada origem de receita.
#
# Fica AQUI, e não no Vue, porque é vocabulário de negócio: "Serviços" é o que o
# menu já chama, e um segmento que amanhã chamar de outra coisa muda por
# declaração. A tela recebe o rótulo pronto e não conhece nenhuma origem.
ROTULO_ORIGEM_RECEITA = {
    "VENDA": "Vendas",
    "ORDEM_SERVICO": "Serviços",
}


def _primeiro_dia(referencia: date) -> date:
    return referencia.replace(day=1)


def _mes_anterior(referencia: date) -> date:
    """Primeiro dia do mês anterior ao de `referencia`."""
    primeiro = _primeiro_dia(referencia)
    return _primeiro_dia(primeiro - timedelta(days=1))


def _ultimo_dia_do_mes(primeiro: date) -> date:
    return _primeiro_dia(primeiro + timedelta(days=32)) - timedelta(days=1)


def get_serie(db: Session, empresa_id: int, meses: int = 12) -> Serie:
    """Receita por origem, despesa e caixa, mês a mês — só de meses FECHADOS.

    A RECEITA SAI DA MESMA FONTE DA VISÃO GERAL (`dashboard_crud`). Se a série
    calculasse por conta própria, existiriam dois números para o mesmo mês, e
    ninguém confia num módulo financeiro depois de ver isso uma vez.

    UMA RODADA DE CONSULTAS POR MÊS, e é uma escolha: dá três consultas
    agregadas por mês (36 numa janela de doze), todas triviais em SQLite. A
    alternativa -- um GROUP BY por mês em cada métrica -- seria mais rápida e
    reescreveria as regras de recorte de venda e de OS aqui dentro, que é
    justamente o que abriria a porta para dois números diferentes.

    O MÊS CORRENTE NÃO ENTRA. Comparar oito dias com um mês inteiro acusaria
    queda todo início de mês.
    """
    hoje = hoje_local()

    # Origens possíveis para ESTA loja. Sem OS no segmento, a série nasce com
    # uma perna -- não com uma perna vazia.
    from app.core.segmentos import segmento_usa_ordem_servico
    from app.db.models.empresa import Empresa

    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    usa_os = segmento_usa_ordem_servico(getattr(empresa, "segmento", None))

    linhas: List[SerieMes] = []
    cursor = _mes_anterior(hoje)  # o último mês FECHADO
    for _ in range(meses):
        inicio, fim = cursor, _ultimo_dia_do_mes(cursor)
        dt_inicio, dt_fim = inicio_do_dia_utc(inicio), fim_do_dia_utc(fim)

        stats = dashboard_crud.get_stats_agregados(db, dt_inicio, dt_fim, empresa_id)
        por_origem = {"VENDA": int(stats.vendas_total or 0)}
        if usa_os:
            por_origem["ORDEM_SERVICO"] = int(stats.os_soma or 0)

        despesas = financeiro_crud.total_despesas_pagas(db, empresa_id, dt_inicio, dt_fim)
        # O CMV entra aqui pela MESMA razão de entrar na Visão Geral, e com a
        # mesma função: se a série somasse diferente do card, o dono veria queda
        # de resultado onde não houve -- só porque duas telas discordam.
        custo, _sem_registro = custo_mercadoria.calcular_cmv(
            db, dt_inicio, dt_fim, empresa_id
        )
        caixa = financeiro_crud.total_entrou_no_caixa(db, empresa_id, dt_inicio, dt_fim)
        prazo = financeiro_crud.prazo_medio_recebimento(db, empresa_id, dt_inicio, dt_fim)
        receita = sum(por_origem.values())

        linhas.append(
            SerieMes(
                mes=inicio.strftime("%Y-%m"),
                inicio=inicio,
                fim=fim,
                receita=receita,
                origens=[
                    SerieOrigem(
                        chave=chave,
                        rotulo=ROTULO_ORIGEM_RECEITA.get(chave, chave),
                        total=total,
                    )
                    for chave, total in por_origem.items()
                ],
                despesas_pagas=despesas,
                custo_mercadorias=custo,
                resultado=receita - custo - despesas,
                entrou_caixa=caixa,
                prazo_medio_recebimento=prazo,
            )
        )
        cursor = _mes_anterior(cursor)

    linhas.reverse()  # do mais antigo para o mais novo, como se lê um gráfico

    # ORIGEM ZERADA NA JANELA INTEIRA SAI. Uma linha reta no zero ocupa legenda,
    # cor e espaço para não dizer nada -- e numa loja que só vende, "Serviços"
    # seria exatamente isso.
    zeradas = {
        chave
        for chave in ROTULO_ORIGEM_RECEITA
        if all(
            o.total == 0 for linha in linhas for o in linha.origens if o.chave == chave
        )
    }
    if zeradas:
        for linha in linhas:
            linha.origens = [o for o in linha.origens if o.chave not in zeradas]

    # HISTÓRICO É DESDE O PRIMEIRO MÊS COM MOVIMENTO, e conta o mês vazio do
    # meio: loja que parou em julho não deixou de existir em julho.
    com_movimento = [
        linha for linha in linhas if linha.receita or linha.despesas_pagas
    ]
    primeiro = com_movimento[0] if com_movimento else None
    disponiveis = 0
    if primeiro:
        disponiveis = sum(1 for linha in linhas if linha.mes >= primeiro.mes)

    return Serie(
        meses_disponiveis=disponiveis,
        primeiro_mes=primeiro.mes if primeiro else None,
        meses=linhas,
    )


# ===========================================================================
# PROJEÇÃO DE 12 MESES (Análise — Fase 4)
# ===========================================================================

# Meses fechados para a projeção existir. Abaixo disso ela não sai torta: não
# sai. Três pontos desenham qualquer coisa.
PORTAO_PROJECAO = 6

# Quantos meses entram na média. Três é o bastante para amortecer um mês fora
# da curva sem esconder uma mudança recente de patamar.
MESES_NA_MEDIA = 3

MARGEM_MINIMA = 0.10   # nem a loja mais regular do mundo acerta na mosca
MARGEM_MAXIMA = 0.50   # acima disso a faixa é tão larga que não informa nada
CASTIGO_HISTORICO_CURTO = 1.3  # menos de um ano: alarga a faixa


def get_projecao(db: Session, empresa_id: int) -> Projecao:
    """Onde o ritmo dos últimos meses leva a loja em doze meses.

    RETA, E NÃO TENDÊNCIA -- a decisão mais importante desta função. A projeção
    repete a média; ela NÃO extrapola a inclinação dos últimos meses. Com seis
    pontos, uma reta de regressão erra feio, e a tela passaria a prometer uma
    data ("em março você quebra") que o dado não sustenta. Quando a média já é
    negativa, isso é dito -- e aí é uma afirmação sobre o presente.
    """
    serie = get_serie(db, empresa_id, meses=12)
    fechados = [m for m in serie.meses if m.mes >= (serie.primeiro_mes or "9999-99")]

    if serie.meses_disponiveis < PORTAO_PROJECAO or not fechados:
        return Projecao(
            disponivel=False,
            meses_faltando=max(0, PORTAO_PROJECAO - serie.meses_disponiveis),
            base_meses=serie.meses_disponiveis,
        )

    base = fechados[-MESES_NA_MEDIA:]
    receita = int(_media(m.receita for m in base))
    despesa = int(_media(m.despesas_pagas for m in base))
    resultado = receita - despesa

    # A MARGEM SAI DO PRÓPRIO HISTÓRICO: coeficiente de variação da receita.
    # Loja regular ganha faixa estreita; loja de altos e baixos ganha faixa
    # larga -- e é exatamente ela que precisa saber que sabe menos.
    receitas = [m.receita for m in fechados]
    media_geral = _media(receitas)
    if media_geral:
        desvio = (_media((r - media_geral) ** 2 for r in receitas)) ** 0.5
        margem = desvio / media_geral
    else:
        margem = MARGEM_MAXIMA
    if serie.meses_disponiveis < 12:
        margem *= CASTIGO_HISTORICO_CURTO
    margem = min(MARGEM_MAXIMA, max(MARGEM_MINIMA, margem))

    hoje = hoje_local()
    meses: List[ProjecaoMes] = []
    acumulado = 0
    cursor = _primeiro_dia(hoje)
    for _ in range(12):
        cursor = _primeiro_dia(_ultimo_dia_do_mes(cursor) + timedelta(days=1))
        acumulado += resultado
        meses.append(
            ProjecaoMes(
                mes=cursor.strftime("%Y-%m"),
                receita=receita,
                despesa=despesa,
                resultado=resultado,
                acumulado=acumulado,
            )
        )

    # Os dois cenários, explicáveis em uma frase: vender `margem` a menos
    # gastando `margem` a mais, e o contrário.
    piso = int((receita * (1 - margem) - despesa * (1 + margem)) * 12)
    teto = int((receita * (1 + margem) - despesa * (1 - margem)) * 12)

    return Projecao(
        disponivel=True,
        meses_faltando=0,
        base_meses=len(base),
        receita_mensal=receita,
        despesa_mensal=despesa,
        resultado_mensal=resultado,
        receita_12_meses=receita * 12,
        despesa_12_meses=despesa * 12,
        resultado_12_meses=resultado * 12,
        margem=round(margem, 2),
        piso_12_meses=piso,
        teto_12_meses=teto,
        meses=meses,
    )


def _media(valores) -> float:
    valores = list(valores)
    return sum(valores) / len(valores) if valores else 0.0


def alertas_de_tendencia(
    db: Session, empresa_id: int, material: int
) -> List[AlertaFinanceiro]:
    """O que a série mostra e a fotografia do mês não mostra.

    Todos os portões são cobrados aqui: sem meses fechados suficientes o alerta
    simplesmente não nasce. Dizer "sua receita está caindo" com dois meses de
    histórico seria transformar acaso em diagnóstico.
    """
    serie = get_serie(db, empresa_id, meses=6)
    fechados = [m for m in serie.meses if m.mes >= (serie.primeiro_mes or "9999-99")]
    alertas: List[AlertaFinanceiro] = []
    if not fechados:
        return alertas

    ultimo = fechados[-1]

    # --- receita caindo em fila (4 meses de histórico) ---
    if len(fechados) >= MESES_DE_QUEDA_PARA_ALERTAR + 1:
        janela = fechados[-(MESES_DE_QUEDA_PARA_ALERTAR + 1):]
        caindo = all(
            janela[i].receita < janela[i - 1].receita for i in range(1, len(janela))
        )
        if caindo and janela[0].receita:
            queda = (janela[0].receita - janela[-1].receita) / janela[0].receita
            alertas.append(
                AlertaFinanceiro(
                    codigo="RECEITA_CAINDO",
                    severidade="CRITICO" if queda >= QUEDA_GRAVE_ACUMULADA else "ATENCAO",
                    valor=janela[0].receita - janela[-1].receita,
                    quantidade=MESES_DE_QUEDA_PARA_ALERTAR,
                )
            )

    # --- uma origem encolhendo (4 meses) ---
    if len(fechados) >= 4:
        anteriores = fechados[-4:-1]
        for origem in ultimo.origens:
            media = _media(
                o.total
                for mes in anteriores
                for o in mes.origens
                if o.chave == origem.chave
            )
            if media and (media - origem.total) / media >= QUEDA_DE_ORIGEM:
                alertas.append(
                    AlertaFinanceiro(
                        codigo="ORIGEM_CAINDO",
                        severidade="ATENCAO",
                        valor=int(media) - origem.total,
                        quantidade=round(((media - origem.total) / media) * 100),
                        rotulo=origem.rotulo,
                    )
                )

    # --- dependência de uma perna só (3 meses) ---
    if len(fechados) >= 3 and ultimo.receita and len(ultimo.origens) > 1:
        maior = max(ultimo.origens, key=lambda o: o.total)
        fatia = maior.total / ultimo.receita
        if fatia >= FATIA_DE_DEPENDENCIA:
            alertas.append(
                AlertaFinanceiro(
                    codigo="DEPENDENCIA_DE_ORIGEM",
                    severidade="ATENCAO",
                    quantidade=round(fatia * 100),
                    rotulo=maior.rotulo,
                )
            )

    # --- custo subindo mais rápido que a receita (4 meses) ---
    if len(fechados) >= 4:
        base, agora = fechados[-4], ultimo
        if base.receita and base.despesas_pagas:
            cresc_receita = (agora.receita - base.receita) / base.receita
            cresc_despesa = (agora.despesas_pagas - base.despesas_pagas) / base.despesas_pagas
            # Só quando a despesa REALMENTE subiu: despesa caindo menos que a
            # receita também passaria na razão, e não é o mesmo problema.
            if (
                cresc_despesa > 0
                and cresc_despesa >= max(cresc_receita, 0) * CUSTO_CRESCE_VEZES_MAIS
                and agora.despesas_pagas - base.despesas_pagas >= material
            ):
                alertas.append(
                    AlertaFinanceiro(
                        codigo="CUSTO_SUBINDO_MAIS",
                        severidade="ATENCAO",
                        valor=agora.despesas_pagas - base.despesas_pagas,
                        quantidade=round(cresc_despesa * 100),
                    )
                )

    # --- o cliente pagando mais devagar (3 meses) ---
    if len(fechados) >= 3 and ultimo.prazo_medio_recebimento:
        anteriores = [
            m.prazo_medio_recebimento
            for m in fechados[-4:-1]
            if m.prazo_medio_recebimento
        ]
        media = _media(anteriores)
        if media and ultimo.prazo_medio_recebimento >= media * PRAZO_LENTO_ACIMA_DE:
            alertas.append(
                AlertaFinanceiro(
                    codigo="RECEBIMENTO_LENTO",
                    severidade="ATENCAO",
                    quantidade=ultimo.prazo_medio_recebimento,
                    valor=round(media),
                )
            )

    return alertas
