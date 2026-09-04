import { useMutation, useQueryClient } from '@tanstack/vue-query';
import type { AxiosError } from 'axios';

import { useToast } from '@/shared/composables/useToast';
import { getErrorMessage } from '@/shared/utils/error.utils';
import type { ApiError } from '@/shared/types/axios.types';

import { fiscalService } from '../services/fiscal.service';
import { fiscalKeys } from '../constants/fiscal.constants';

export function useFiscalEmitirBatchMutation() {
  const toast = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (vendaIds: number[]) => fiscalService.emitirNfeBatch(vendaIds),
    onSuccess: (data) => {
      if (data.falha === 0) {
        toast.success(`${data.sucesso} NF-e(s) emitida(s) com sucesso.`);
      } else if (data.sucesso > 0) {
        toast.warning(
          'Emissão parcial',
          `${data.sucesso} sucesso, ${data.falha} falha(s).`,
        );
      } else {
        toast.error(`Falha ao emitir ${data.falha} NF-e(s).`);
      }
      queryClient.invalidateQueries({ queryKey: fiscalKeys.documentos() });
      queryClient.invalidateQueries({ queryKey: fiscalKeys.resumo() });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error as AxiosError<ApiError>));
    },
  });
}
