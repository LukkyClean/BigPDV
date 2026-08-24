import api from '@/api/axios';

import {
  CobrancaSchema,
  CobrancaStatusSchema,
  RenovacaoPlanosSchema,
  type CobrancaDataType,
  type CobrancaStatusDataType,
  type MetodoPagamento,
  type RenovacaoPlanosDataType,
} from '../schemas/renovacao.schema';

/**
 * Renovação de assinatura.
 *
 * Usa a instância `api` (com interceptor de auth), diferente do
 * `shared/services/licenca.service.ts`, que fala com uma rota pública porque
 * roda antes do login. Estas rodam depois: são exclusivas do master.
 */

const BASE = '/licenca/renovacao';

/** Períodos e preços — sempre do servidor, nunca chumbados aqui. */
export async function listarPeriodos(): Promise<RenovacaoPlanosDataType> {
  const { data } = await api.get(`${BASE}/periodos`);
  return RenovacaoPlanosSchema.parse(data);
}

export async function criarCobranca(
  metodo: MetodoPagamento,
  periodo: string,
): Promise<CobrancaDataType> {
  const { data } = await api.post(`${BASE}/cobranca`, { metodo, periodo });
  return CobrancaSchema.parse(data);
}

export async function consultarCobranca(
  cobrancaId: string,
): Promise<CobrancaStatusDataType> {
  const { data } = await api.get(`${BASE}/cobranca/${encodeURIComponent(cobrancaId)}`);
  return CobrancaStatusSchema.parse(data);
}

/** Atalho para quem pagou e não quer esperar o ciclo de revalidação. */
export async function revalidarAgora(): Promise<boolean> {
  const { data } = await api.post<{ renovada: boolean }>(`${BASE}/revalidar`);
  return data?.renovada === true;
}
