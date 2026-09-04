import { computed, type MaybeRef, unref } from 'vue';
import { useQuery } from '@tanstack/vue-query';
import { fiscalService } from '../services/fiscal.service';
import { fiscalKeys, FISCAL_STALE_TIME } from '../constants/fiscal.constants';
import type { ResultadoVerificacaoBatch } from '../types/fiscal.types';

export function useFiscalVerificacaoBatchQuery(vendaIds: MaybeRef<number[] | null>) {
  return useQuery<ResultadoVerificacaoBatch>({
    queryKey: computed(() => fiscalKeys.verificacaoBatch(unref(vendaIds) ?? [])),
    queryFn: () => fiscalService.verificarFiscalBatch(unref(vendaIds)!),
    enabled: computed(() => {
      const ids = unref(vendaIds);
      return !!ids && ids.length > 0;
    }),
    staleTime: FISCAL_STALE_TIME,
  });
}
