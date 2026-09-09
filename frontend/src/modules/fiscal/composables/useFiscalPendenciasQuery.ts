import { computed, type MaybeRefOrGetter, toValue } from 'vue';
import { keepPreviousData, useQuery } from '@tanstack/vue-query';

import { fiscalService } from '../services/fiscal.service';
import { fiscalKeys } from '../constants/fiscal.constants';

/**
 * Pendências fiscais globais do cadastro (emitente, produtos, serviços, pagamentos).
 *
 * O `enabled` existe para quem pergunta de FORA do Centro Fiscal — hoje a tela
 * de Empresa. O router inteiro de `/fiscal` exige o módulo NFE
 * (`requer_modulo("NFE")`), então perguntar sem o módulo não devolve lista
 * vazia: devolve 403. Numa tela que a loja SEM NF-e abre todo dia, isso seria
 * um erro no console a cada visita, para nada.
 *
 * Sem argumento o comportamento é o de antes — ligado.
 */
export function useFiscalPendenciasQuery(enabled?: MaybeRefOrGetter<boolean>) {
  return useQuery({
    queryKey: fiscalKeys.pendencias(),
    queryFn: () => fiscalService.obterPendencias(),
    staleTime: 1000 * 60,
    placeholderData: keepPreviousData,
    enabled: computed(() => (enabled === undefined ? true : toValue(enabled))),
  });
}
