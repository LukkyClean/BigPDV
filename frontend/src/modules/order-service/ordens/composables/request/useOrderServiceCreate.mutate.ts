import { useMutation, useQueryClient } from '@tanstack/vue-query';
import { AxiosError } from 'axios';

import { ApiError } from '@/shared/types/axios.types';
import { getErrorMessage } from '@/shared/utils/error.utils';
import { useToast } from '@/shared/composables/useToast';
import {
  ORDER_SERVICE_QUERY_KEY,
  ORDER_SERVICE_STATS_QUERY_KEY,
} from '../../constants/core.constant';

import { createOrderService } from '../../services/orderServiceCreate.service';
import { createItemOS } from '../../services/orderServiceCreate.service';

import { OrderServiceCreateSchemaDataType } from '../../schemas/orderServiceMutate.schema';
import { OrderServiceReadDataType } from '../../schemas/orderServiceQuery.schema';

import { OsItemCreateRequest } from '../../types/requests.type';
import { REVISOES_PENDENTES_QUERY_KEY } from '../../../shared/constants/queryKeys';

export function useCreateOrderServiceMutation() {
  const toast = useToast();
  const queryClient = useQueryClient();

  return useMutation<
    OrderServiceReadDataType,
    AxiosError<ApiError>,
    OrderServiceCreateSchemaDataType
  >({
    mutationFn: createOrderService,
    onSuccess: (data) => {
      toast.success(`${data.numero_os} cadastrada com sucesso!`);
      queryClient.invalidateQueries({ queryKey: [ORDER_SERVICE_QUERY_KEY] });
      queryClient.invalidateQueries({ queryKey: [ORDER_SERVICE_STATS_QUERY_KEY] });
      // A OS carrega o KM de entrada do veículo, e é ele que decide se uma
      // revisão por KM venceu. Sem invalidar aqui, o veículo só aparecia na aba
      // e no sino depois de recarregar a página.
      queryClient.invalidateQueries({ queryKey: REVISOES_PENDENTES_QUERY_KEY });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Erro ao cadastrar ordem de serviço') as string);
    },
  });
}

export function useCreateItemOSMutation() {
  const toast = useToast();
  const queryClient = useQueryClient();

  return useMutation<OrderServiceReadDataType, AxiosError<ApiError>, OsItemCreateRequest>({
    mutationFn: createItemOS,
    onSuccess: (data) => {
      const lastItem = data.itens[data.itens.length - 1];
      const itemType = lastItem?.tipo === 'PRODUTO' ? 'Produto' : 'Serviço';
      toast.success(`${itemType} adicionado com sucesso na ${data.numero_os}`);
      queryClient.invalidateQueries({ queryKey: [ORDER_SERVICE_QUERY_KEY] });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Erro ao adicionar item na ordem de serviço') as string);
    },
  });
}
