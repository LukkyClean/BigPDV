import { useMutation, useQueryClient } from '@tanstack/vue-query';
import { fiscalService } from '../services/fiscal.service';
import { fiscalKeys } from '../constants/fiscal.constants';
import type { FiscalConfiguracao } from '../types/fiscal.types';

export function useFiscalConfiguracaoMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: Partial<FiscalConfiguracao>) => fiscalService.atualizarConfiguracao(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: fiscalKeys.configuracao() });
    },
  });
}

