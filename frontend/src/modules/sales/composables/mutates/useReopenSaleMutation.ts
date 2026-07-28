import { useMutation, useQueryClient } from "@tanstack/vue-query";
import type { AxiosError } from "axios";

import { useToast } from "@/shared/composables/useToast";
import { getErrorMessage } from "@/shared/utils/error.utils";
import { invalidarRelatorios } from "@/shared/utils/invalidarRelatorios";
import type { ApiError } from "@/shared/types/axios.types";

import { saleService } from "../../api.service";
import { saleKeys } from "../../query.keys";

import { SaleRead } from "../../schemas/sale.schema";

const PIN_CODES = ['REQUER_APROVACAO_GERENTE', 'PIN_GERENTE_INVALIDO'];

export function useReopenSaleMutation() {
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation<SaleRead, AxiosError<ApiError>, { saleId: number; codigoGerente?: string }>({
        mutationFn: ({ saleId, codigoGerente }) => saleService.reopenSale(saleId, codigoGerente),
        onSuccess: (reopenedSale) => {
            toast.success('Venda reaberta com sucesso');
            queryClient.setQueryData(saleKeys.draft(reopenedSale.id), reopenedSale);
            queryClient.invalidateQueries({
              queryKey: saleKeys.lists(),
            });
            queryClient.invalidateQueries({
              queryKey: saleKeys.status(),
            });
            invalidarRelatorios(queryClient);
        },
        onError: (error) => {
            const detail = (error?.response?.data as any)?.detail;
            if (PIN_CODES.includes(detail)) return;
            toast.error(getErrorMessage(error, 'Erro ao reabrir venda'));
        }
    })
}
