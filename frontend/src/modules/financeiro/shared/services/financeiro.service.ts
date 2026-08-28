import api from '@/api/axios';
import { safeParseResponse } from '@/shared/utils/parse.utils';

import {
  ContaBancariaSchema,
  ContaPagarListagemSchema,
  ContaPagarSchema,
  HistoricoFinanceiroSchema,
  PlanoContaSchema,
  ResumoFinanceiroSchema,
  type ContaBancaria,
  type ContaPagar,
  type ContaPagarBaixaPayload,
  type ContaPagarFiltros,
  type ContaPagarListagem,
  type ContaPagarPayload,
  ContaReceberListagemSchema,
  ContaReceberSchema,
  type ContaReceber,
  type ContaReceberBaixaPayload,
  type ContaReceberListagem,
  type ContaReceberPayload,
  type HistoricoFinanceiro,
  type PlanoConta,
  type ResumoFinanceiro,
} from '../schemas/financeiro.schema';

import { z } from 'zod';

/**
 * Chamadas do módulo financeiro.
 *
 * Todas passam pelo mesmo `/financeiro`, que no backend exige o módulo
 * FINANCEIRO na licença além da permissão do cargo. Um 403 com
 * `MODULO_NAO_CONTRATADO` significa "a loja não contratou", e não "você não
 * pode" — quem trata essa diferença é o interceptor do axios.
 */

// ===========================================================================
// PLANO DE CONTAS
// ===========================================================================

export async function listarPlanoContas(apenasAtivos = false): Promise<PlanoConta[]> {
  const { data } = await api.get('/financeiro/plano-contas', {
    params: { apenas_ativos: apenasAtivos },
  });
  return safeParseResponse(z.array(PlanoContaSchema), data, 'listarPlanoContas');
}

export async function criarPlanoConta(nome: string): Promise<PlanoConta> {
  const { data } = await api.post('/financeiro/plano-contas', { nome });
  return safeParseResponse(PlanoContaSchema, data, 'criarPlanoConta');
}

export async function atualizarPlanoConta(
  id: number,
  dados: { nome?: string; ativo?: boolean },
): Promise<PlanoConta> {
  const { data } = await api.patch(`/financeiro/plano-contas/${id}`, dados);
  return safeParseResponse(PlanoContaSchema, data, 'atualizarPlanoConta');
}

// ===========================================================================
// CONTAS BANCÁRIAS
// ===========================================================================

export async function listarContasBancarias(apenasAtivas = true): Promise<ContaBancaria[]> {
  const { data } = await api.get('/financeiro/contas-bancarias', {
    params: { apenas_ativas: apenasAtivas },
  });
  return safeParseResponse(z.array(ContaBancariaSchema), data, 'listarContasBancarias');
}

export async function criarContaBancaria(payload: {
  nome: string;
  tipo: string;
  principal?: boolean;
}): Promise<ContaBancaria> {
  const { data } = await api.post('/financeiro/contas-bancarias', payload);
  return safeParseResponse(ContaBancariaSchema, data, 'criarContaBancaria');
}

// ===========================================================================
// CONTAS A PAGAR
// ===========================================================================

export async function listarContasPagar(
  filtros: ContaPagarFiltros = {},
): Promise<ContaPagarListagem> {
  // Campos vazios não viram query string: `?status=` faria o backend filtrar
  // por status vazio e devolver lista vazia, em vez de "sem filtro".
  const params = Object.fromEntries(
    Object.entries(filtros).filter(([, v]) => v !== undefined && v !== '' && v !== null),
  );
  const { data } = await api.get('/financeiro/contas-pagar', { params });
  return safeParseResponse(ContaPagarListagemSchema, data, 'listarContasPagar');
}

export async function criarContaPagar(payload: ContaPagarPayload): Promise<ContaPagar> {
  const { data } = await api.post('/financeiro/contas-pagar', payload);
  return safeParseResponse(ContaPagarSchema, data, 'criarContaPagar');
}

export async function atualizarContaPagar(
  id: number,
  payload: Partial<ContaPagarPayload>,
): Promise<ContaPagar> {
  const { data } = await api.patch(`/financeiro/contas-pagar/${id}`, payload);
  return safeParseResponse(ContaPagarSchema, data, 'atualizarContaPagar');
}

/** Cancela — o backend NÃO exclui a linha, só muda o status. */
export async function cancelarContaPagar(id: number): Promise<ContaPagar> {
  const { data } = await api.delete(`/financeiro/contas-pagar/${id}`);
  return safeParseResponse(ContaPagarSchema, data, 'cancelarContaPagar');
}

export async function pagarConta(
  id: number,
  payload: ContaPagarBaixaPayload,
): Promise<ContaPagar> {
  const { data } = await api.post(`/financeiro/contas-pagar/${id}/pagar`, payload);
  return safeParseResponse(ContaPagarSchema, data, 'pagarConta');
}

export async function estornarPagamento(id: number, motivo: string): Promise<ContaPagar> {
  const { data } = await api.post(`/financeiro/contas-pagar/${id}/estornar`, { motivo });
  return safeParseResponse(ContaPagarSchema, data, 'estornarPagamento');
}

export async function listarHistoricoDaConta(id: number): Promise<HistoricoFinanceiro[]> {
  const { data } = await api.get(`/financeiro/contas-pagar/${id}/historico`);
  return safeParseResponse(
    z.array(HistoricoFinanceiroSchema),
    data,
    'listarHistoricoDaConta',
  );
}

// ===========================================================================
// RESUMO
// ===========================================================================

export async function getResumo(inicio: string, fim: string): Promise<ResumoFinanceiro> {
  const { data } = await api.get('/financeiro/resumo', { params: { inicio, fim } });
  return safeParseResponse(ResumoFinanceiroSchema, data, 'getResumo');
}

// ===========================================================================
// CONTAS A RECEBER
// ===========================================================================

export async function listarContasReceber(
  filtros: ContaPagarFiltros = {},
): Promise<ContaReceberListagem> {
  const params = Object.fromEntries(
    Object.entries(filtros).filter(([, v]) => v !== undefined && v !== '' && v !== null),
  );
  const { data } = await api.get('/financeiro/contas-receber', { params });
  return safeParseResponse(ContaReceberListagemSchema, data, 'listarContasReceber');
}

export async function criarContaReceber(payload: ContaReceberPayload): Promise<ContaReceber> {
  const { data } = await api.post('/financeiro/contas-receber', payload);
  return safeParseResponse(ContaReceberSchema, data, 'criarContaReceber');
}

export async function atualizarContaReceber(
  id: number,
  payload: Partial<ContaReceberPayload>,
): Promise<ContaReceber> {
  const { data } = await api.patch(`/financeiro/contas-receber/${id}`, payload);
  return safeParseResponse(ContaReceberSchema, data, 'atualizarContaReceber');
}

export async function cancelarContaReceber(id: number): Promise<ContaReceber> {
  const { data } = await api.delete(`/financeiro/contas-receber/${id}`);
  return safeParseResponse(ContaReceberSchema, data, 'cancelarContaReceber');
}

export async function receberConta(
  id: number,
  payload: ContaReceberBaixaPayload,
): Promise<ContaReceber> {
  const { data } = await api.post(`/financeiro/contas-receber/${id}/receber`, payload);
  return safeParseResponse(ContaReceberSchema, data, 'receberConta');
}

export async function estornarRecebimento(id: number, motivo: string): Promise<ContaReceber> {
  const { data } = await api.post(`/financeiro/contas-receber/${id}/estornar`, { motivo });
  return safeParseResponse(ContaReceberSchema, data, 'estornarRecebimento');
}
