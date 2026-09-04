import { keepPreviousData, useQuery } from '@tanstack/vue-query';

import { fiscalService } from '../services/fiscal.service';
import { fiscalKeys, FISCAL_STALE_TIME } from '../constants/fiscal.constants';

export function useFiscalConfiguracaoQuery() {
  return useQuery({
    queryKey: fiscalKeys.configuracao(),
    queryFn: () => fiscalService.obterConfiguracao(),
    staleTime: FISCAL_STALE_TIME,
    placeholderData: keepPreviousData,
  });
}
