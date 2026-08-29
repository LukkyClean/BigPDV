# ---------------------------------------------------------------------------
# ARQUIVO: schemas/financeiro.py
# DESCRIÇÃO: Schemas do resumo do módulo financeiro (a Visão Geral).
# ---------------------------------------------------------------------------

from datetime import date, datetime
from typing import List

from pydantic import BaseModel, Field

from app.schemas.conta_pagar import ContaPagarRead


class DespesaPorCategoria(BaseModel):
    """Quanto saiu em cada categoria, no período."""

    plano_conta_id: int | None = Field(None, description="NULL agrupa as contas sem categoria")
    nome: str = Field(..., description="Nome da categoria, ou 'Sem categoria'")
    total: int = Field(..., description="Soma do que foi PAGO na categoria (centavos)")


class AlertaFinanceiro(BaseModel):
    """Um ponto que precisa de atenção — SEM TEXTO, de propósito.

    O backend diz o QUE aconteceu (código + números); quem escreve a frase é a
    tela. Mandar texto pronto daqui congelaria o idioma, o rótulo por segmento
    ("cliente" vs "paciente") e a redação numa camada que não vê a tela.

    A regra para entrar nesta lista: precisa ter AÇÃO POSSÍVEL e um lugar para
    onde ir. Alerta que só informa vira ruído, e um painel que grita todo dia
    deixa de ser lido -- e aí some junto o alerta que importava.
    """

    codigo: str = Field(
        ...,
        description=(
            "CAIXA_NEGATIVO, CONTAS_VENCIDAS, FIADO_ATRASADO, MES_NO_VERMELHO, "
            "SALDO_NUNCA_INFORMADO, SALDO_DESATUALIZADO, DESPESA_SEM_CATEGORIA"
        ),
    )
    severidade: str = Field(..., description="CRITICO ou ATENCAO")
    valor: int | None = Field(None, description="Quanto (centavos), quando faz sentido")
    data: date | None = Field(None, description="Quando, quando faz sentido")
    quantidade: int | None = Field(None, description="Contagem (dias, itens)")
    rotulo: str | None = Field(
        None,
        description=(
            "Nome de uma origem, quando o alerta fala de uma. É DADO, não frase: "
            "a tela escreve 'X% veio de {rotulo}' — o backend continua sem "
            "mandar texto pronto"
        ),
    )


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
    entrou_caixa: int = Field(
        ...,
        description=(
            "O que de fato PASSOU PELO CAIXA no período (centavos): venda, OS e "
            "recebimento pelo livro do dinheiro, já descontados os estornos. "
            "Leitura diferente de `faturamento`, não um pedaço dele -- aqui "
            "entra o fiado do mês passado que foi quitado agora, e não entra a "
            "venda fechada que ainda não foi paga. O livro só passou a receber "
            "venda e OS sem caixa aberto em 29/08/2026; antes disso ele é "
            "incompleto, e por isso este número NÃO substitui o faturamento"
        ),
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
    alertas: List[AlertaFinanceiro] = Field(
        default_factory=list,
        description="O que precisa de atenção, mais grave primeiro. Vazio é bom sinal",
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


# ===========================================================================
# CONCILIAÇÃO (Onda 4)
# ===========================================================================

class ConciliacaoItem(BaseModel):
    """Uma cobrança que compõe o repasse do dia."""

    conta_id: int
    descricao: str
    valor: int = Field(..., description="Previsto LÍQUIDO (centavos)")
    cliente_nome: str | None = None
    forma_origem: str | None = Field(
        None, description="Forma que originou (Cartão de Crédito, PIX...); None se lançada à mão"
    )


class ConciliacaoDia(BaseModel):
    """Tudo que a loja espera receber num dia — o candidato a um depósito.

    O agrupamento é por DIA de vencimento porque é assim que o dinheiro chega:
    a operadora não deposita venda a venda, deposita o lote do dia. Conferir
    item a item contra o extrato é o trabalho que esta tela existe para evitar.
    """

    data: date
    quantidade: int
    total_previsto: int
    itens: List[ConciliacaoItem] = Field(default_factory=list)


class Conciliacao(BaseModel):
    inicio: date
    fim: date
    total_previsto: int
    dias: List[ConciliacaoDia] = Field(default_factory=list)


class ConciliacaoBaixaLote(BaseModel):
    """O depósito que caiu: um valor só, cobrindo o lote inteiro do dia."""

    data: date = Field(..., description="Dia do vencimento cujo lote está sendo conferido")
    valor_recebido: int = Field(
        ..., gt=0, description="O que caiu de fato na conta, em centavos"
    )
    conta_bancaria_id: int | None = Field(None, description="Onde o depósito caiu")
    forma_pagamento_id: int | None = None


class ConciliacaoResultado(BaseModel):
    """O que a baixa em lote fez, para a tela poder mostrar sem recarregar."""

    data: date
    quantidade: int
    total_previsto: int
    total_recebido: int
    diferenca: int = Field(
        ...,
        description=(
            "total_recebido - total_previsto (centavos). Negativo é o comum: é a "
            "taxa que a operadora reteve"
        ),
    )


# ===========================================================================
# EXTRATO (o livro do dinheiro, linha a linha)
# ===========================================================================

class ExtratoLinha(BaseModel):
    """Um movimento que JÁ aconteceu. O oposto do Fluxo de Caixa.

    Vem de `movimentacoes_financeiras`, que só recebe INSERT: um pagamento
    lançado por engano não some daqui, ele ganha uma linha contrária. É o que
    torna esta tela auditável — o extrato conta a história inteira, inclusive
    a parte que alguém preferiria esquecer.
    """

    id: int
    criado_em: datetime = Field(..., description="Instante do movimento, em UTC")
    tipo: str = Field(..., description="ENTRADA ou SAIDA")
    origem: str = Field(
        ..., description="VENDA, ORDEM_SERVICO, ABERTURA, SANGRIA, SUPRIMENTO, RECEBIMENTO ou DESPESA"
    )
    valor: int = Field(..., description="Sempre positivo (centavos); o sinal é o `tipo`")

    motivo: str | None = None
    funcionario_nome: str | None = None
    conta_bancaria_nome: str | None = None
    forma_pagamento_nome: str | None = None
    sessao_caixa_id: int | None = Field(
        None, description="Turno de caixa; NULL = não passou pela gaveta"
    )
    documento: str | None = Field(
        None, description="Venda ou OS que originou, quando houve uma"
    )


class Extrato(BaseModel):
    """A lista com os totais do MESMO filtro.

    Os dois saem da mesma query base de propósito: um rodapé que não fecha com
    a lista acima destrói a confiança na tela inteira -- e num extrato isso é
    fatal, porque ele existe justamente para ser conferido contra o banco.
    """

    total_itens: int
    total_entradas: int
    total_saidas: int
    saldo: int = Field(..., description="entradas - saidas no filtro (pode ser negativo)")
    itens: List[ExtratoLinha] = Field(default_factory=list)


# ===========================================================================
# SÉRIE MENSAL (Análise — Fase 1)
# ===========================================================================

class SerieOrigem(BaseModel):
    """De onde veio o dinheiro num mês.

    ORIGEM É DADO, NÃO CÓDIGO NA TELA. A lista chega pronta, com rótulo, e o
    frontend desenha o que vier — ele não pode conhecer "venda" nem "OS". Uma
    tela que soubesse disso teria um `v-if` por segmento, e a serigrafia, a
    marcenaria e o que vier depois quebrariam uma a uma.

    Origem nova (locação, assinatura) é uma declaração no backend, sem tocar em
    Vue.
    """

    chave: str = Field(..., description="Identificador técnico (VENDA, ORDEM_SERVICO)")
    rotulo: str = Field(..., description="Nome que o lojista lê, já no vocabulário dele")
    total: int = Field(..., description="Receita da origem no mês (centavos)")


class SerieMes(BaseModel):
    """Um mês FECHADO. O mês corrente nunca entra.

    Comparar oito dias com um mês inteiro acusaria queda todo início de mês --
    e é o erro mais fácil de reintroduzir sem perceber.
    """

    mes: str = Field(..., description="AAAA-MM")
    inicio: date
    fim: date

    receita: int = Field(..., description="Soma das origens (centavos), por competência")
    origens: List[SerieOrigem] = Field(default_factory=list)

    despesas_pagas: int
    resultado: int = Field(..., description="receita - despesas_pagas (pode ser negativo)")
    entrou_caixa: int = Field(
        ..., description="O que passou pelo caixa no mês, pelo livro do dinheiro"
    )
    prazo_medio_recebimento: int | None = Field(
        None,
        description=(
            "Dias que o cliente levou para pagar, em média, nas cobranças "
            "recebidas no mês. NULL quando não houve recebimento -- e nulo não "
            "é zero: zero diria que todo mundo pagou à vista"
        ),
    )


class Serie(BaseModel):
    """A série mensal que sustenta a tela de Análise.

    `meses_disponiveis` é o número que abre e fecha os PORTÕES da tela: cada
    métrica declara quantos meses fechados exige, e abaixo disso não aparece
    torta nem vazia -- aparece dizendo o que falta. Dois pontos fazem qualquer
    reta, e um sistema que projeta doze meses a partir de dois está inventando.
    """

    meses_disponiveis: int = Field(
        ...,
        description=(
            "Meses FECHADOS de histórico, do primeiro mês com movimento até o "
            "último mês fechado. Zero = a loja começou neste mês"
        ),
    )
    primeiro_mes: str | None = Field(None, description="AAAA-MM do primeiro mês com movimento")
    meses: List[SerieMes] = Field(default_factory=list)


# ===========================================================================
# PROJEÇÃO DE 12 MESES (Análise — Fase 4)
# ===========================================================================

class ProjecaoMes(BaseModel):
    """Um mês futuro estimado. Nada aqui existe no banco."""

    mes: str
    receita: int
    despesa: int
    resultado: int
    acumulado: int = Field(..., description="Soma dos resultados até este mês")


class Projecao(BaseModel):
    """Onde o ritmo atual leva a loja em doze meses.

    É a leitura mais arriscada do módulo, e por isso a mais cercada:

    RETA, E NÃO TENDÊNCIA. A projeção repete a média dos últimos meses; ela NÃO
    extrapola a inclinação. Com seis pontos, uma reta de regressão erra feio e a
    tela passaria a prometer uma data ("em março você quebra") que o dado não
    sustenta. Se a média já é negativa, isso é dito -- e é uma afirmação sobre o
    presente, não uma adivinhação.

    FAIXA, NUNCA NÚMERO SECO. `piso` e `teto` são os dois cenários explicáveis:
    vender `margem` a menos gastando `margem` a mais, e o contrário.

    A MARGEM SAI DO PRÓPRIO HISTÓRICO (coeficiente de variação da receita): loja
    estável ganha faixa estreita, loja instável ganha faixa larga. E alarga mais
    ainda quando o histórico é curto -- é a forma honesta de dizer "sei menos".
    """

    disponivel: bool = Field(..., description="False enquanto faltar histórico")
    meses_faltando: int = Field(0, description="Quantos meses até a projeção existir")
    base_meses: int = Field(0, description="Quantos meses entraram na média")

    receita_mensal: int = 0
    despesa_mensal: int = 0
    resultado_mensal: int = 0

    receita_12_meses: int = 0
    despesa_12_meses: int = 0
    resultado_12_meses: int = 0

    margem: float = Field(0, description="0.30 = os cenários abrem 30% para cada lado")
    piso_12_meses: int = Field(0, description="Cenário ruim: vende menos e gasta mais")
    teto_12_meses: int = Field(0, description="Cenário bom")

    meses: List[ProjecaoMes] = Field(default_factory=list)
