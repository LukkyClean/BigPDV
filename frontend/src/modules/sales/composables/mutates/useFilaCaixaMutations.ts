import { useMutation, useQueryClient } from "@tanstack/vue-query";
import type { AxiosError } from "axios";

import { useToast } from "@/shared/composables/useToast";
import { getErrorMessage } from "@/shared/utils/error.utils";
import type { ApiError } from "@/shared/types/axios.types";

import { saleService } from "../../api.service";
import { saleKeys } from "../../query.keys";

import { SaleRead } from "../../schemas/sale.schema";

/**
 * A fila do caixa: o atendente entrega a venda, o caixa recebe o dinheiro.
 *
 * Nenhuma das duas mexe em dinheiro nem em status — a venda continua ATIVA dos
 * dois lados. O que muda é o carimbo que separa, na lista, a venda pronta da
 * que ainda está sendo montada.
 *
 * Por isso `invalidarRelatorios` NÃO é chamado aqui, ao contrário do cancelar e
 * do reabrir: nada que os relatórios somam mudou. Invalidar à toa derrubaria as
 * telas de relatório a cada entrega de venda.
 *
 * As duas invalidam o prefixo `saleKeys.lists()` e a chave `status()`. A
 * segunda não é alcançada pela primeira — chave-irmã não é filha —, e é ela que
 * alimenta a contagem da fila.
 */
export function useEnviarAoCaixaMutation() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation<SaleRead, AxiosError<ApiError>, number>({
    mutationFn: (saleId) => saleService.enviarAoCaixa(saleId),
    onSuccess: (venda) => {
      toast.success('Venda enviada para o caixa');
      queryClient.setQueryData(saleKeys.draft(venda.id), venda);
      queryClient.invalidateQueries({ queryKey: saleKeys.lists() });
      queryClient.invalidateQueries({ queryKey: saleKeys.status() });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Não foi possível enviar a venda ao caixa'));
    },
  });
}

export function useDevolverParaMontagemMutation() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation<SaleRead, AxiosError<ApiError>, number>({
    mutationFn: (saleId) => saleService.devolverParaMontagem(saleId),
    onSuccess: (venda) => {
      toast.success('Venda devolvida para montagem');
      queryClient.setQueryData(saleKeys.draft(venda.id), venda);
      queryClient.invalidateQueries({ queryKey: saleKeys.lists() });
      queryClient.invalidateQueries({ queryKey: saleKeys.status() });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Não foi possível devolver a venda para montagem'));
    },
  });
}
