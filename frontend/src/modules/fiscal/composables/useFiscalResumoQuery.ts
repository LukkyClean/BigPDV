import { keepPreviousData, useQuery } from '@tanstack/vue-query';

import { fiscalService } from '../services/fiscal.service';
import { fiscalKeys, FISCAL_STALE_TIME, FISCAL_REFETCH_INTERVAL } from '../constants/fiscal.constants';

export function useFiscalResumoQuery() {
  return useQuery({
    queryKey: fiscalKeys.resumo(),
    queryFn: () => fiscalService.obterResumo(),
    staleTime: FISCAL_STALE_TIME,
    refetchInterval: FISCAL_REFETCH_INTERVAL,
    placeholderData: keepPreviousData,
  });
}
