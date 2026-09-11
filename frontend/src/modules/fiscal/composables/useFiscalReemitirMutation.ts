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
      // A reemissão vai à SEFAZ na hora (é a emissão da mesma origem, de novo),
      // e o documento volta com o desfecho. O toast diz qual foi — o mesmo
      // clique pode terminar autorizado, recusado de novo ou sem resposta.
      const numero = novoDoc.numero_documento ?? novoDoc.id;
      switch (novoDoc.status) {
        case 'AUTORIZADA':
          toast.success(`Nota nº ${numero} autorizada pela SEFAZ.`);
          break;
        case 'PROCESSANDO':
          toast.info(`Nota nº ${numero} enviada. Aguardando a SEFAZ.`);
          break;
        case 'INDETERMINADA':
          toast.warning(
            `Nota nº ${numero} sem resposta confirmada.`,
            'A SEFAZ será consultada de novo automaticamente. Não reemita antes disso.',
          );
          break;
        default:
          toast.error(
            `Nota nº ${numero} ${novoDoc.status.toLowerCase()} de novo.`,
            novoDoc.mensagem_sefaz ?? 'Veja o motivo nos detalhes do documento.',
          );
      }
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
