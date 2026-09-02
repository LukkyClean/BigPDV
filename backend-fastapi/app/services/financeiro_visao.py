# ---------------------------------------------------------------------------
# ARQUIVO: services/financeiro_visao.py
# DESCRIÇÃO: As três leituras do módulo — resumo do mês, fluxo de caixa e
#            extrato. Nenhuma delas escreve nada.
# ---------------------------------------------------------------------------
"""
O que o dono OLHA: quanto entrou e saiu no mês (com os alertas do painel de
atenção), a projeção do caixa dos próximos dias e o livro do dinheiro linha a
linha.

Os três estão juntos por serem leitura pura: nenhuma função daqui cria, baixa
ou estorna nada. Quem escreve mora em `financeiro.py` (contas a pagar) e em
`financeiro_receber.py`.

Separado em 29/08/2026 pelo mesmo motivo do irmão: o PyArmor da licença trial
recusa ofuscar arquivo acima de ~55 KB, e o original tinha 79 KB.
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from app.core.enum import (
    ContaPagarStatus,
    ContaReceberStatus,
    MovimentacaoFinanceiraOrigem,
    MovimentacaoFinanceiraTipo,
)
from app.core.tempo import agora_utc, fim_do_dia_utc, hoje_local, inicio_do_dia_utc
from app.db.crud import dashboard as dashboard_crud
from app.db.crud import financeiro as financeiro_crud
from app.db.crud import sessao_caixa as caixa_crud
from app.db.models.conta_receber import ContaReceber
from app.helpers.exceptions import BadRequestException, NotFoundException
from app.schemas.conta_receber import ContaReceberBaixa
from app.db.models.conta_bancaria import ContaBancaria
from app.schemas.financeiro import (
    AlertaFinanceiro,
    DespesaPorCategoria,
    Extrato,
    ExtratoLinha,
    FluxoCaixa,
    FluxoDia,
    FluxoLancamento,
    ResumoFinanceiro,
)
from app.services import custo_mercadoria
from app.services import financeiro_analise as analise_service
from app.services.financeiro import (
    _funcionario_do_token,
    _serializar_conta,
)


# ===========================================================================
# SALDO — quanto a loja tem AGORA
# ===========================================================================

class SaldoDasContas:
    """O saldo de hoje, e as duas metades que o formam.

    Guardar as metades separadas não é enfeite de tela: é o que permite o dono
    conferir. "Você declarou R$ 500 no dia 29 e desde então entrou R$ 740 e saiu
    R$ 90" é auditável na hora; "você tem R$ 1.150" só dá para acreditar ou não.
    """

    __slots__ = (
        "saldo", "ancora", "movimentado", "entrou", "saiu", "declarado", "informado_em",
    )

    def __init__(self, saldo, ancora, entrou, saiu, declarado, informado_em):
        self.saldo = saldo
        self.ancora = ancora
        self.entrou = entrou
        self.saiu = saiu
        self.movimentado = entrou - saiu
        self.declarado = declarado
        self.informado_em = informado_em


def saldo_atual_das_contas(db: Session, empresa_id: int) -> SaldoDasContas:
    """Âncora declarada + tudo que o livro moveu depois dela.

    ESTE É O NÚMERO QUE FALTAVA. Até 02/09/2026 o Fluxo de Caixa partia do
    `saldo_informado` puro, e o resultado era o dono vendendo o dia inteiro e
    vendo o saldo parado no mesmo valor -- só mudava quando ele digitava outro à
    mão. É o desenho do "saldo inicial" do Conta Azul e do Omie: declara-se uma
    vez, e daí em diante quem move o saldo são os lançamentos.

    ENQUANTO A LOJA NÃO DECLARAR NADA, não há saldo. Sem ponto de partida, somar
    movimento daria "o quanto mudou", que não é saldo -- e a loja apareceria com
    saldo negativo no primeiro boleto que pagasse.

    MAS BASTA UMA CONTA DECLARADA para todas passarem a contar, e isso foi um
    defeito real: a regra era "conta sem âncora própria não entra, nem com o
    movimento dela", e o resultado era dinheiro sumindo em silêncio. A loja que
    declarou a conta do banco e deixou a gaveta em branco via o dinheiro da OS
    cair na gaveta (que é a conta principal) e desaparecer do saldo -- o Extrato
    mostrava a entrada, o Fluxo de Caixa não se mexia.

    A conta não declarada herda o corte MAIS ANTIGO da loja e parte de zero. É o
    que o dono quis dizer: no dia em que ele declarou o que tinha, o que ele não
    declarou valia zero. Herdar o corte mais antigo (e não o mais recente) é o
    que garante que nenhum movimento fique de fora.

    SÓ CONTAS ATIVAS. Uma conta desativada é dinheiro que a loja não usa mais, e
    somá-la faria toda a projeção partir de um número alto demais.

    O corte de cada conta é o INSTANTE da declaração; nas contas declaradas
    antes de a coluna existir, o fim daquele dia (a convenção conservadora do
    Conta Azul: perde-se o movimento do próprio dia, mas nada é contado duas
    vezes).
    """
    contas = financeiro_crud.listar_contas_bancarias(db, empresa_id, apenas_ativas=True)
    principal = financeiro_crud.get_conta_principal(db, empresa_id)
    principal_id = principal.id if principal else None

    ancora = sum(int(c.saldo_informado or 0) for c in contas)
    datas = [c.saldo_informado_em for c in contas if c.saldo_informado_em]

    def _corte(conta) -> Optional[datetime]:
        if not conta.saldo_informado_em:
            return None
        return conta.saldo_informado_instante or fim_do_dia_utc(conta.saldo_informado_em)

    cortes = [c for c in (_corte(conta) for conta in contas) if c is not None]
    corte_da_loja = min(cortes) if cortes else None

    entrou = saiu = 0
    for conta in contas:
        corte = _corte(conta) or corte_da_loja
        if corte is None:
            continue  # a loja inteira nunca declarou nada
        conta_entrou, conta_saiu = financeiro_crud.entradas_e_saidas_desde(
            db,
            empresa_id,
            conta_id=conta.id,
            desde=corte,
            # As linhas órfãs (antigas, ou de uma conta apagada) caem na
            # principal -- que é para onde os lançamentos novos vão. Jogá-las
            # fora faria o saldo derivado ficar abaixo do real.
            incluir_sem_conta=(conta.id == principal_id),
        )
        entrou += conta_entrou
        saiu += conta_saiu

    return SaldoDasContas(
        saldo=ancora + entrou - saiu,
        ancora=ancora,
        entrou=entrou,
        saiu=saiu,
        declarado=bool(datas),
        # A data MAIS ANTIGA entre as contas: é ela que envelhece o número. Uma
        # loja que atualizou o Nubank hoje e esqueceu a gaveta há um mês tem uma
        # âncora de um mês atrás.
        informado_em=min(datas) if datas else None,
    )


# ===========================================================================
# RESUMO — a Visão Geral
# ===========================================================================

# Uma semana é o ponto em que o retrato do saldo deixa de servir: nele já
# couberam um fim de semana de vendas e as contas do começo do mês.
DIAS_ATE_O_SALDO_ENVELHECER = 7

# ---------------------------------------------------------------------------
# COMO A GRAVIDADE É DECIDIDA
#
# Business Central resolve isto com os "Cues": o indicador muda de cor por
# LIMIAR, e não pelo tipo do dado. Copiamos a ideia e jogamos fora a execução —
# lá o administrador DIGITA os limiares numa tela de setup, e lojista nenhum vai
# abrir uma tela para digitar quanto é muito dinheiro. Aqui o limiar sai do
# porte da própria loja: uma padaria e uma concessionária ganham gravidades
# diferentes sem ninguém configurar nada.
#
# Do Odoo vem a segunda metade: nas atividades dele a cor vem do PRAZO (verde no
# futuro, laranja hoje, vermelho atrasado). Por isso valor e tempo decidem
# juntos — R$ 80 vencidos há três meses é grave, e R$ 80 vencidos ontem não é.
# ---------------------------------------------------------------------------

# 10% do que a loja fatura no mês. Abaixo disso, é ruído para ela.
FRACAO_MATERIAL_DO_FATURAMENTO = 0.10

# Piso, para a loja parada (ou no primeiro mês de uso): sem ele, 10% de zero
# faria QUALQUER centavo vencido virar alerta crítico.
PISO_VALOR_MATERIAL = 20000  # R$ 200,00

# Um mês de atraso é grave por si só, custe o que custar: já passou de
# esquecimento para inadimplência.
DIAS_DE_ATRASO_GRAVE = 30

# Dentro de uma semana já não dá para "resolver depois" — é o horizonte em que
# adiar uma conta ou cobrar um cliente ainda muda o desfecho.
DIAS_ATE_O_APERTO_SER_URGENTE = 7
def _montar_alertas(
    db: Session,
    empresa_id: int,
    *,
    faturamento: int,
    resultado: int,
    a_pagar_vencido: int,
    a_receber_vencido: int,
    categorias: List[DespesaPorCategoria],
    com_projecao: bool,
) -> List[AlertaFinanceiro]:
    """O que precisa de atenção, do mais grave para o menos.

    TODO alerta daqui tem ação possível e uma tela para onde ir. A tentação é
    somar sinal ("faturamento caiu 3%"), e é exatamente assim que um painel de
    alertas morre: quem vê aviso todo dia para de ler, e some junto o aviso que
    importava. Na dúvida, fica de fora.

    Não é IA e não deve ser vendido como tal: são regras explícitas, com limiar
    escrito e defensável -- ver o bloco de constantes acima.
    """
    alertas: List[AlertaFinanceiro] = []
    hoje = hoje_local()

    # O que é "muito dinheiro" PARA ESTA LOJA. É o limiar do Business Central,
    # só que derivado em vez de digitado.
    material = max(
        int(faturamento * FRACAO_MATERIAL_DO_FATURAMENTO), PISO_VALOR_MATERIAL
    )

    def _dias_de_atraso(*, receber: bool) -> int:
        mais_antigo = financeiro_crud.vencimento_mais_antigo_pendente(
            db, empresa_id, hoje=hoje, receber=receber
        )
        return (hoje - mais_antigo).days if mais_antigo else 0

    def _gravidade(valor: int, dias: int) -> str:
        """Valor material OU atraso longo. Qualquer um dos dois basta."""
        if valor >= material or dias >= DIAS_DE_ATRASO_GRAVE:
            return "CRITICO"
        return "ATENCAO"

    # 1. O DINHEIRO VAI ACABAR. O mais grave que o módulo sabe dizer, e o único
    #    que olha para frente. Só existe com FINANCEIRO_PRO (é o Fluxo de Caixa
    #    respondendo) e só faz sentido com saldo declarado -- sem ponto de
    #    partida, "ficar negativo" não significa nada.
    if com_projecao:
        fluxo = get_fluxo_caixa(db, empresa_id, dias=30)
        if fluxo.saldo_declarado and fluxo.primeiro_dia_negativo:
            faltam = (fluxo.primeiro_dia_negativo - hoje).days
            alertas.append(
                AlertaFinanceiro(
                    codigo="CAIXA_NEGATIVO",
                    # Longe ainda dá para resolver sem susto; dentro da semana,
                    # não. A urgência vem do prazo, como nas atividades do Odoo.
                    severidade=(
                        "CRITICO" if faltam <= DIAS_ATE_O_APERTO_SER_URGENTE else "ATENCAO"
                    ),
                    data=fluxo.primeiro_dia_negativo,
                    valor=fluxo.menor_saldo,
                    quantidade=faltam,
                )
            )

    # 2. Dívida vencida: já passou do prazo e continua devida.
    if a_pagar_vencido > 0:
        dias = _dias_de_atraso(receber=False)
        alertas.append(
            AlertaFinanceiro(
                codigo="CONTAS_VENCIDAS",
                severidade=_gravidade(a_pagar_vencido, dias),
                valor=a_pagar_vencido,
                quantidade=dias,
            )
        )

    # 3. Fiado atrasado: dinheiro na rua que já deveria ter voltado.
    if a_receber_vencido > 0:
        dias = _dias_de_atraso(receber=True)
        alertas.append(
            AlertaFinanceiro(
                codigo="FIADO_ATRASADO",
                severidade=_gravidade(a_receber_vencido, dias),
                valor=a_receber_vencido,
                quantidade=dias,
            )
        )

    # 4. O mês fechou no vermelho. Sem link para "resolver" -- a ação é olhar
    #    para onde o dinheiro foi, que está logo abaixo na mesma tela.
    if resultado < 0:
        alertas.append(
            AlertaFinanceiro(
                codigo="MES_NO_VERMELHO",
                severidade="CRITICO" if -resultado >= material else "ATENCAO",
                valor=resultado,
            )
        )

    # 5 e 6. O saldo é a base de toda projeção. Nunca informado é pior que
    #        desatualizado, e por isso são dois alertas e não um. Nenhum dos
    #        dois é CRÍTICO: é falta de informação, não perda de dinheiro.
    contas = financeiro_crud.listar_contas_bancarias(db, empresa_id, apenas_ativas=True)
    datas = [c.saldo_informado_em for c in contas if c.saldo_informado_em]
    if not datas:
        alertas.append(
            AlertaFinanceiro(codigo="SALDO_NUNCA_INFORMADO", severidade="ATENCAO")
        )
    else:
        # A conta mais ANTIGA é a que envelhece o número: quem atualizou o banco
        # hoje e esqueceu a gaveta há um mês tem um saldo de um mês atrás.
        mais_antiga = min(datas)
        dias = (hoje - mais_antiga).days
        if dias >= DIAS_ATE_O_SALDO_ENVELHECER:
            alertas.append(
                AlertaFinanceiro(
                    codigo="SALDO_DESATUALIZADO", severidade="ATENCAO",
                    data=mais_antiga, quantidade=dias,
                )
            )

    # 7. Gasto sem categoria: o gráfico "para onde o dinheiro foi" não responde
    #    nada enquanto a maior fatia se chamar "Sem categoria". Nunca crítico --
    #    é organização, não dinheiro em risco.
    sem_categoria = next(
        (c for c in categorias if c.plano_conta_id is None and c.total > 0), None
    )
    if sem_categoria:
        alertas.append(
            AlertaFinanceiro(
                codigo="DESPESA_SEM_CATEGORIA", severidade="ATENCAO",
                valor=sem_categoria.total,
            )
        )

    # 8. TENDÊNCIA -- o que só a série sabe dizer.
    #
    # Custa uma série de 6 meses (18 agregações triviais) a cada carregamento da
    # Visão Geral, e só para quem tem PRO. É o preço de o painel falar de
    # direção e não só de estado.
    if com_projecao:
        alertas.extend(analise_service.alertas_de_tendencia(db, empresa_id, material))

    # O SILÊNCIO PEDIDO PELO DONO, aplicado no fim de propósito: o alerta é
    # calculado de qualquer jeito e só então some da lista. Assim, quando o
    # prazo expira, ele volta com o número de HOJE -- e não com o de quando foi
    # silenciado.
    calados = financeiro_crud.codigos_dispensados(db, empresa_id, hoje)
    alertas = [a for a in alertas if a.codigo not in calados]

    # Crítico antes de atenção, preservando a ordem de urgência dentro de cada
    # grupo (o `sorted` do Python é estável).
    return sorted(alertas, key=lambda a: 0 if a.severidade == "CRITICO" else 1)


# Só estes códigos podem ser silenciados. Lista fechada para a rota não virar
# porta de entrada de linha inventada na tabela.
CODIGOS_DE_ALERTA = (
    "CAIXA_NEGATIVO",
    "CONTAS_VENCIDAS",
    "FIADO_ATRASADO",
    "MES_NO_VERMELHO",
    "SALDO_NUNCA_INFORMADO",
    "SALDO_DESATUALIZADO",
    "DESPESA_SEM_CATEGORIA",
    "RECEITA_CAINDO",
    "ORIGEM_CAINDO",
    "DEPENDENCIA_DE_ORIGEM",
    "CUSTO_SUBINDO_MAIS",
    "RECEBIMENTO_LENTO",
)


def adiar_alerta(
    db: Session, empresa_id: int, codigo: str, dias: int, usuario_token: Dict[str, Any]
) -> Dict[str, Any]:
    """Cala um alerta por `dias`. Nunca para sempre.

    "Dispensar de vez" não existe aqui, e a diferença é de propósito: alerta
    financeiro que some para sempre vira problema escondido. O prazo devolve o
    aviso; se o problema tiver sido resolvido no meio tempo, ele nem reaparece,
    porque a regra deixou de valer.
    """
    if codigo not in CODIGOS_DE_ALERTA:
        raise BadRequestException(detail="Alerta desconhecido.")

    func_id, func_nome = _funcionario_do_token(usuario_token)
    ate = hoje_local() + timedelta(days=dias)
    registro = financeiro_crud.dispensar_alerta(
        db, empresa_id, codigo=codigo, ate=ate,
        funcionario_id=func_id, funcionario_nome=func_nome,
    )
    return {"codigo": registro.codigo, "dispensado_ate": registro.dispensado_ate}


def get_resumo(
    db: Session,
    empresa_id: int,
    inicio: date,
    fim: date,
    com_projecao: bool = False,
) -> ResumoFinanceiro:
    """Entrou, saiu, sobrou — em regime de caixa. Ver o docstring do schema."""
    hoje = hoje_local()
    dt_inicio, dt_fim = inicio_do_dia_utc(inicio), fim_do_dia_utc(fim)

    # Faturamento sai da MESMA fonte do dashboard e dos relatórios. Recalcular
    # aqui abriria a porta para o financeiro mostrar um número e o relatório
    # outro, para o mesmo mês.
    stats = dashboard_crud.get_stats_agregados(db, dt_inicio, dt_fim, empresa_id)
    faturamento = int(stats.vendas_total or 0) + int(stats.os_soma or 0)

    # DESPESA, e não "tudo que saiu": compra de mercadoria fica de fora (ela é
    # categoria de tipo CUSTO no plano de contas). O dinheiro dela saiu do caixa
    # e aparece no Fluxo, mas não sai do lucro no dia da compra -- vira estoque,
    # e entra no lucro como CMV no dia em que a peça é vendida.
    despesas = financeiro_crud.total_despesas_pagas(db, empresa_id, dt_inicio, dt_fim)
    compras_estoque = financeiro_crud.total_compras_estoque(
        db, empresa_id, dt_inicio, dt_fim
    )

    # O CUSTO DO QUE FOI VENDIDO. A conta mora em services/custo_mercadoria.py,
    # compartilhada com o módulo de Relatórios -- duas cópias e as duas telas
    # mostrariam lucros diferentes para o mesmo mês.
    #
    # Ficou de fora do resultado até 02/09/2026, e a justificativa de então
    # ("a compra do fornecedor já está em despesas_pagas, descontar o CMV
    # contaria duas vezes") era verdadeira -- mas resolvia a dupla contagem
    # apagando o custo de quem NÃO lança a compra como conta a pagar, que é a
    # maioria. O caso que abriu isto foi uma OS de R$ 160 com uma peça de R$ 60
    # comprada na hora: o custo não existia em lugar nenhum e a tela mostrava
    # R$ 160 de lucro. A dupla contagem agora é resolvida na origem, pelo tipo
    # da categoria.
    custo_mercadorias, custo_sem_registro = custo_mercadoria.calcular_cmv(
        db, dt_inicio, dt_fim, empresa_id
    )

    saiu_caixa = financeiro_crud.total_saiu_do_caixa(db, empresa_id, dt_inicio, dt_fim)

    # A OUTRA LEITURA do que entrou: pelo livro, não pelas tabelas de venda.
    #
    # `faturamento` responde "quanto a loja vendeu"; este responde "quanto
    # dinheiro passou pelo caixa". Os dois divergem por motivo legítimo (fiado
    # vendido agora, fiado antigo quitado agora) e a tela mostra os dois em vez
    # de escolher um -- trocar o faturamento por este apagaria da tela o mês
    # inteiro de quem vende a prazo.
    entrou_caixa = financeiro_crud.total_entrou_no_caixa(
        db, empresa_id, dt_inicio, dt_fim
    )

    # Em aberto ATÉ O FIM DO MÊS VISTO, sem piso de data.
    #
    # Sem o teto, este era o único número da tela que ignorava o mês: olhando
    # agosto, o card somava contas de outubro. Foi assim que o primeiro uso real
    # pegou o defeito -- pagar a internet de setembro criou a de outubro pela
    # recorrência, e o total "em aberto" não se moveu, porque uma saiu e a outra
    # entrou na mesma soma.
    #
    # Sem o piso porque conta atrasada de mês anterior continua sendo devida:
    # ela precisa aparecer aqui, não sumir junto com o mês que passou.
    pendente, _pago, vencido = financeiro_crud.totais_contas_pagar(
        db, empresa_id, hoje=hoje, fim=fim
    )

    # O outro lado da rua: SEM o teto de data que o a pagar tem.
    #
    # Não é descuido. O teto do a pagar nasceu da recorrência (pagar a de
    # setembro criava a de outubro, e o total não se movia), e cobrança não se
    # reproduz na baixa. Do outro lado, fiado quase sempre vence no mês
    # seguinte: com teto, o card mostraria zero em todo mês que o dono
    # consegue abrir -- a Visão Geral trava o botão de avançar.
    #
    # Não entra no resultado: a venda fiado já está em `faturamento`, e somá-la
    # de novo contaria o mesmo dinheiro duas vezes. O card responde outra
    # pergunta -- quanto do que já vendi ainda não recebi.
    a_receber, _recebido, a_receber_vencido = financeiro_crud.totais_contas_receber(
        db, empresa_id, hoje=hoje
    )

    categorias = [
        DespesaPorCategoria(
            plano_conta_id=plano_id,
            nome=nome or "Sem categoria",
            total=total,
        )
        for plano_id, nome, total in financeiro_crud.despesas_por_categoria(
            db, empresa_id, dt_inicio, dt_fim
        )
    ]
    categorias.sort(key=lambda c: c.total, reverse=True)

    # Uma semana para frente: prazo em que ainda dá para agir (pedir prazo,
    # remanejar dinheiro). Um mês encheria o painel de coisa que não é urgente.
    proximas = financeiro_crud.proximas_a_vencer(
        db, empresa_id, ate=hoje + timedelta(days=7), limite=5
    )

    return ResumoFinanceiro(
        periodo_inicio=inicio,
        periodo_fim=fim,
        faturamento=faturamento,
        entrou_caixa=entrou_caixa,
        saiu_caixa=saiu_caixa,
        sobrou_caixa=entrou_caixa - saiu_caixa,
        despesas_pagas=despesas,
        compras_estoque=compras_estoque,
        custo_mercadorias=custo_mercadorias,
        custo_sem_registro=custo_sem_registro,
        lucro_bruto=faturamento - custo_mercadorias,
        resultado=faturamento - custo_mercadorias - despesas,
        a_pagar_pendente=pendente,
        a_pagar_vencido=vencido,
        a_receber_pendente=a_receber,
        a_receber_vencido=a_receber_vencido,
        despesas_por_categoria=categorias,
        proximas_a_vencer=[_serializar_conta(c, hoje) for c in proximas],
        alertas=_montar_alertas(
            db, empresa_id,
            faturamento=faturamento,
            resultado=faturamento - custo_mercadorias - despesas,
            a_pagar_vencido=vencido,
            a_receber_vencido=a_receber_vencido,
            categorias=categorias,
            com_projecao=com_projecao,
        ),
    )


# ===========================================================================
# FLUXO DE CAIXA (Onda 3)
# ===========================================================================

def get_fluxo_caixa(db: Session, empresa_id: int, dias: int = 30) -> FluxoCaixa:
    """A projeção dos próximos `dias`, a partir do saldo declarado pelo dono.

    Três decisões que sustentam a tela, e o motivo de cada uma:

    O SALDO DE PARTIDA É O DE HOJE, DERIVADO. É a âncora que o dono declarou
    mais tudo que o livro registrou depois dela (ver `saldo_atual_das_contas`).
    Era o `saldo_informado` puro até 02/09/2026, e essa foto parada é o defeito
    que fez o dono relatar "não sobe conforme vou vendendo". Enquanto ninguém
    declarar a âncora, `saldo_declarado` sai False e a tela pede o número em vez
    de desenhar uma linha que parte de zero.

    O ATRASADO NÃO ENTRA NA RÉGUA. Conta vencida não tem dia futuro para
    ocupar. Empurrá-la para hoje inventaria um aperto que talvez não aconteça
    (o fiado atrasado pode nunca chegar; o boleto vencido pode já ter sido
    pago no banco sem alguém dar baixa aqui). Vai num balde à parte, como
    aviso, e o dono decide.

    SÓ DIAS COM MOVIMENTO. Sessenta linhas de zero escondem as cinco que
    importam. A régua contínua é trabalho da tela, que sabe o tamanho dela.
    """
    hoje = hoje_local()
    # `dias` conta a partir de HOJE inclusive: "próximos 30 dias" para o dono da
    # loja começa hoje de manhã, não amanhã.
    fim = hoje + timedelta(days=dias - 1)

    atual = saldo_atual_das_contas(db, empresa_id)
    saldo_inicial = atual.saldo

    pagar, receber = financeiro_crud.pendentes_por_vencimento(
        db, empresa_id, inicio=hoje, fim=fim
    )

    por_dia: Dict[date, Dict[str, Any]] = {}

    def _bucket(dia: date) -> Dict[str, Any]:
        return por_dia.setdefault(
            dia, {"entradas": 0, "saidas": 0, "lancamentos": []}
        )

    for conta in receber:
        b = _bucket(conta.vencimento)
        b["entradas"] += int(conta.valor or 0)
        b["lancamentos"].append(
            FluxoLancamento(
                conta_id=conta.id, tipo=MovimentacaoFinanceiraTipo.ENTRADA.value,
                descricao=conta.descricao, valor=int(conta.valor or 0),
            )
        )

    for conta in pagar:
        b = _bucket(conta.vencimento)
        b["saidas"] += int(conta.valor or 0)
        b["lancamentos"].append(
            FluxoLancamento(
                conta_id=conta.id, tipo=MovimentacaoFinanceiraTipo.SAIDA.value,
                descricao=conta.descricao, valor=int(conta.valor or 0),
                # A tela marca as que se repetem. Sem isso, pagar a internet de
                # setembro fazia a de outubro aparecer na régua e o dono ler que
                # o pagamento não tinha sido registrado -- foi o primeiro
                # estranhamento relatado depois que o saldo passou a andar.
                recorrente=bool(conta.recorrente),
            )
        )

    saldo = saldo_inicial
    # O fundo do poço começa no próprio saldo de hoje: numa loja sem nada
    # agendado, o menor saldo do período é o que ela já tem.
    menor_saldo, menor_saldo_em = saldo_inicial, None
    primeiro_negativo: Optional[date] = None
    total_entradas = total_saidas = 0
    linha: List[FluxoDia] = []

    for data_dia in sorted(por_dia):
        dados = por_dia[data_dia]
        saldo += dados["entradas"] - dados["saidas"]
        total_entradas += dados["entradas"]
        total_saidas += dados["saidas"]

        if saldo < menor_saldo:
            menor_saldo, menor_saldo_em = saldo, data_dia
        # O PRIMEIRO dia negativo, e não o último: é a data em que o dono
        # precisa ter feito alguma coisa, e depois dela o resto é consequência.
        if saldo < 0 and primeiro_negativo is None:
            primeiro_negativo = data_dia

        linha.append(
            FluxoDia(
                data=data_dia,
                entradas=dados["entradas"],
                saidas=dados["saidas"],
                saldo=saldo,
                # Entrada antes de saída no mesmo dia: é a ordem em que o dono
                # lê ("entrou tanto, saiu tanto"), e o saldo do dia não depende
                # da ordem dentro dele.
                lancamentos=sorted(
                    dados["lancamentos"],
                    key=lambda item: (item.tipo != MovimentacaoFinanceiraTipo.ENTRADA.value,
                                      -item.valor),
                ),
            )
        )

    _p, _pg, atrasado_a_pagar = financeiro_crud.totais_contas_pagar(
        db, empresa_id, hoje=hoje
    )
    _r, _rc, atrasado_a_receber = financeiro_crud.totais_contas_receber(
        db, empresa_id, hoje=hoje
    )

    return FluxoCaixa(
        inicio=hoje,
        fim=fim,
        dias=dias,
        saldo_inicial=saldo_inicial,
        saldo_declarado=atual.declarado,
        # As duas metades do saldo, para a tela poder mostrar a conta em vez de
        # pedir fé num total: "declarou X no dia tal, e desde então moveu Y".
        saldo_ancora=atual.ancora,
        saldo_movimentado=atual.movimentado,
        saldo_entrou=atual.entrou,
        saldo_saiu=atual.saiu,
        saldo_informado_em=atual.informado_em,
        total_entradas=total_entradas,
        total_saidas=total_saidas,
        saldo_final=saldo,
        primeiro_dia_negativo=primeiro_negativo,
        menor_saldo=menor_saldo,
        menor_saldo_em=menor_saldo_em,
        atrasado_a_receber=atrasado_a_receber,
        atrasado_a_pagar=atrasado_a_pagar,
        linha=linha,
    )


# ===========================================================================
# EXTRATO (Onda 5)
# ===========================================================================

def listar_extrato(
    db: Session,
    empresa_id: int,
    *,
    inicio: Optional[date] = None,
    fim: Optional[date] = None,
    tipo: Optional[str] = None,
    origem: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> Extrato:
    """O livro do dinheiro linha a linha — o que JÁ aconteceu.

    O Fluxo de Caixa olha para frente e só enxerga documento em aberto; conta
    paga SAI da régua dele. Este é o outro lado: aqui nada sai nunca, porque
    `movimentacoes_financeiras` só recebe INSERT. Estorno não apaga o
    lançamento original, cria o contrário -- e as duas linhas ficam.

    O período filtra por `criado_em` (o instante em que o dinheiro andou), e
    não por vencimento: no extrato não existe futuro.
    """
    dt_inicio = inicio_do_dia_utc(inicio) if inicio else None
    dt_fim = fim_do_dia_utc(fim) if fim else None

    itens, total = financeiro_crud.listar_extrato(
        db, empresa_id, inicio=dt_inicio, fim=dt_fim, tipo=tipo, origem=origem,
        limit=limit, offset=offset,
    )
    entradas, saidas = financeiro_crud.totais_extrato(
        db, empresa_id, inicio=dt_inicio, fim=dt_fim, tipo=tipo, origem=origem
    )

    por_venda, por_os = financeiro_crud.documentos_de_origem(
        db,
        venda_pagamento_ids=[m.venda_pagamento_id for m in itens if m.venda_pagamento_id],
        os_pagamento_ids=[
            m.ordem_servico_pagamento_id for m in itens if m.ordem_servico_pagamento_id
        ],
    )

    def _documento(mov) -> Optional[str]:
        if mov.venda_pagamento_id:
            numero = por_venda.get(mov.venda_pagamento_id)
            return f"Venda {numero}" if numero else "Venda"
        if mov.ordem_servico_pagamento_id:
            return por_os.get(mov.ordem_servico_pagamento_id)
        return None

    # A conta bancária é lida do relacionamento por linha e não por join com
    # `joinedload`: nem toda linha tem conta, e o extrato de um mês cabe numa
    # página. Se um dia a tela paginar milhares, isto vira joinedload.
    contas = {
        c.id: c.nome for c in financeiro_crud.listar_contas_bancarias(db, empresa_id)
    }

    return Extrato(
        total_itens=total,
        total_entradas=entradas,
        total_saidas=saidas,
        saldo=entradas - saidas,
        itens=[
            ExtratoLinha(
                id=m.id,
                criado_em=m.criado_em,
                tipo=m.tipo,
                origem=m.origem,
                valor=int(m.valor or 0),
                motivo=m.motivo,
                funcionario_nome=m.funcionario_nome,
                conta_bancaria_nome=contas.get(m.conta_bancaria_id),
                forma_pagamento_nome=(
                    m.forma_pagamento.nome if m.forma_pagamento else None
                ),
                sessao_caixa_id=m.sessao_caixa_id,
                documento=_documento(m),
            )
            for m in itens
        ],
    )
