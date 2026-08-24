import { z } from 'zod';

/**
 * Objeto encontrado pela placa / nº de série / código da arte, com o dono junto.
 *
 * Vem com os campos do objeto (e não só o id) de propósito: quem clica nesta
 * linha já disse qual é o bem, então a OS abre preenchida sem passar pela tela
 * de "objeto já cadastrado?".
 */
export const ObjetoBuscaItemSchema = z.object({
  objeto_id: z.number(),
  cliente_id: z.number(),
  cliente_nome: z.string().nullable().optional(),
  tipo_equipamento: z.string().nullable().optional(),
  marca: z.string().nullable().optional(),
  modelo: z.string().nullable().optional(),
  numero_serie: z.string().nullable().optional(),
  cor: z.string().nullable().optional(),
  dados_adicionais: z.record(z.any()).nullable().optional(),
});

export const ObjetoBuscaListSchema = z.array(ObjetoBuscaItemSchema);

export type ObjetoBuscaItemDataType = z.infer<typeof ObjetoBuscaItemSchema>;
