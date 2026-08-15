import { z } from 'zod';

export const EstoqueAbcItemSchema = z.object({
  produto_id: z.number(),
  nome: z.string(),
  sku: z.string().nullable(),
  categoria: z.string().nullable(),
  faturamento: z.number(),
  quantidade: z.number(),
  participacao_pct: z.number(),
  acumulado_pct: z.number(),
  classe: z.enum(['A', 'B', 'C']),
});

export const EstoqueReposicaoItemSchema = z.object({
  produto_id: z.number(),
  nome: z.string(),
  sku: z.string().nullable(),
  quantidade: z.number(),
  quantidade_minima: z.number().nullable(),
  quantidade_ideal: z.number().nullable(),
});

export const EstoqueParadoItemSchema = z.object({
  produto_id: z.number(),
  nome: z.string(),
  sku: z.string().nullable(),
  quantidade: z.number(),
  valor_custo: z.number(),
});

export const RelatorioEstoqueSchema = z.object({
  inicio: z.string(),
  fim: z.string(),
  valor_custo_total: z.number(),
  valor_venda_total: z.number(),
  skus_ativos: z.number(),
  itens_abaixo_minimo: z.number(),
  itens_parados: z.number(),
  curva_abc: z.array(EstoqueAbcItemSchema),
  abaixo_minimo: z.array(EstoqueReposicaoItemSchema),
  parados: z.array(EstoqueParadoItemSchema),
});

export type RelatorioEstoque = z.infer<typeof RelatorioEstoqueSchema>;
export type EstoqueAbcItem = z.infer<typeof EstoqueAbcItemSchema>;
export type EstoqueReposicaoItem = z.infer<typeof EstoqueReposicaoItemSchema>;
export type EstoqueParadoItem = z.infer<typeof EstoqueParadoItemSchema>;
