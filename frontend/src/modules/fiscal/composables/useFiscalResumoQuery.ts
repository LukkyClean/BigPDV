import { keepPreviousData, useQuery } from '@tanstack/vue-query';

import { fiscalService } from '../services/fiscal.service';
import { fiscalKeys, FISCAL_STALE_TIME, FISCAL_REFETCH_INTERVAL } from '../constants/fiscal.constants';
import type { DocumentoFiscalTipo } from '../types/fiscal.types';

/**
 * Contadores por status. `tipo` restringe a um modelo — a tela da NFC-e não
 * pode somar NF-e nos seus cartões.
 */
export function useFiscalResumoQuery(tipo?: DocumentoFiscalTipo) {
  return useQuery({
    queryKey: fiscalKeys.resumo(tipo),
    queryFn: () => fiscalService.obterResumo(tipo),
    staleTime: FISCAL_STALE_TIME,
    refetchInterval: FISCAL_REFETCH_INTERVAL,
    placeholderData: keepPreviousData,
  });
}
