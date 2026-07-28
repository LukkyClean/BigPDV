import { useMutation, useQueryClient } from "@tanstack/vue-query";
import type { AxiosError } from "axios";

import { useToast } from "@/shared/composables/useToast";
import { getErrorMessage } from "@/shared/utils/error.utils";
import { invalidarRelatorios } from "@/shared/utils/invalidarRelatorios";
import type { ApiError } from "@/shared/types/axios.types";

import { saleService } from "../../api.service";
import { saleKeys } from "../../query.keys";

import { PaymentSaleCreate } from "../../schemas/paymentSale.schema";
import { SaleRead } from "../../schemas/sale.schema";

export function useFinishSaleMutation() {
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation<SaleRead, AxiosError<ApiError>, { saleId: number; payments: PaymentSaleCreate[]; acrescimo?: number }>({
        mutationFn: (variables) => saleService.finishSale(variables.saleId, variables.payments, variables.acrescimo ?? 0),
        onSuccess: (finishedSale) => {
          toast.success('Venda finalizada com sucesso');
          queryClient.invalidateQueries({
            queryKey: saleKeys.draft(finishedSale.id)
          });
          queryClient.setQueryData(saleKeys.detail(finishedSale.id), finishedSale);
          queryClient.invalidateQueries({
            queryKey: saleKeys.lists(),
          });
          queryClient.invalidateQueries({
            queryKey: saleKeys.status(),
          });
          invalidarRelatorios(queryClient);
        },
        onError: (error) => {
          toast.error(getErrorMessage(error, 'Erro ao finalizar venda'));
        }
    })
}