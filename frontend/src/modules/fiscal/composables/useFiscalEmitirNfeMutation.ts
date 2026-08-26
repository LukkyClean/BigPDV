import { useMutation, useQueryClient } from '@tanstack/vue-query';
import type { AxiosError } from 'axios';

import { useToast } from '@/shared/composables/useToast';
import { getErrorMessage } from '@/shared/utils/error.utils';
import type { ApiError } from '@/shared/types/axios.types';

import { fiscalService } from '../services/fiscal.service';
import { fiscalKeys } from '../constants/fiscal.constants';
import type { EmissaoNFeRequest } from '../types/fiscal.types';

export function useFiscalEmitirNfeMutation() {
  const toast = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: EmissaoNFeRequest) => fiscalService.emitirNfe(payload),
    onSuccess: (data) => {
      toast.success(data.mensagem || 'NF-e emitida com sucesso.');
      queryClient.invalidateQueries({ queryKey: fiscalKeys.documentos() });
      queryClient.invalidateQueries({ queryKey: fiscalKeys.resumo() });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error as AxiosError<ApiError>));
    },
  });
}
