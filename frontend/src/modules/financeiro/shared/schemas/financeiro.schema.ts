import { z } from 'zod';

/**
 * Schemas das respostas do módulo financeiro.
 *
 * Valores monetários são SEMPRE inteiros em centavos, como no resto do sistema.
 * Nunca `number` com casa decimal: 0.1 + 0.2 não dá 0.3 em ponto flutuante, e
 * num módulo cujo trabalho é somar dinheiro isso apareceria no fechamento.
 *
 * Duas espécies de data convivem aqui, e a diferença importa (ver date.utils):
 *   `vencimento` e `pago_em` (no filtro) são DATA PURA — dia 10 é dia 10 em
 *   qualquer fuso, e converter faria o boleto vencer um dia antes.
 *   `pago_em` na resposta e `criado_em` são TIMESTAMP em UTC, e convertem para
 *   o fuso da loja na exibição.
 */

/**
 * A natureza da categoria — e a conta do lucro depende dela.
 *
 *   DESPESA  gasto para a loja existir (aluguel, luz, salário). Sai do lucro
 *            no mês em que é paga.
 *   CUSTO    compra de mercadoria ou peça para revender. Sai do caixa, mas só
 *            sai do lucro quando a peça é VENDIDA — até lá virou estoque.
 *   RECEITA  entrada classificada.
 *
 * `z.string()` e não enum de propósito no schema de leitura: um backend mais
 * novo que este frontend pode mandar um tipo que a tela ainda não conhece, e
 * derrubar a listagem inteira por causa disso seria pior que exibi-lo cru.
 */
export type PlanoContaTipo = 'DESPESA' | 'CUSTO' | 'RECEITA';

export const PlanoContaSchema = z.object({
  id: z.number(),
  nome: z.string(),
  tipo: z.string(),
  padrao: z.boolean(),
  ativo: z.boolean(),
  criado_em: z.string(),
  em_uso: z.boolean(),
});
export type PlanoConta = z.infer<typeof PlanoContaSchema>;

export const ContaBancariaSchema = z.object({
  id: z.number(),
  nome: z.string(),
  tipo: z.string(),
  principal: z.boolean(),
  ativo: z.boolean(),
  // Saldo DECLARADO pelo dono, com a data em que ele declarou. O sistema não
  // calcula esse número (ver ContaBancaria.saldo_informado no backend), e a
  // data é o que permite avisar "informado há 12 dias".
  saldo_informado: z.number().default(0),
  saldo_informado_em: z.string().nullable().optional(),
  criado_em: z.string(),
});
export type ContaBancaria = z.infer<typeof ContaBancariaSchema>;

export const ContaPagarSchema = z.object({
  id: z.number(),
  descricao: z.string(),
  valor: z.number(),
  vencimento: z.string(),
  status: z.string(),

  plano_conta_id: z.number().nullable().optional(),
  plano_conta_nome: z.string().nullable().optional(),
  fornecedor_id: z.number().nullable().optional(),
  fornecedor_nome: z.string().nullable().optional(),

  valor_pago: z.number().nullable().optional(),
  pago_em: z.string().nullable().optional(),
  conta_bancaria_id: z.number().nullable().optional(),
  conta_bancaria_nome: z.string().nullable().optional(),
  forma_pagamento_id: z.number().nullable().optional(),

  recorrente: z.boolean(),
  // Parcelamento e recorrencia sao mecanismos DIFERENTES, nunca os dois juntos.
  // Nulos em conta avulsa: 1x e conta comum, nao "parcelamento de uma parcela",
  // e mostrar "1/1" em toda conta seria ruido.
  parcelamento_id: z.number().nullable().optional(),
  parcela_numero: z.number().nullable().optional(),
  parcela_total: z.number().nullable().optional(),
  observacao: z.string().nullable().optional(),
  criado_em: z.string(),

  // Derivados pelo SERVIDOR a partir da data de hoje. Não são recalculados
  // aqui: a loja e o servidor são a mesma máquina, e duplicar a regra abriria
  // espaço para a tela dizer "vence amanhã" e o filtro discordar.
  vencida: z.boolean(),
  dias_para_vencer: z.number().nullable().optional(),
});
export type ContaPagar = z.infer<typeof ContaPagarSchema>;

export const ContaPagarListagemSchema = z.object({
  itens: z.array(ContaPagarSchema),
  total_itens: z.number(),
  // Os três totais vêm do servidor e valem para o FILTRO INTEIRO, não para a
  // página. Somar `itens` aqui daria o total da página — e a diferença só
  // apareceria quando a loja já tivesse contas o bastante para paginar.
  total_pendente: z.number(),
  total_pago: z.number(),
  total_vencido: z.number(),
});
export type ContaPagarListagem = z.infer<typeof ContaPagarListagemSchema>;

export const HistoricoFinanceiroSchema = z.object({
  id: z.number(),
  campo: z.string(),
  valor_antigo: z.string().nullable().optional(),
  valor_novo: z.string().nullable().optional(),
  funcionario_nome: z.string().nullable().optional(),
  criado_em: z.string(),
});
export type HistoricoFinanceiro = z.infer<typeof HistoricoFinanceiroSchema>;

export const DespesaPorCategoriaSchema = z.object({
  plano_conta_id: z.number().nullable().optional(),
  nome: z.string(),
  total: z.number(),
});
export type DespesaPorCategoria = z.infer<typeof DespesaPorCategoriaSchema>;

export const AlertaFinanceiroSchema = z.object({
  codigo: z.string(),
  severidade: z.string(),
  valor: z.number().nullable().optional(),
  data: z.string().nullable().optional(),
  quantidade: z.number().nullable().optional(),
  // Nome de uma origem, quando o alerta fala de uma. Continua sendo DADO: a
  // frase é escrita aqui na tela.
  rotulo: z.string().nullable().optional(),
});
export type AlertaFinanceiro = z.infer<typeof AlertaFinanceiroSchema>;

export const ResumoFinanceiroSchema = z.object({
  periodo_inicio: z.string(),
  periodo_fim: z.string(),
  faturamento: z.number(),
  // A outra leitura: o que passou pelo CAIXA (livro do dinheiro). Não é um
  // pedaço do faturamento — inclui fiado antigo quitado agora e exclui venda
  // fechada que ainda não foi paga.
  entrou_caixa: z.number(),
  // O espelho: o que SAIU do caixa, já descontados os estornos. Inclui a compra
  // de mercadoria, que é dinheiro saindo mesmo não sendo despesa.
  // `.default(0)` em todo campo novo porque um backend mais antigo que este
  // frontend não os manda — e a tela não pode quebrar por causa disso.
  saiu_caixa: z.number().default(0),
  sobrou_caixa: z.number().default(0),
  // Só o que É despesa. Compra de mercadoria saiu daqui em 02/09/2026: ela é
  // categoria de tipo CUSTO e entra no lucro pelo CMV, no dia da venda.
  despesas_pagas: z.number(),
  compras_estoque: z.number().default(0),
  // O custo do que foi VENDIDO no período — a peça, o produto. É o que faltava
  // para um serviço de R$ 160 com peça de R$ 60 não aparecer como R$ 160 de
  // lucro.
  custo_mercadorias: z.number().default(0),
  // Quantas saídas de estoque não tinham custo conhecido. NÃO é dinheiro: é a
  // confiança do CMV. Diferente de zero, a tela avisa — custo subestimado em
  // silêncio vira lucro inventado.
  custo_sem_registro: z.number().default(0),
  lucro_bruto: z.number().default(0),
  // O LUCRO: faturamento - custo das mercadorias - despesas pagas.
  // Pode ser NEGATIVO, e a tela precisa saber mostrar isso: um módulo que só
  // exibe resultado positivo esconde justamente o mês que o dono precisa ver.
  resultado: z.number(),
  a_pagar_pendente: z.number(),
  a_pagar_vencido: z.number(),
  // O que já foi vendido e ainda não entrou, de QUALQUER vencimento (é o
  // único número da tela que ignora o mês visto). Não desconta nem soma ao
  // resultado — o faturamento já contou essa venda.
  a_receber_pendente: z.number(),
  a_receber_vencido: z.number(),
  despesas_por_categoria: z.array(DespesaPorCategoriaSchema),
  proximas_a_vencer: z.array(ContaPagarSchema),
  // O backend manda só o código e os números; a frase e o destino são daqui.
  // `.default([])` porque um backend mais antigo que este frontend não manda o
  // campo — e a tela não pode quebrar por causa de um alerta.
  alertas: z.array(AlertaFinanceiroSchema).default([]),
});
export type ResumoFinanceiro = z.infer<typeof ResumoFinanceiroSchema>;

// --- Entradas (o que a tela manda) ---

export interface ContaPagarPayload {
  descricao: string;
  valor: number;
  vencimento: string;
  plano_conta_id?: number | null;
  fornecedor_id?: number | null;
  recorrente?: boolean;
  /**
   * Quantidade de parcelas. 1 = conta unica.
   *
   * `valor` e o valor DE CADA parcela, nunca o total — e como a maquininha e a
   * fatura falam ("10x de 100"), e nao sobra centavo para distribuir.
   */
  parcelas?: number;
  observacao?: string | null;
  /**
   * Só na EDIÇÃO de uma parcela: repete a correção nas parcelas seguintes que
   * ainda estão em aberto. Existe porque corrigir a data de um empréstimo em
   * 72x significaria abrir 72 telas — e ninguém abre.
   *
   * O vencimento RE-ANCORA (mesmo dia, mês a mês), não é copiado; parcela paga
   * e parcela anterior não são tocadas.
   */
  aplicar_nas_proximas?: boolean;
}

export interface ContaPagarBaixaPayload {
  valor_pago?: number;
  pago_em?: string;
  conta_bancaria_id?: number | null;
  forma_pagamento_id?: number | null;
  observacao?: string | null;
}

export interface ContaPagarFiltros {
  status?: string;
  inicio?: string;
  fim?: string;
  plano_conta_id?: number;
  busca?: string;
  // Recortes do painel de atenção. `vencidas` IGNORA o período no backend:
  // dívida vencida é de mês anterior quase sempre, e filtrar pelo mês visto
  // esconderia justamente a conta do alerta.
  vencidas?: boolean;
  sem_categoria?: boolean;
}

// ===========================================================================
// CONTAS A RECEBER
// ===========================================================================

export const ContaReceberSchema = z.object({
  id: z.number(),
  descricao: z.string(),
  valor: z.number(),
  taxa: z.number(),
  juros: z.number(),
  juros_destino: z.string(),
  vencimento: z.string(),
  status: z.string(),

  cliente_id: z.number().nullable().optional(),
  cliente_nome: z.string().nullable().optional(),

  valor_recebido: z.number().nullable().optional(),
  recebido_em: z.string().nullable().optional(),
  conta_bancaria_id: z.number().nullable().optional(),
  conta_bancaria_nome: z.string().nullable().optional(),
  forma_pagamento_id: z.number().nullable().optional(),

  venda_pagamento_id: z.number().nullable().optional(),
  ordem_servico_pagamento_id: z.number().nullable().optional(),
  // Nasceu do fecho de uma venda ou OS. A tela usa para explicar de onde veio e
  // para nao oferecer edicao livre do que um documento fechado ja decidiu.
  automatica: z.boolean(),

  observacao: z.string().nullable().optional(),
  criado_em: z.string(),
  vencida: z.boolean(),
  dias_para_vencer: z.number().nullable().optional(),
});
export type ContaReceber = z.infer<typeof ContaReceberSchema>;

export const ContaReceberListagemSchema = z.object({
  itens: z.array(ContaReceberSchema),
  total_itens: z.number(),
  total_pendente: z.number(),
  total_recebido: z.number(),
  total_vencido: z.number(),
});
export type ContaReceberListagem = z.infer<typeof ContaReceberListagemSchema>;

export interface ContaReceberPayload {
  descricao: string;
  valor: number;
  vencimento: string;
  cliente_id?: number | null;
  taxa?: number;
  observacao?: string | null;
}

export interface ContaReceberBaixaPayload {
  /** TOTAL que entrou, juros incluso. */
  valor_recebido?: number;
  /** Juros/multa por atraso. Separado porque e receita FINANCEIRA, nao venda. */
  juros?: number;
  /** LOJA = multa, entra no caixa. OPERADORA = maquininha, a loja NAO recebe. */
  juros_destino?: 'LOJA' | 'OPERADORA';
  recebido_em?: string;
  conta_bancaria_id?: number | null;
  forma_pagamento_id?: number | null;
  observacao?: string | null;
}

// --- Fluxo de Caixa (Onda 3) ---

export const FluxoLancamentoSchema = z.object({
  // A conta se repete todo mês. A tela marca porque a próxima ocorrência nasce
  // da BAIXA da anterior: quem paga a de setembro vê a de outubro aparecer na
  // régua na mesma hora, e sem a marca isso se lê como "não registrou".
  recorrente: z.boolean().default(false),
  conta_id: z.number(),
  tipo: z.string(),
  descricao: z.string(),
  valor: z.number(),
});
export type FluxoLancamento = z.infer<typeof FluxoLancamentoSchema>;

export const FluxoDiaSchema = z.object({
  data: z.string(),
  entradas: z.number(),
  saidas: z.number(),
  saldo: z.number(),
  lancamentos: z.array(FluxoLancamentoSchema),
});
export type FluxoDia = z.infer<typeof FluxoDiaSchema>;

export const FluxoCaixaSchema = z.object({
  inicio: z.string(),
  fim: z.string(),
  dias: z.number(),
  // O saldo de HOJE: a âncora declarada mais tudo que o livro moveu depois
  // dela. Até 02/09/2026 era só a âncora, e por isso não andava com as vendas.
  saldo_inicial: z.number(),
  // As metades, para a tela mostrar a conta em vez de pedir fé no total.
  saldo_ancora: z.number().default(0),
  saldo_movimentado: z.number().default(0),
  // Entrou e saiu SEPARADOS: um líquido de zero pode ser "nada aconteceu" ou
  // "entraram 500 e saíram 500", e as duas leituras pedem reações opostas.
  saldo_entrou: z.number().default(0),
  saldo_saiu: z.number().default(0),
  // `false` NÃO significa saldo zero: significa que ninguém declarou. A tela
  // pede o número em vez de desenhar uma linha que parte de zero.
  saldo_declarado: z.boolean(),
  saldo_informado_em: z.string().nullable().optional(),
  total_entradas: z.number(),
  total_saidas: z.number(),
  saldo_final: z.number(),
  primeiro_dia_negativo: z.string().nullable().optional(),
  menor_saldo: z.number(),
  menor_saldo_em: z.string().nullable().optional(),
  atrasado_a_receber: z.number(),
  atrasado_a_pagar: z.number(),
  // Só os dias COM movimento; a régua contínua é desenhada pela tela.
  linha: z.array(FluxoDiaSchema),
});
export type FluxoCaixa = z.infer<typeof FluxoCaixaSchema>;

// --- Conciliação (Onda 4) ---

export const ConciliacaoItemSchema = z.object({
  conta_id: z.number(),
  descricao: z.string(),
  valor: z.number(),
  cliente_nome: z.string().nullable().optional(),
  forma_origem: z.string().nullable().optional(),
});
export type ConciliacaoItem = z.infer<typeof ConciliacaoItemSchema>;

export const ConciliacaoDiaSchema = z.object({
  data: z.string(),
  quantidade: z.number(),
  total_previsto: z.number(),
  itens: z.array(ConciliacaoItemSchema),
});
export type ConciliacaoDia = z.infer<typeof ConciliacaoDiaSchema>;

export const ConciliacaoSchema = z.object({
  inicio: z.string(),
  fim: z.string(),
  total_previsto: z.number(),
  // Um grupo por DIA de vencimento: é o formato em que o dinheiro chega.
  dias: z.array(ConciliacaoDiaSchema),
});
export type Conciliacao = z.infer<typeof ConciliacaoSchema>;

export const ConciliacaoResultadoSchema = z.object({
  data: z.string(),
  quantidade: z.number(),
  total_previsto: z.number(),
  total_recebido: z.number(),
  diferenca: z.number(),
});
export type ConciliacaoResultado = z.infer<typeof ConciliacaoResultadoSchema>;

export interface ConciliacaoBaixaLotePayload {
  data: string;
  valor_recebido: number;
  conta_bancaria_id?: number | null;
  forma_pagamento_id?: number | null;
}

// --- Extrato (o livro do dinheiro) ---

export const ExtratoLinhaSchema = z.object({
  id: z.number(),
  criado_em: z.string(),
  tipo: z.string(),
  origem: z.string(),
  valor: z.number(),
  motivo: z.string().nullable().optional(),
  funcionario_nome: z.string().nullable().optional(),
  conta_bancaria_nome: z.string().nullable().optional(),
  forma_pagamento_nome: z.string().nullable().optional(),
  sessao_caixa_id: z.number().nullable().optional(),
  documento: z.string().nullable().optional(),
});
export type ExtratoLinha = z.infer<typeof ExtratoLinhaSchema>;

export const ExtratoSchema = z.object({
  total_itens: z.number(),
  total_entradas: z.number(),
  total_saidas: z.number(),
  saldo: z.number(),
  itens: z.array(ExtratoLinhaSchema),
});
export type Extrato = z.infer<typeof ExtratoSchema>;

export interface ExtratoFiltros {
  inicio?: string;
  fim?: string;
  tipo?: string;
  origem?: string;
  /**
   * A tela usa o padrão do backend (200). A IMPRESSÃO pede o teto (500), senão
   * um mês movimentado sairia cortado no papel sem ninguém perceber — e um
   * extrato incompleto é pior que nenhum, porque ele parece completo.
   */
  limit?: number;
}

// --- Série mensal (Análise) ---

export const SerieOrigemSchema = z.object({
  chave: z.string(),
  rotulo: z.string(),
  total: z.number(),
});
export type SerieOrigem = z.infer<typeof SerieOrigemSchema>;

export const SerieMesSchema = z.object({
  mes: z.string(),
  inicio: z.string(),
  fim: z.string(),
  receita: z.number(),
  // A tela NÃO conhece "venda" nem "OS": desenha o que vier, com o rótulo que
  // vier. É o que permite um segmento novo entrar por declaração no backend.
  origens: z.array(SerieOrigemSchema),
  despesas_pagas: z.number(),
  custo_mercadorias: z.number().default(0),
  // MESMA fórmula do card da Visão Geral, de propósito: a Análise existe para
  // comparar meses, e uma série que somasse diferente faria o dono ver queda
  // onde não houve.
  resultado: z.number(),
  entrou_caixa: z.number(),
  // NULL não é zero: zero diria que todo mundo pagou à vista.
  prazo_medio_recebimento: z.number().nullable().optional(),
});
export type SerieMes = z.infer<typeof SerieMesSchema>;

export const SerieSchema = z.object({
  // O número que abre e fecha os portões da tela.
  meses_disponiveis: z.number(),
  primeiro_mes: z.string().nullable().optional(),
  meses: z.array(SerieMesSchema),
});
export type Serie = z.infer<typeof SerieSchema>;

// --- Projeção de 12 meses ---

export const ProjecaoMesSchema = z.object({
  mes: z.string(),
  receita: z.number(),
  despesa: z.number(),
  resultado: z.number(),
  acumulado: z.number(),
});
export type ProjecaoMes = z.infer<typeof ProjecaoMesSchema>;

export const ProjecaoSchema = z.object({
  // `false` enquanto faltar histórico — e a tela mostra o que falta, não um
  // gráfico chutado.
  disponivel: z.boolean(),
  meses_faltando: z.number(),
  base_meses: z.number(),
  receita_mensal: z.number(),
  despesa_mensal: z.number(),
  resultado_mensal: z.number(),
  receita_12_meses: z.number(),
  despesa_12_meses: z.number(),
  resultado_12_meses: z.number(),
  margem: z.number(),
  piso_12_meses: z.number(),
  teto_12_meses: z.number(),
  meses: z.array(ProjecaoMesSchema),
});
export type Projecao = z.infer<typeof ProjecaoSchema>;

/**
 * O card "Custo do que vendeu" aberto, linha a linha.
 *
 * Existe porque o card mostrava um total e nada mais: em 05/09/2026 o dono
 * passou uma tarde conferindo R$ 846 de CMV no papel, OS por OS, e o que
 * faltava era um custo lançado num item avulso — invisível depois que a OS
 * finaliza. Número que não se consegue abrir não se consegue confiar.
 */
export const CustoDetalheLinhaSchema = z.object({
  data: z.string().nullable(),
  /** VENDA ou OS. */
  origem: z.string(),
  referencia: z.string(),
  descricao: z.string(),
  quantidade: z.number(),
  /** Negativo em estorno: a peça voltou pra prateleira e o custo sai da conta. */
  custo: z.number(),
  /** ESTOQUE (congelado na baixa), DECLARADO (digitado à mão) ou ESTORNO. */
  fonte: z.string(),
});

export const CustoDetalheSchema = z.object({
  periodo_inicio: z.string(),
  periodo_fim: z.string(),
  total: z.number(),
  linhas: z.array(CustoDetalheLinhaSchema).default([]),
});

export type CustoDetalhe = z.infer<typeof CustoDetalheSchema>;
export type CustoDetalheLinha = z.infer<typeof CustoDetalheLinhaSchema>;
