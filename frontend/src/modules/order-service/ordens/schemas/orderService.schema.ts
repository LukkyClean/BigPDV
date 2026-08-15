import z from 'zod';

import { OsPriorityEnum } from './enums/osEnums.schema';

export const OrderServiceBaseSchema = z.object({
  // Status e Prioridade
  prioridade: OsPriorityEnum,

  // Descrição técnica
  defeito_relatado: z
    .string({ required_error: 'A descrição de defeito é obrigatória' })
    .trim()
    .min(1, 'A descrição de defeito é obrigatória')
    .max(500, 'A descrição de defeito deve ter máximo 500 caracteres'),
  diagnostico: z.string().max(500, 'O diagnóstico deve ter máximo 500 caracteres').optional().nullable(),
  solucao: z.string().max(500, 'A solução deve ter máximo 500 caracteres').optional().nullable(),

  // Observacoes Operacionais
  senha_aparelho: z.string().max(100, 'A senha deve ter máximo 100 caracteres').optional().nullable(),
  acessorios: z
    .string()
    .max(500, 'A observação de acessórios deve ter máximo 500 caracteres')
    .optional().nullable(),
  condicoes_aparelho: z
    .string()
    .max(500, 'A observação de condições do aparelho deve ter máximo 500 caracteres')
    .optional().nullable(),
  observacoes: z.string().max(500, 'A observação deve ter máximo 500 caracteres').optional().nullable(),

  // Check-in do segmento (nível OS): km_entrada, combustível, vistoria, etc.
  dados_adicionais: z.record(z.any()).optional().nullable(),

  // Financeiro
  desconto: z.number().int().optional().nullable(),
  valor_entrada: z.number().int().optional().nullable(),
  taxa_entrega: z.number().int().optional().nullable(),
  acrescimo: z.number().int().optional().nullable(),

  // Prazos e garantia
  garantia: z.string().max(20, 'A garantia deve ter máximo 20 caracteres').optional().nullable(),
  data_previsao: z.string().optional().nullable(),
});

