import { z } from 'zod';

/** Objeto já cadastrado que usa o identificador digitado, e de quem ele é. */
export const IdentificadorConflitoSchema = z.object({
  objeto_id: z.number(),
  cliente_id: z.number(),
  cliente_nome: z.string().nullable().optional(),
  marca: z.string().nullable().optional(),
  modelo: z.string().nullable().optional(),
  numero_serie: z.string().nullable().optional(),
  ultima_os_numero: z.string().nullable().optional(),
  ultima_os_data: z.string().nullable().optional(),
});

/**
 * `pesquisavel: false` = o texto digitado não identifica um bem ("S/N", "não
 * sei"). Não é erro nem impedimento — só não há o que procurar, e a UI fica
 * calada. `conflitos` vazio significa seguir sem aviso.
 */
export const IdentificadorCheckSchema = z.object({
  identificador: z.string(),
  pesquisavel: z.boolean(),
  conflitos: z.array(IdentificadorConflitoSchema).default([]),
});

export type IdentificadorConflitoDataType = z.infer<typeof IdentificadorConflitoSchema>;
export type IdentificadorCheckDataType = z.infer<typeof IdentificadorCheckSchema>;
