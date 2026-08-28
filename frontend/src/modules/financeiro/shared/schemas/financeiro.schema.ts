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

export const ResumoFinanceiroSchema = z.object({
  periodo_inicio: z.string(),
  periodo_fim: z.string(),
  faturamento: z.number(),
  despesas_pagas: z.number(),
  // Pode ser NEGATIVO, e a tela precisa saber mostrar isso: um módulo que só
  // exibe resultado positivo esconde justamente o mês que o dono precisa ver.
  resultado: z.number(),
  a_pagar_pendente: z.number(),
  a_pagar_vencido: z.number(),
  despesas_por_categoria: z.array(DespesaPorCategoriaSchema),
  proximas_a_vencer: z.array(ContaPagarSchema),
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
}
