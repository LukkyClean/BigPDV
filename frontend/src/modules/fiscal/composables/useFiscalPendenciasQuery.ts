import { keepPreviousData, useQuery } from '@tanstack/vue-query';

import { fiscalService } from '../services/fiscal.service';
import { fiscalKeys } from '../constants/fiscal.constants';

export function useFiscalPendenciasQuery() {
  return useQuery({
    queryKey: fiscalKeys.pendencias(),
    queryFn: () => fiscalService.obterPendencias(),
    staleTime: 1000 * 60,
    placeholderData: keepPreviousData,
  });
}
