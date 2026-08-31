import { useMutation } from '@tanstack/vue-query';
import type { AxiosError } from 'axios';
import { useToast } from '@/shared/composables/useToast';
import { getErrorMessage } from '@/shared/utils/error.utils';
import type { ApiError } from '@/shared/types/axios.types';
import { fiscalService } from '../services/fiscal.service';
import type { EmissaoNFeRequest } from '../types/fiscal.types';

export function useFiscalPreviewMutation() {
  const toast = useToast();

  return useMutation({
    mutationFn: (payload: EmissaoNFeRequest) => fiscalService.previewNfe(payload),
    onError: (error) => {
      toast.error(getErrorMessage(error as AxiosError<ApiError>));
    },
  });
}
