import { useMutation, useQueryClient } from '@tanstack/vue-query';
import type { AxiosError } from 'axios';

import { useToast } from '@/shared/composables/useToast';
import { getErrorMessage } from '@/shared/utils/error.utils';
import type { ApiError } from '@/shared/types/axios.types';

import { fiscalService } from '../services/fiscal.service';
import { fiscalKeys } from '../constants/fiscal.constants';
import type { EmissaoNFeRequest, FiscalConflictDetail } from '../types/fiscal.types';

export function useFiscalEmitirNfeMutation() {
  const toast = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: EmissaoNFeRequest) => fiscalService.emitirNfe(payload),
    onSuccess: (data) => {
      if (data.status === 'AUTORIZADA' || data.status === 'PROCESSANDO') {
        toast.success(data.mensagem || 'NF-e emitida com sucesso.');
      } else {
        toast.error(data.mensagem || 'Erro ao emitir NF-e.');
      }
      queryClient.invalidateQueries({ queryKey: fiscalKeys.documentos() });
      queryClient.invalidateQueries({ queryKey: fiscalKeys.resumo() });
    },
    onError: (error) => {
      const axiosErr = error as AxiosError<ApiError>;

      if (axiosErr.response?.status === 409) {
        const detail = axiosErr.response.data?.detail as FiscalConflictDetail | undefined;
        const msg = detail?.mensagem || 'Esta venda já possui documento fiscal ativo.';
        toast.warning('Documento fiscal existente', msg);
        queryClient.invalidateQueries({ queryKey: fiscalKeys.documentos() });
        queryClient.invalidateQueries({ queryKey: fiscalKeys.resumo() });
        return;
      }

      toast.error(getErrorMessage(axiosErr));
    },
  });
}
