import { useQuery } from '@tanstack/vue-query'

import { getPaymentMethodsAll } from '@/shared/services/paymentMethods.service'
import { REFETCH_CADASTROS } from '@/core/config/queryIntervals'

export const FORMAS_PAGAMENTO_KEY = 'formas-pagamento'

/**
 * O catálogo de formas de pagamento, para a tela que declara o prazo de cada uma.
 *
 * Traz TODAS, inclusive as inativas: uma forma desativada continua tendo
 * cobranças antigas penduradas nela, e esconder o prazo dela deixaria o dono
 * sem entender de onde vem uma previsão que ele ainda vê no Fluxo de Caixa.
 */
export function useFormasPagamentoQuery() {
  return useQuery({
    queryKey: [FORMAS_PAGAMENTO_KEY],
    queryFn: getPaymentMethodsAll,
    staleTime: REFETCH_CADASTROS,
  })
}
