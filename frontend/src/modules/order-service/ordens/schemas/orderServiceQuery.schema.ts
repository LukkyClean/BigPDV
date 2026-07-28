import z from 'zod';
import { toTypedSchema } from '@vee-validate/zod';

import { OrderServiceBaseSchema } from './orderService.schema';

import { OsStatusEnum, OsEquipSituacaoEnum } from './enums/osEnums.schema';

import {
  CustomerPFReadSchema,
  CustomerPJReadSchema,
} from './relationship/customer/customer.schema';
import { EmployeeReadSchema } from './relationship/employee/employee.schema';
import { OsObjetoReadSchema } from './relationship/osObjeto.schema';
import { OsItemReadSchema } from './relationship/osItem.schema';
import { OsPaymentReadSchema } from './relationship/osPayment.schema';
import { OsImageReadSchema } from './relationship/osPhoto.schema';
import { PaginationBaseSchema } from '@/shared/schemas/pagination/pagination.schema';

const OrderServiceParamsSchema = z.object({
  search: z.string().max(255, 'A busca pode ter no máximo 255 caracteres').optional().nullable(),
  status: OsStatusEnum.optional().nullable(),
  priority_sort: z.boolean().optional(),
  page: z.number().int().min(1).optional(),
  limit: z.number().int().min(1).max(100).optional(),
});

export const orderServiceParamsValidationSchema = toTypedSchema(OrderServiceParamsSchema);
export type OrderServiceParamsDataType = z.infer<typeof OrderServiceParamsSchema>;

export const OrderServiceReadSchema = z.object({
  ...OrderServiceBaseSchema.shape,

  // Identificação
  id: z.number().int().positive(),
  numero_os: z.string().max(20, 'O número da OS deve ter máximo 20 caracteres'),

  // Estados
  status: OsStatusEnum,
  situacao_equipamento: OsEquipSituacaoEnum.optional().nullable(),

  // Financeiro
  valor_bruto: z.number().int(),
  valor_total: z.number().int(),
  taxa_entrega: z.number().int().default(0),
  acrescimo: z.number().int().default(0),
  credito_anterior: z.number().int().nullable().optional(),

  // Datas
  data_finalizacao: z.string().optional().nullable(),
  data_criacao: z.string(),
  data_atualizacao: z.string(),

  // Status Lógico
  ativo: z.boolean(),

  // Relacionamentos
  cliente: z.union([CustomerPFReadSchema, CustomerPJReadSchema]),
  funcionario: EmployeeReadSchema,
  objeto: OsObjetoReadSchema,
  itens: z.array(OsItemReadSchema),
  pagamentos: z.array(OsPaymentReadSchema),
  fotos: z.array(OsImageReadSchema),
}).passthrough();

export const orderServiceReadValidationSchema = toTypedSchema(OrderServiceReadSchema);
export type OrderServiceReadDataType = z.infer<typeof OrderServiceReadSchema>;

export const OrderServicePaginationSchema = z.object({
  ...PaginationBaseSchema.shape,
  filters: OrderServiceParamsSchema,
  items: z.array(OrderServiceReadSchema),
}).passthrough();

export type OrderServicePaginationDataType = z.infer<typeof OrderServicePaginationSchema>;

export const OrderServiceStatsSchema = z.object({
  total: z.number().int(),
  abertas: z.number().int(),
  finalizadas: z.number().int(),
  ticket_medio: z.number().int(),
});

export type OrderServiceStatsDataType = z.infer<typeof OrderServiceStatsSchema>;
