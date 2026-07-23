import { z } from 'zod';

export const ComissaoItemSchema = z.object({
  funcionario_id: z.number(),
  nome: z.string(),
  faturamento_vendas: z.number(),
  faturamento_os: z.number(),
  faturamento_total: z.number(),
  percentual_venda: z.number().nullable(),
  percentual_servico: z.number().nullable(),
  comissao_vendas: z.number(),
  comissao_servico: z.number(),
  comissao_total: z.number(),
  meta_mensal: z.number().nullable(),
  meta_atingida_percentual: z.number().nullable(),
});

export const RelatorioComissaoSchema = z.object({
  inicio: z.string(),
  fim: z.string(),
  total_comissao: z.number(),
  itens: z.array(ComissaoItemSchema),
});

export type RelatorioComissao = z.infer<typeof RelatorioComissaoSchema>;
export type ComissaoItem = z.infer<typeof ComissaoItemSchema>;
