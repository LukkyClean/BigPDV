import { z } from 'zod';

export const RankingItemSchema = z.object({
  funcionario_id: z.number(),
  nome: z.string(),
  faturamento_vendas: z.number(),
  faturamento_os: z.number(),
  faturamento_total: z.number(),
  qtd_vendas: z.number(),
  qtd_os: z.number(),
});

export const RelatorioRankingSchema = z.object({
  inicio: z.string(),
  fim: z.string(),
  itens: z.array(RankingItemSchema),
});

export type RelatorioRanking = z.infer<typeof RelatorioRankingSchema>;
export type RankingItem = z.infer<typeof RankingItemSchema>;
