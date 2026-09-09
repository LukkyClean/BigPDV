import { computed, type MaybeRefOrGetter, toValue } from 'vue';
import { useQuery } from '@tanstack/vue-query';

import { fiscalService } from '../services/fiscal.service';
import { fiscalKeys } from '../constants/fiscal.constants';

/**
 * O que a plataforma de emissão enxerga desta licença.
 *
 * `staleTime` curto de propósito: isto é uma ferramenta de diagnóstico, e quem
 * a abre está justamente conferindo se algo mudou do outro lado depois de o
 * suporte mexer. Cache longo aqui faria o operador ver o estado anterior e
 * concluir que o ajuste não funcionou.
 *
 * Sem `retry`: a rota já trata a indisponibilidade como resposta válida
 * (`consultou: false`). Tentar de novo só atrasaria a tela para chegar à mesma
 * informação.
 */
export function useFiscalPlataformaQuery(enabled?: MaybeRefOrGetter<boolean>) {
  return useQuery({
    queryKey: fiscalKeys.plataforma(),
    queryFn: () => fiscalService.obterDiagnosticoPlataforma(),
    staleTime: 1000 * 5,
    retry: false,
    enabled: computed(() => (enabled === undefined ? true : toValue(enabled))),
  });
}
