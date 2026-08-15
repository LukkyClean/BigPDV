import z from 'zod';

import { OsItemTypeEnum, OsItemMeasureEnum, OsItemAprovacaoEnum } from '../enums/osEnums.schema';

const OsItemBaseSchema = z.object({
  tipo: OsItemTypeEnum,
  nome: z
    .string({ required_error: 'O nome é obrigatório' })
    .max(255, 'O nome deve ter no máximo 255 caracteres'),
  unidade_medida: OsItemMeasureEnum,
  quantidade: z
    .number({ required_error: 'A quantidade é obrigatória' })
    .int()
    .min(0, 'A quantidade deve ser maior ou igual a 0'),
  valor_unitario: z
    .number({ required_error: 'O valor unitário é obrigatório' })
    .int()
    .min(0, 'O valor unitário deve ser maior ou igual a 0'),
  // Aprovação/garantia por item. Opcional: o backend já default APROVADO,
  // então não enviar preserva o comportamento atual (informática intacta).
  status_aprovacao: OsItemAprovacaoEnum.optional(),
  garantia_dias: z.number().int().min(0).optional().nullable(),
  garantia_km: z.number().int().min(0).optional().nullable(),
  // Peça EMBUTIDA no serviço: sai do estoque e entra no custo, mas não é
  // listada nas vias do cliente. Exige valor zero — o dinheiro fica na linha do
  // serviço, senão as linhas impressas não somam o total impresso.
  // Opcional: o backend já default `true`, então não enviar mantém tudo como é hoje.
  visivel_cliente: z.boolean().optional(),
  // Quanto a loja PAGOU por unidade. Campo INTERNO — nenhum template de
  // impressão o exibe, por decisão explícita: o cliente nunca vê o que foi pago
  // pela peça. Só se aplica a item sem produto do catálogo; com produto, o custo
  // vem do livro de estoque.
  custo_unitario: z.number().int().min(0).optional().nullable(),
});

export const OsItemCreateSchema = z.object({
  ...OsItemBaseSchema.shape,
  item_id: z.number().int().optional(),
});

export type OsItemCreateSchemaDataType = z.infer<typeof OsItemCreateSchema>

export const OsItemReadSchema = z.object({
  ...OsItemBaseSchema.shape,
  id: z.number().int().positive(),
  ordem_servico_id: z.number().int().positive(),
  produto_id: z.number().int().positive().optional().nullable(),
  servico_id: z.number().int().positive().optional().nullable(),
  valor_total: z.number().int(),
});

export const OsItemUpdateSchema = z.object({
  nome: z.string().max(255, 'O nome deve ter no máximo 255 caracteres').optional(),
  unidade_medida: OsItemMeasureEnum.optional(),
  quantidade: z.number().int().min(0, 'A quantidade deve ser maior ou igual a 0').optional(),
  valor_unitario: z.number().min(0, 'O valor unitário deve ser maior ou igual a 0').optional(),
  status_aprovacao: OsItemAprovacaoEnum.optional(),
  garantia_dias: z.number().int().min(0).optional().nullable(),
  garantia_km: z.number().int().min(0).optional().nullable(),
  visivel_cliente: z.boolean().optional(),
  custo_unitario: z.number().int().min(0).optional().nullable(),
});

export type OsItemUpdateSchemaDataType = z.infer<typeof OsItemUpdateSchema>
export type OsItemReadSchemaDataType = z.infer<typeof OsItemReadSchema>
