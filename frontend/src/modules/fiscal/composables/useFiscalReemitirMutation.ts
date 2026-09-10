import { useMutation, useQueryClient } from '@tanstack/vue-query';
import type { AxiosError } from 'axios';

import { useToast } from '@/shared/composables/useToast';
import { getErrorMessage } from '@/shared/utils/error.utils';
import type { ApiError } from '@/shared/types/axios.types';

import { fiscalService } from '../services/fiscal.service';
import { fiscalKeys } from '../constants/fiscal.constants';

export function useFiscalReemitirMutation() {
  const toast = useToast();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (documentoId: number) => fiscalService.reemitirDocumento(documentoId),
    onSuccess: (novoDoc) => {
      // "criada para reemissão" ainda sugeria que a transmissão viria sozinha.
      // Nao vem: a linha nasce PENDENTE e so sai quando alguem manda emitir.
      toast.success(
        `Nova tentativa #${novoDoc.numero_documento ?? novoDoc.id} criada. Emita para transmitir.`,
      );
      queryClient.invalidateQueries({ queryKey: fiscalKeys.documentos() });
      queryClient.invalidateQueries({ queryKey: fiscalKeys.resumo() });
      queryClient.invalidateQueries({ queryKey: fiscalKeys.historico(novoDoc.id) });
      if (novoDoc.tentativa_anterior_id) {
        queryClient.invalidateQueries({ queryKey: fiscalKeys.historico(novoDoc.tentativa_anterior_id) });
      }
    },
    onError: (error) => {
      toast.error(getErrorMessage(error as AxiosError<ApiError>));
    },
  });
}
