import { z } from 'zod';

export const ExtratoServicoItemSchema = z.object({
  numero_os: z.string(),
  data_finalizacao: z.string(),
  objeto: z.string().nullable().optional(),
  cliente: z.string().nullable().optional(),
  servico: z.string(),
  quantidade: z.number(),
  valor_total: z.number(),
  /** Custo da peça embutida no preço do serviço. Interno: nunca sai na via do cliente. */
  custo: z.number().default(0),
  /** valor_total − custo. É a base da comissão de serviço. */
  mao_de_obra: z.number().default(0),
});

export const RelatorioExtratoFuncionarioSchema = z.object({
  inicio: z.string(),
  fim: z.string(),
  funcionario_id: z.number(),
  funcionario_nome: z.string(),
  /** OS DISTINTAS, não linhas: três serviços numa OS contam 1. */
  qtd_os: z.number(),
  qtd_servicos: z.number(),
  valor_total: z.number(),
  /** Soma da mão de obra — o que a comissão de serviço realmente paga. */
  total_mao_de_obra: z.number().default(0),
  itens: z.array(ExtratoServicoItemSchema),
});

export type RelatorioExtratoFuncionario = z.infer<typeof RelatorioExtratoFuncionarioSchema>;
export type ExtratoServicoItem = z.infer<typeof ExtratoServicoItemSchema>;
