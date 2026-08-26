/**
 * @fileoverview Zod validation schemas for product forms
 * @description Validates product and stock data for create/edit
 */

import { z } from 'zod';
import { toTypedSchema } from '@vee-validate/zod';

export const productSchema = z.object({
  nome: z
    .string({ required_error: 'Nome e obrigatorio' })
    .min(3, 'Nome deve ter no minimo 3 caracteres')
    .max(255),
  codigo_produto: z
    .string({ required_error: 'Codigo do produto e obrigatorio' })
    .min(2, 'Codigo deve ter no minimo 2 caracteres')
    .max(100),
  codigo_barras: z.string().max(100).optional().or(z.literal('')),
  unidade_medida: z.string().max(25).optional().or(z.literal('')),
  categoria: z.string().max(100).optional().or(z.literal('')),
  marca: z.string().max(100).optional().or(z.literal('')),
  fornecedor_id: z
    .string()
    .optional()
    .or(z.literal(''))
    .refine((val) => (val ? /^\d+$/.test(val) : true), {
      message: 'Fornecedor deve ser um numero',
    }),
  localizacao_estoque: z.string().max(255).optional().or(z.literal('')),
  observacao: z.string().max(500).optional().or(z.literal('')),

  valor_entrada: z.number().optional().or(z.literal(0)),
  valor_varejo: z
    .number({ required_error: 'Valor de varejo e obrigatorio' })
    .min(0.01, 'Valor de varejo deve ser maior que zero'),
  valor_atacado: z.number().optional().or(z.literal(0)),

  quantidade: z
  .number({ required_error: 'Quantidade e obrigatoria' })
  .min(1, 'Quantidade deve ser maior que zero'),
  quantidade_minima: z
  .number()
  .optional(),
  quantidade_ideal: z
  .number()
  .optional(),

  // Dados fiscais (opcionais, mas validam formato quando preenchidos)
  fiscal_ncm: z.string()
    .refine((v) => !v || /^\d{8}$/.test(v), { message: 'NCM deve ter exatamente 8 dígitos' })
    .optional().or(z.literal('')),
  fiscal_cest: z.string()
    .refine((v) => !v || /^\d{7}$/.test(v), { message: 'CEST deve ter exatamente 7 dígitos' })
    .optional().or(z.literal('')),
  fiscal_cfop_padrao: z.string()
    .refine((v) => !v || /^\d{4}$/.test(v), { message: 'CFOP deve ter exatamente 4 dígitos' })
    .optional().or(z.literal('')),
  fiscal_origem_mercadoria: z.string().optional().or(z.literal('')),
  fiscal_unidade_tributavel: z.string().max(6).optional().or(z.literal('')),
  fiscal_gtin_tributavel: z.string()
    .refine((v) => !v || /^\d{8}$|^\d{13}$|^\d{14}$/.test(v), { message: 'GTIN deve ter 8, 13 ou 14 dígitos' })
    .optional().or(z.literal('')),
  fiscal_cst_icms: z.string()
    .refine((v) => !v || /^\d{2,3}$/.test(v), { message: 'CST deve ter 2 ou 3 dígitos' })
    .optional().or(z.literal('')),
  fiscal_csosn: z.string()
    .refine((v) => !v || /^\d{3}$/.test(v), { message: 'CSOSN deve ter 3 dígitos' })
    .optional().or(z.literal('')),

  // Alíquotas e tributos (NF-e)
  fiscal_aliquota_icms_display: z.string().optional().or(z.literal('')),
  fiscal_reducao_base_icms_display: z.string().optional().or(z.literal('')),
  fiscal_codigo_beneficio_fiscal: z.string().max(10).optional().or(z.literal('')),
  fiscal_aliquota_pis_display: z.string().optional().or(z.literal('')),
  fiscal_aliquota_cofins_display: z.string().optional().or(z.literal('')),
  fiscal_cst_pis: z.string()
    .refine((v) => !v || /^\d{2}$/.test(v), { message: 'CST PIS deve ter 2 dígitos' })
    .optional().or(z.literal('')),
  fiscal_cst_cofins: z.string()
    .refine((v) => !v || /^\d{2}$/.test(v), { message: 'CST COFINS deve ter 2 dígitos' })
    .optional().or(z.literal('')),

  // Reforma Tributária (IBS/CBS)
  fiscal_c_class_trib: z.string().max(20).optional().or(z.literal('')),
  fiscal_cst_ibs_cbs: z.string()
    .refine((v) => !v || /^\d{2,3}$/.test(v), { message: 'CST IBS/CBS deve ter 2 ou 3 dígitos' })
    .optional().or(z.literal('')),
  fiscal_aliquota_ibs_display: z.string().optional().or(z.literal('')),
  fiscal_aliquota_cbs_display: z.string().optional().or(z.literal('')),
  fiscal_c_benef: z.string().max(10).optional().or(z.literal('')),
});

export const productValidationSchema = toTypedSchema(productSchema);
export type ProductSchemaData = z.infer<typeof productSchema>;
