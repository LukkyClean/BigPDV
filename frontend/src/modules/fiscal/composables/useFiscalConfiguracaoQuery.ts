import { keepPreviousData, useQuery } from '@tanstack/vue-query';

import { fiscalService } from '../services/fiscal.service';
import { fiscalKeys, FISCAL_STALE_TIME } from '../constants/fiscal.constants';

/**
 * @param options.enabled Desligue quando o módulo fiscal não estiver liberado —
 *   o backend recusa `/fiscal/configuracao` com 403 e a chamada só gera ruído.
 *   Default `true` para não alterar os consumidores existentes.
 */
export function useFiscalConfiguracaoQuery(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: fiscalKeys.configuracao(),
    queryFn: () => fiscalService.obterConfiguracao(),
    staleTime: FISCAL_STALE_TIME,
    placeholderData: keepPreviousData,
    enabled: options.enabled ?? true,
  });
}
