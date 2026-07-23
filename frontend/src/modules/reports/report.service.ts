import api from '@/api/axios';
import { safeParseResponse } from '@/shared/utils/parse.utils';
import {
  RelatorioFaturamentoSchema,
  type RelatorioFaturamento,
} from './schemas/faturamento.schema';
import { RelatorioRankingSchema, type RelatorioRanking } from './schemas/ranking.schema';

/**
 * Faturamento (vendas + OS finalizadas) no intervalo [inicio, fim].
 * Datas em formato YYYY-MM-DD.
 */
export async function getFaturamento(inicio: string, fim: string): Promise<RelatorioFaturamento> {
  const { data } = await api.get('/relatorios/faturamento', { params: { inicio, fim } });
  return safeParseResponse(RelatorioFaturamentoSchema, data, 'getFaturamento');
}

/** Ranking de funcionários por faturamento (vendas + OS) no intervalo. */
export async function getRanking(inicio: string, fim: string): Promise<RelatorioRanking> {
  const { data } = await api.get('/relatorios/ranking-funcionarios', { params: { inicio, fim } });
  return safeParseResponse(RelatorioRankingSchema, data, 'getRanking');
}
