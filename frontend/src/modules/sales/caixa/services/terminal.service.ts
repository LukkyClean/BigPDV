/**
 * @fileoverview Cadastro durável dos terminais da loja.
 * @description Nome e papel por máquina — o que sobrevive ao logout, ao
 * contrário da tabela de presença que a licença usa para heartbeat.
 */

import { z } from 'zod';

import { api } from '@/api/axios';
import { obterHwid } from '@/shared/services/system/hwid.service';

export const PapelTerminalSchema = z.enum(['PDV', 'RETAGUARDA']);
export type PapelTerminal = z.infer<typeof PapelTerminalSchema>;

export const TerminalSchema = z.object({
  id: z.number(),
  hwid: z.string(),
  nome: z.string().nullable(),
  papel: PapelTerminalSchema.nullable(),
  criado_em: z.string(),
  atualizado_em: z.string(),
});
export type Terminal = z.infer<typeof TerminalSchema>;

export const TerminalEsteSchema = TerminalSchema.extend({
  e_retaguarda: z.boolean(),
});
export type TerminalEste = z.infer<typeof TerminalEsteSchema>;

/**
 * O HWID viaja em header porque é propriedade da MÁQUINA, não do usuário.
 *
 * O token diz quem está logado; ele não diz de onde. Dois operadores no mesmo
 * PC e um operador em dois PCs são situações normais numa loja com dois caixas,
 * e as duas perguntas — "quem é você" e "onde você está" — precisam de respostas
 * independentes.
 */
async function cabecalhoTerminal(): Promise<Record<string, string>> {
  try {
    const hwid = await obterHwid();
    return hwid ? { 'X-Terminal-HWID': hwid } : {};
  } catch {
    // Sem HWID a máquina não se identifica, e a tela trata isso como "sou um
    // caixa" — o lado seguro. Não é motivo para derrubar a requisição.
    return {};
  }
}

export async function listarTerminais(): Promise<Terminal[]> {
  const { data } = await api.get('/terminais/', { headers: await cabecalhoTerminal() });
  return z.array(TerminalSchema).parse(data);
}

export async function getEsteTerminal(): Promise<TerminalEste | null> {
  const { data } = await api.get('/terminais/este', { headers: await cabecalhoTerminal() });
  if (data === null || data === undefined || data === '') return null;
  return TerminalEsteSchema.parse(data);
}

export async function atualizarTerminal(
  id: number,
  dados: { nome?: string | null; papel?: PapelTerminal | null },
): Promise<Terminal> {
  const { data } = await api.patch(`/terminais/${id}`, dados);
  return TerminalSchema.parse(data);
}
