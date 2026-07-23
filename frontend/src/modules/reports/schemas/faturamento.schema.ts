import { z } from 'zod';

/** Faturamento consolidado de um dia. Valores em centavos. */
export const FaturamentoDiaSchema = z.object({
  dia: z.string(), // YYYY-MM-DD
  total_vendas: z.number(),
  total_os: z.number(),
  total_geral: z.number(),
});

export const FormaPagamentoResumoSchema = z.object({
  nome: z.string(),
  valor_total: z.number(),
});

export const RelatorioFaturamentoSchema = z.object({
  inicio: z.string(),
  fim: z.string(),
  faturamento_total: z.number(),
  faturamento_vendas: z.number(),
  faturamento_os: z.number(),
  ticket_medio: z.number(),
  qtd_vendas: z.number(),
  qtd_os: z.number(),
  por_dia: z.array(FaturamentoDiaSchema),
  formas_pagamento: z.array(FormaPagamentoResumoSchema),
});

export type RelatorioFaturamento = z.infer<typeof RelatorioFaturamentoSchema>;
export type FaturamentoDia = z.infer<typeof FaturamentoDiaSchema>;
export type FormaPagamentoResumo = z.infer<typeof FormaPagamentoResumoSchema>;
