import { useMutation, useQueryClient } from '@tanstack/vue-query';
import type { AxiosError } from 'axios';

import { useToast } from '@/shared/composables/useToast';
import { invalidarRelatorios } from '@/shared/utils/invalidarRelatorios';
import { getErrorMessage } from '@/shared/utils/error.utils';
import type { ApiError } from '@/shared/types/axios.types';

import { saleService } from '../../api.service';
import { saleKeys } from '../../query.keys';

import { SaleRead } from '../../schemas/sale.schema';

export function useCancelSaleMutation() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation<SaleRead, AxiosError<ApiError>, { saleId: number; motivo: string; codigoGerente?: string }>({
    mutationFn: ({ saleId, motivo, codigoGerente }) => saleService.cancelSale(saleId, motivo, codigoGerente),
    onSuccess: (canceledSale) => {
      toast.success('Venda cancelada');
      queryClient.invalidateQueries({
        queryKey: saleKeys.draft(canceledSale.id),
      });
      queryClient.setQueryData(saleKeys.detail(canceledSale.id), canceledSale);
      queryClient.invalidateQueries({
        queryKey: saleKeys.lists(),
      });
      queryClient.invalidateQueries({
        queryKey: saleKeys.status(),
      });
      invalidarRelatorios(queryClient);
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Erro ao cancelar venda'));
    },
  });
}
