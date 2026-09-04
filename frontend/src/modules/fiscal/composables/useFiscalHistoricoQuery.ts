import { Ref, computed } from 'vue';
import { useQuery } from '@tanstack/vue-query';
import { fiscalService } from '../services/fiscal.service';
import { fiscalKeys } from '../constants/fiscal.constants';

export function useFiscalHistoricoQuery(documentoId: Ref<number | null>) {
  return useQuery({
    queryKey: computed(() => [...fiscalKeys.documentos(), documentoId.value, 'historico']),
    queryFn: () => fiscalService.obterHistorico(documentoId.value!),
    enabled: computed(() => !!documentoId.value),
  });
}
