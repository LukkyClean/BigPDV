import { computed, unref, type MaybeRef } from 'vue';
import { keepPreviousData, useQuery } from '@tanstack/vue-query';

import { fiscalService } from '../services/fiscal.service';
import { fiscalKeys, FISCAL_STALE_TIME, FISCAL_REFETCH_INTERVAL } from '../constants/fiscal.constants';
import type { DocumentoFiscalFilters } from '../types/fiscal.types';

export function useFiscalDocumentosQuery(
  filters: MaybeRef<DocumentoFiscalFilters>,
  pagina: MaybeRef<number>,
) {
  return useQuery({
    queryKey: computed(() => fiscalKeys.documentos(unref(filters), unref(pagina))),
    queryFn: () => fiscalService.listarDocumentos(unref(filters), unref(pagina)),
    staleTime: FISCAL_STALE_TIME,
    refetchInterval: FISCAL_REFETCH_INTERVAL,
    placeholderData: keepPreviousData,
  });
}
