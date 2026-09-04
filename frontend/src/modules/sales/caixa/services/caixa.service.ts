import api from '@/api/axios';

import {
  SessaoCaixaResumoSchema,
  type AbrirCaixaPayload,
  type FecharCaixaPayload,
  type MovimentoCaixaPayload,
  type SessaoCaixaResumo,
} from '../schemas/caixa.schema';

const CAIXA_ENDPOINT = '/caixa';

/**
 * Turno aberto do operador logado.
 *
 * Devolve `null` em dois casos que a tela trata igual: o controle de caixa está
 * desligado, ou está ligado e não há turno aberto. Quem diferencia os dois é a
 * configuração de vendas (`controlar_caixa`), não este endpoint — por isso ele
 * responde 200 com `null` em vez de 404.
 */
export async function getSessaoAtual(): Promise<SessaoCaixaResumo | null> {
  const { data } = await api.get(`${CAIXA_ENDPOINT}/atual`);
  if (!data) return null;
  return SessaoCaixaResumoSchema.parse(data);
}

export async function abrirCaixa(payload: AbrirCaixaPayload): Promise<SessaoCaixaResumo> {
  const { data } = await api.post(`${CAIXA_ENDPOINT}/abrir`, payload);
  return SessaoCaixaResumoSchema.parse(data);
}

export async function registrarSuprimento(
  payload: MovimentoCaixaPayload,
): Promise<SessaoCaixaResumo> {
  const { data } = await api.post(`${CAIXA_ENDPOINT}/suprimento`, payload);
  return SessaoCaixaResumoSchema.parse(data);
}

export async function registrarSangria(
  payload: MovimentoCaixaPayload,
): Promise<SessaoCaixaResumo> {
  const { data } = await api.post(`${CAIXA_ENDPOINT}/sangria`, payload);
  return SessaoCaixaResumoSchema.parse(data);
}

export async function fecharCaixa(payload: FecharCaixaPayload): Promise<SessaoCaixaResumo> {
  const { data } = await api.post(`${CAIXA_ENDPOINT}/fechar`, payload);
  return SessaoCaixaResumoSchema.parse(data);
}
