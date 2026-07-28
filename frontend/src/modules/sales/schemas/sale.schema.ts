import z from 'zod';

import { ProductSaleReadSchema } from './productSale.schema';
import { PaymentSaleReadSchema } from './paymentSale.schema';
import { CustomerDiscriminatedSchema } from './customers.schema';

export const FuncionarioVendaReadSchema = z.object({
  id: z.number(),
  nome: z.string(),
  cargo: z.object({ nome: z.string() }).nullable().optional(),
});

export type FuncionarioVendaRead = z.infer<typeof FuncionarioVendaReadSchema>;

export const SaleCreateSchema = z.object({
  cliente_id: z.number().nullable().optional(),
  funcionario_id: z.number({ required_error: 'Funcionário é obrigatório' }),
});

export type SaleCreate = z.infer<typeof SaleCreateSchema>;

export const SaleUpdateSchema = SaleCreateSchema.extend({
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
  observacao: z.string().max(500).nullable().optional(),
  observacao_interna: z.string().max(500).nullable().optional(),
  codigo_gerente: z.string().nullable().optional(),
}).partial();

export type SaleUpdate = z.infer<typeof SaleUpdateSchema>;

export const SaleSimpleReadSchema = z.object({
  id: z.number(),
  numero_venda: z.number().nullable().optional(),

  cliente_id: z.number().nullable().optional(),
  funcionario_id: z.number(),

  total: z.number(),

  status: z.enum(['ATIVA', 'FINALIZADA', 'CANCELADA']),

  criado_em: z.string(),

  atualizado_em: z.string().transform((dateTimeStamp) =>
    new Date(dateTimeStamp).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
    }),
  ),

  cliente: CustomerDiscriminatedSchema.nullable().optional(),
  funcionario: FuncionarioVendaReadSchema.nullable().optional(),
});

export type SaleSimpleRead = z.infer<typeof SaleSimpleReadSchema>;

export const SaleReadSchema = SaleSimpleReadSchema.extend({
  entrega: z.number(),
  descontos: z.number(),
  subtotal: z.number(),
  acrescimo: z.number(),
  troco: z.number(),

  observacao: z.string().nullable().optional(),
  observacao_interna: z.string().nullable().optional(),
  motivo_cancelamento: z.string().nullable().optional(),

  produtos: z.array(ProductSaleReadSchema),
  pagamentos: z.array(PaymentSaleReadSchema),
});

export type SaleRead = z.infer<typeof SaleReadSchema>;

export const SaleSearchSchema = z.object({
  search: z.string().max(255).nullable().optional(),
  status: z.enum(['ATIVA', 'FINALIZADA', 'CANCELADA']).nullable().optional(),
});

export type SaleSearch = z.infer<typeof SaleSearchSchema>;

export const SaleListSchema = z.object({
  filters: SaleSearchSchema,
  vendas: SaleSimpleReadSchema.array(),
  total: z.number(),
  page: z.number(),
  limit: z.number(),
  total_pages: z.number(),
  links: z.object({
    next: z.string().nullable().optional(),
    prev: z.string().nullable().optional(),
  }),
});

export type SaleList = z.infer<typeof SaleListSchema>;

export const SalesStatusSchema = z.object({
  vendas_ativas: z.number(),
  vendas_finalizadas: z.number(),
  vendas_canceladas: z.number(),
  ticket_medio: z.number(),
});

export type SalesStatus = z.infer<typeof SalesStatusSchema>;
