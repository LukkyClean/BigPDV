/**
 * @fileoverview Zod validation schema for cargo (position) form
 */

import { z } from 'zod';
import { toTypedSchema } from '@vee-validate/zod';

export const positionSchema = z.object({
  nome: z
    .string({ required_error: 'Nome do cargo e obrigatorio' })
    .min(3, 'Nome deve ter no minimo 3 caracteres')
    .max(50, 'Nome deve ter no maximo 50 caracteres'),
  permissoes: z.record(z.boolean()).optional().default({}),
  // Basis points (0–10000 = 0–100%) e centavos; null = não configurado.
  comissao_venda_percentual: z.number().min(0).max(10000).nullable().default(null),
  comissao_servico_percentual: z.number().min(0).max(10000).nullable().default(null),
  meta_mensal: z.number().min(0).nullable().default(null),
});

export const positionValidationSchema = toTypedSchema(positionSchema);
export type PositionSchemaData = z.infer<typeof positionSchema>;
