import { useMutation, useQueryClient } from '@tanstack/vue-query';
import type { AxiosError } from 'axios';

import { useToast } from '@/shared/composables/useToast';
import { getErrorMessage, getConflictErrors, isConflictError } from '@/shared/utils/error.utils';
import type { ApiError } from '@/shared/types/axios.types';

import { createServico, updateServico, toggleServicoAtivo } from '../services/servicos.service';
import { SERVICOS_QUERY_KEY } from '../constants/servicos.constants';
import type { ServiceCreateZod, ServiceUpdateZod, ServiceReadZod } from '../schemas/servicos.schema';

export function useCreateServicoMutation(setErrors?: (errors: Record<string, string>) => void) {
  const toast = useToast();
  const queryClient = useQueryClient();

  return useMutation<ServiceReadZod, AxiosError<ApiError>, ServiceCreateZod>({
    mutationFn: createServico,
    onSuccess: () => {
      toast.success('Serviço cadastrado com sucesso!');
      // Prefixo canônico: alcança o catálogo, as stats e a busca do item da OS.
      queryClient.invalidateQueries({ queryKey: [SERVICOS_QUERY_KEY] });
    },
    onError: (error) => {
      if (isConflictError(error) && setErrors) {
        const conflictErrors = getConflictErrors(error);
        if (conflictErrors) {
          setErrors(conflictErrors);
          toast.error('Erro ao cadastrar serviço', 'Dados já registrados');
          return;
        }
      }
      toast.error(getErrorMessage(error, 'Erro ao cadastrar serviço') as string);
    },
  });
}

export function useUpdateServicoMutation(setErrors?: (errors: Record<string, string>) => void) {
  const toast = useToast();
  const queryClient = useQueryClient();

  return useMutation<ServiceReadZod, AxiosError<ApiError>, { id: number; data: ServiceUpdateZod }>({
    mutationFn: ({ id, data }) => updateServico(id, data),
    onSuccess: () => {
      toast.success('Serviço atualizado com sucesso!');
      // Prefixo canônico: alcança o catálogo, as stats e a busca do item da OS.
      queryClient.invalidateQueries({ queryKey: [SERVICOS_QUERY_KEY] });
    },
    onError: (error) => {
      if (isConflictError(error) && setErrors) {
        const conflictErrors = getConflictErrors(error);
        if (conflictErrors) {
          setErrors(conflictErrors);
          toast.error('Erro ao atualizar serviço', 'Dados já registrados');
          return;
        }
      }
      toast.error(getErrorMessage(error, 'Erro ao atualizar serviço') as string);
    },
  });
}

export function useToggleServicoAtivoMutation() {
  const toast = useToast();
  const queryClient = useQueryClient();

  return useMutation<ServiceReadZod, AxiosError<ApiError>, number>({
    mutationFn: toggleServicoAtivo,
    onSuccess: (data) => {
      const status = data.ativo ? 'ativado' : 'desativado';
      toast.success(`Serviço ${status} com sucesso!`);
      // Prefixo canônico: alcança o catálogo, as stats e a busca do item da OS.
      queryClient.invalidateQueries({ queryKey: [SERVICOS_QUERY_KEY] });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Erro ao alterar status do serviço') as string);
    },
  });
}
