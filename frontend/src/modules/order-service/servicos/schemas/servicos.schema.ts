import { z } from 'zod';
import { toTypedSchema } from '@vee-validate/zod';

export const ServiceReadSchema = z.object({
  id: z.number().int().positive(),
  descricao: z.string().min(1, 'Descrição é obrigatória'),
  valor: z.number().int().nonnegative(),
  ativo: z.boolean(),
});

export const ServiceCreateSchema = z.object({
  descricao: z.string().min(1, 'Descrição é obrigatória').max(255),
  valor: z.number().int().nonnegative(),
});

export const ServiceUpdateSchema = z.object({
  descricao: z.string().min(1).max(255).optional(),
  valor: z.number().int().nonnegative().optional(),
});

export const ServiceFormSchema = z.object({
  descricao: z
    .string({ required_error: 'Descrição é obrigatória' })
    .min(3, 'Descrição deve ter no mínimo 3 caracteres')
    .max(255, 'Descrição deve ter no máximo 255 caracteres'),
  valor: z
    .number({ required_error: 'Valor é obrigatório' })
    .nonnegative('Valor não pode ser negativo'),

  // Dados fiscais (opcionais, mas validam formato quando preenchidos)
  fiscal_codigo_servico_lc116: z.string()
    .refine((v) => !v || /^\d{2}\.\d{2}$/.test(v), { message: 'Formato deve ser XX.XX (ex: 14.01)' })
    .optional().or(z.literal('')),
  fiscal_cnae: z.string()
    .refine((v) => !v || /^\d{4}-\d\/\d{2}$/.test(v), { message: 'Formato deve ser XXXX-X/XX (ex: 9512-6/00)' })
    .optional().or(z.literal('')),
  fiscal_aliquota_iss_display: z.string().optional().or(z.literal('')),
  fiscal_codigo_tributacao_municipio: z.string().optional().or(z.literal('')),
  fiscal_cfop_padrao: z.string()
    .refine((v) => !v || /^\d{4}$/.test(v), { message: 'CFOP deve ter exatamente 4 dígitos' })
    .optional().or(z.literal('')),
  fiscal_cst_icms: z.string()
    .refine((v) => !v || /^\d{2,3}$/.test(v), { message: 'CST deve ter 2 ou 3 dígitos' })
    .optional().or(z.literal('')),
  fiscal_csosn: z.string()
    .refine((v) => !v || /^\d{3}$/.test(v), { message: 'CSOSN deve ter 3 dígitos' })
    .optional().or(z.literal('')),
  fiscal_unidade_tributavel: z.string().max(6).optional().or(z.literal('')),

  // Reforma Tributária (IBS/CBS)
  fiscal_c_class_trib: z.string().max(20).optional().or(z.literal('')),
  fiscal_cst_ibs_cbs: z.string()
    .refine((v) => !v || /^\d{2,3}$/.test(v), { message: 'CST IBS/CBS deve ter 2 ou 3 dígitos' })
    .optional().or(z.literal('')),
  fiscal_aliquota_ibs_display: z.string().optional().or(z.literal('')),
  fiscal_aliquota_cbs_display: z.string().optional().or(z.literal('')),
  fiscal_c_benef: z.string().max(10).optional().or(z.literal('')),
});

const FiltersServiceSchema = z.object({
  search: z.string().nullable(),
  active: z.boolean().nullable()
})

export const PaginatedServicesSchema = z.object({
  filters: FiltersServiceSchema,
  items: z.array(ServiceReadSchema),
  total_items: z.number().int().nonnegative(),
  page: z.number().int().positive(),
  limit: z.number().int().positive(),
  total_pages: z.number().int().nonnegative(),
});

export const ServiceStatsSchema = z.object({
  total: z.number().int().nonnegative(),
  ativos: z.number().int().nonnegative(),
  inativos: z.number().int().nonnegative(),
  media_valor: z.number().int().nonnegative(),
});

export type ServiceStatsZod = z.infer<typeof ServiceStatsSchema>;
export type ServiceReadZod = z.infer<typeof ServiceReadSchema>;
export type ServiceCreateZod = z.infer<typeof ServiceCreateSchema>;
export type ServiceUpdateZod = z.infer<typeof ServiceUpdateSchema>;
export type ServiceFormZod = z.infer<typeof ServiceFormSchema>;
export type PaginatedServicesZod = z.infer<typeof PaginatedServicesSchema>;

export const servicoFormValidationSchema = toTypedSchema(ServiceFormSchema);
