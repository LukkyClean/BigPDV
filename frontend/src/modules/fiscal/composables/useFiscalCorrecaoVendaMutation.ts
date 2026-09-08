import { useMutation, useQueryClient } from '@tanstack/vue-query';
import type { AxiosError } from 'axios';

import { useToast } from '@/shared/composables/useToast';
import { getErrorMessage } from '@/shared/utils/error.utils';
import type { ApiError } from '@/shared/types/axios.types';

import { fiscalService } from '../services/fiscal.service';
import { fiscalKeys } from '../constants/fiscal.constants';
import type { VendaCorrecaoFiscalPayload } from '../types/fiscal.types';

export function useFiscalCorrecaoVendaMutation() {
  const toast = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ vendaId, payload }: { vendaId: number; payload: VendaCorrecaoFiscalPayload }) =>
      fiscalService.corrigirVendaFiscal(vendaId, payload),
    onSuccess: () => {
      toast.success('Venda e dados fiscais atualizados com sucesso.');
      queryClient.invalidateQueries({ queryKey: fiscalKeys.documentos() });
      queryClient.invalidateQueries({ queryKey: fiscalKeys.resumo() });
      queryClient.invalidateQueries({ queryKey: fiscalKeys.all });
      queryClient.invalidateQueries({ queryKey: ['sales'] });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error as AxiosError<ApiError>));
    },
  });
}
