import api from '@/api/axios';
import { safeParseResponse } from '@/shared/utils/parse.utils';
import {
  RelatorioFaturamentoSchema,
  type RelatorioFaturamento,
} from './schemas/faturamento.schema';

/**
 * Faturamento (vendas + OS finalizadas) no intervalo [inicio, fim].
 * Datas em formato YYYY-MM-DD.
 */
export async function getFaturamento(inicio: string, fim: string): Promise<RelatorioFaturamento> {
  const { data } = await api.get('/relatorios/faturamento', { params: { inicio, fim } });
  return safeParseResponse(RelatorioFaturamentoSchema, data, 'getFaturamento');
}
