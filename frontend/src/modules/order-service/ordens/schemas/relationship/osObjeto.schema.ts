import z from 'zod';

import { OsEquipTypeEnum } from '../enums/osEnums.schema';
import type { OsEquipTypeEnumDataType } from '../enums/osEnums.schema';

/**
 * `tipo_equipamento` é o enum de TI (COMPUTADOR, CELULAR...). Outros segmentos
 * não o usam: o select fica oculto e o campo chega como `''`, e reutilizar um
 * objeto do histórico traz o rótulo do shim do backend (ex: "Veículo").
 * Qualquer coisa fora do enum vira `undefined` — agnóstico de segmento, sem
 * quebrar TI, sem deixar passar lixo.
 *
 * Usa `transform` (e não `preprocess`) de propósito: `preprocess` tipa a
 * ENTRADA como `unknown`, o que fazia `defineField('tipo_equipamento')` devolver
 * `Ref<unknown>` e não casar com `Ref<string | null | undefined>` do contexto —
 * eram 2 dos erros que quebravam o `npm run build`. Com `transform`, a entrada
 * continua `string | null | undefined` e a saída é o enum.
 */
const TipoEquipamentoOpcional = z
  .string()
  .nullable()
  .optional()
  .transform((v): OsEquipTypeEnumDataType | undefined =>
    (OsEquipTypeEnum.options as readonly string[]).includes(v as string)
      ? (v as OsEquipTypeEnumDataType)
      : undefined,
  );

/**
 * Regex de placa (Mercosul ABC1D23 ou antiga ABC1234), já normalizada
 * (maiúsculas, sem hífen). Espelha app/core/segmentos.PLACA_REGEX do backend.
 * Usada como validação leve de UX no segmento de oficina; o backend é a fonte da verdade.
 */
export const PLACA_REGEX = /^(?:[A-Z]{3}\d{4}|[A-Z]{3}\d[A-Z]\d{2})$/;

export const OsObjetoCreateSchema = z.object({
  tipo_equipamento: TipoEquipamentoOpcional,
  marca: z
    .string({ required_error: 'A marca é obrigatória' })
    .trim()
    .min(1, 'A marca é obrigatória')
    .max(100, 'A marca deve ter no máximo 100 caracteres'),
  modelo: z
    .string({ required_error: 'O modelo é obrigatório' })
    .trim()
    .min(1, 'O modelo é obrigatório')
    .max(100, 'O modelo deve ter no máximo 100 caracteres'),
  numero_serie: z
    .string({ required_error: 'O número de série é obrigatório' })
    .trim()
    .min(1, 'O número de série é obrigatório')
    .max(100, 'O número de série deve ter no máximo 100 caracteres'),
  // `imei` não é coluna do objeto — o backend devolve null quando não há.
  // `.optional()` aceita undefined mas REPROVA null, e o campo aparecia em
  // vermelho com "Expected string, received null". Trata null como ausente.
  imei: z
    .string()
    .max(20, 'O IMEI deve ter no máximo 20 caracteres')
    .nullable()
    .optional()
    .transform((v) => v ?? ''),
  cor: z.string().max(50, 'A cor deve ter no máximo 50 caracteres').optional(),
  // Lembrete de revisão (oficina) — colunas do objeto no backend.
  proxima_revisao_data: z.string().optional().nullable(),
  proxima_revisao_km: z.number().int().min(0).optional().nullable(),
  // Campos dinâmicos do objeto por segmento (ex: oficina → chassi, ano).
  dados_adicionais: z.record(z.any()).optional().default({}),
});

export const OsObjetoReadSchema = z.object({
  ...OsObjetoCreateSchema.shape,
  // Na resposta, tipo_equipamento é livre por segmento (ex: 'Veículo', 'COMPUTADOR').
  tipo_equipamento: z.string().optional().nullable(),
  id: z.number().int().positive(),
  cliente_id: z.number().int().positive(),
  ativo: z.boolean(),
  data_criacao: z.string(),
  data_atualizacao: z.string(),
});

export const OsObjetoUpdateSchema = z.object({
  tipo_equipamento: TipoEquipamentoOpcional,
  marca: z.string().max(255, 'A marca deve ter no máximo 255 caracteres').optional(),
  modelo: z.string().max(255, 'O modelo deve ter no máximo 255 caracteres').optional(),
  numero_serie: z
    .string({ required_error: 'O número de série é obrigatório' })
    .max(255, 'O número de série deve ter no máximo 255 caracteres')
    .optional(),
  // `imei` não é coluna do objeto — o backend devolve null quando não há. Sem
  // `.nullable()` o Zod reprovava na carga da OS com "Expected string, received
  // null" (campo em vermelho). É opcional; não uso transform aqui porque este
  // schema também valida updates parciais (OSFinalizarModal só manda revisão).
  imei: z.string().max(255, 'O IMEI deve ter no máximo 255 caracteres').nullable().optional(),
  cor: z.string().max(255, 'A cor deve ter no máximo 255 caracteres').optional(),
  cliente_id: z.number().int().positive().optional(),
  proxima_revisao_data: z.string().optional().nullable(),
  proxima_revisao_km: z.number().int().min(0).optional().nullable(),
  dados_adicionais: z.record(z.any()).optional(),
});

export type OsObjetoCreateSchemaDataType = z.infer<typeof OsObjetoCreateSchema>
export type OsObjetoReadSchemaDataType = z.infer<typeof OsObjetoReadSchema>
export type OsObjetoUpdateSchemaDataType = z.infer<typeof OsObjetoUpdateSchema>
