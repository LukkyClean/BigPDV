import z from 'zod';

import { ProductSaleReadSchema } from './productSale.schema';
import { parseTimestampBackend } from '@/shared/utils/date.utils';

export const FuncionarioOrcamentoReadSchema = z.object({
  id: z.number(),
  nome: z.string(),
  cargo: z.object({ nome: z.string() }).nullable().optional(),
});

export type FuncionarioOrcamentoRead = z.infer<typeof FuncionarioOrcamentoReadSchema>;

export const OrcamentoCreateSchema = z.object({
  funcionario_id: z.number({ required_error: 'Funcionário é obrigatório' }),
});

export type OrcamentoCreate = z.infer<typeof OrcamentoCreateSchema>;

export const OrcamentoUpdateSchema = z.object({
  funcionario_id: z.number().optional(),
  entrega: z
    .number()
    .min(0)
    .optional()
    .default(0)
    .transform((val) => val * 100),
  desconto: z
    .number()
    .min(0)
    .optional()
    .default(0)
    .transform((val) => val * 100),
  observacao: z.string().max(255).nullable().optional(),
}).partial();

export type OrcamentoUpdate = z.infer<typeof OrcamentoUpdateSchema>;

export const OrcamentoSimpleReadSchema = z.object({
  id: z.number(),
  funcionario_id: z.number(),
  total: z.number(),
  convertido: z.boolean(),
  venda_id: z.number().nullable().optional(),

  criado_em: z.string(),
  // Timestamp de evento: gravado em UTC no backend.
  atualizado_em: z.string().transform((dateTimeStamp) =>
    parseTimestampBackend(dateTimeStamp).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
    }),
  ),

  funcionario: FuncionarioOrcamentoReadSchema.nullable().optional(),
});

export type OrcamentoSimpleRead = z.infer<typeof OrcamentoSimpleReadSchema>;

export const OrcamentoReadSchema = OrcamentoSimpleReadSchema.extend({
  entrega: z.number(),
  descontos: z.number(),
  subtotal: z.number(),
  observacao: z.string().nullable().optional(),
  produtos: z.array(ProductSaleReadSchema),
});

export type OrcamentoRead = z.infer<typeof OrcamentoReadSchema>;

export const OrcamentoSearchSchema = z.object({
  search: z.string().max(255).nullable().optional(),
  convertido: z.boolean().nullable().optional(),
});

export type OrcamentoSearch = z.infer<typeof OrcamentoSearchSchema>;

export const OrcamentoListSchema = z.object({
  filters: OrcamentoSearchSchema,
  orcamentos: OrcamentoSimpleReadSchema.array(),
  total: z.number(),
  page: z.number(),
  limit: z.number(),
  total_pages: z.number(),
  links: z.object({
    next: z.string().nullable().optional(),
    prev: z.string().nullable().optional(),
  }),
});

export type OrcamentoList = z.infer<typeof OrcamentoListSchema>;

export const OrcamentosStatusSchema = z.object({
  orcamentos_ativos: z.number(),
  orcamentos_convertidos: z.number(),
});

export type OrcamentosStatus = z.infer<typeof OrcamentosStatusSchema>;

export const ConverterOrcamentoSchema = z.object({
  cliente_id: z.number({ required_error: 'Cliente é obrigatório' }),
});

export type ConverterOrcamento = z.infer<typeof ConverterOrcamentoSchema>;
