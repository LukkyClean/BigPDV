import { useMutation, useQueryClient } from '@tanstack/vue-query';
import type { AxiosError } from 'axios';

import { useToast } from '@/shared/composables/useToast';
import { getErrorMessage } from '@/shared/utils/error.utils';
import type { ApiError } from '@/shared/types/axios.types';

import { fiscalService } from '../services/fiscal.service';
import { fiscalKeys } from '../constants/fiscal.constants';

export function useFiscalConsultarMutation() {
  const toast = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => fiscalService.consultarDocumento(id),
    onSuccess: (data) => {
      toast.success(`Documento atualizado: ${data.status}`);
      queryClient.invalidateQueries({ queryKey: fiscalKeys.documentos() });
      queryClient.invalidateQueries({ queryKey: fiscalKeys.resumo() });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error as AxiosError<ApiError>));
    },
  });
}
