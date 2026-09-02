import { useMutation, useQueryClient } from '@tanstack/vue-query'
import { AxiosError } from 'axios'

import { useToast } from '@/shared/composables/useToast'
import { updatePaymentMethod } from '@/shared/services/paymentMethods.service'
import type {
  PaymentFormReadDataType,
  PaymentFormUpdateDataType,
} from '@/shared/schemas/payments/payment.schema'
import type { ApiError } from '@/shared/types/axios.types'

import { FINANCEIRO_KEY } from '@/shared/constants/entityKeys'

import { FORMAS_PAGAMENTO_KEY } from '../queries/useFormasPagamentoQuery'

interface Variaveis {
  id: number
  dados: PaymentFormUpdateDataType
}

/**
 * Salva o prazo (e a conta de destino) de uma forma de pagamento.
 *
 * Invalida TAMBÉM as chaves do financeiro: mudar o prazo muda o que o Fluxo de
 * Caixa prevê para os próximos dias, e deixar aquela tela com o número antigo
 * seria pior que não ter salvado — o dono acharia que não pegou.
 */
export function useAtualizarFormaPagamentoMutation() {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation<PaymentFormReadDataType, AxiosError<ApiError>, Variaveis>({
    mutationFn: ({ id, dados }) => updatePaymentMethod(id, dados),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [FORMAS_PAGAMENTO_KEY] })
      queryClient.invalidateQueries({ queryKey: [FINANCEIRO_KEY] })
      toast.success('Forma de recebimento salva')
    },
    onError: (error) => {
      const detail = error.response?.data?.detail
      toast.error(
        'Não foi possível salvar',
        typeof detail === 'string' ? detail : 'Tente novamente.',
      )
    },
  })
}
