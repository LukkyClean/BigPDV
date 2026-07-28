import { useMutation, useQueryClient } from '@tanstack/vue-query';
import { AxiosError } from 'axios';

import type { ApiError } from '@/shared/types/axios.types';
import type { UserResponse } from '@/shared/types/auth.types';
import type { AtualizarContaPayload } from '../../services/minhaConta.service';
import { atualizarConta } from '../../services/minhaConta.service';
import { useToast } from '@/shared/composables/useToast';
import { getErrorMessage } from '@/shared/utils/error.utils';

export function useAtualizarContaMutation() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation<UserResponse, AxiosError<ApiError>, AtualizarContaPayload>({
    mutationFn: atualizarConta,
    onSuccess: (usuarioAtualizado) => {
      toast.success('Informações atualizadas!', 'Seus dados de usuário foram salvos com sucesso.');
      // Mesclamos só nome/email: a resposta do PATCH traz o modelo cru, sem o
      // cargo.permissoes montado (feito só no GET /me). Sobrescrever o objeto
      // inteiro zeraria as permissões e esvaziaria a sidebar.
      const anterior = queryClient.getQueryData<UserResponse>(['user-me']);
      if (anterior) {
        queryClient.setQueryData<UserResponse>(['user-me'], {
          ...anterior,
          nome: usuarioAtualizado.nome,
          email: usuarioAtualizado.email,
        });
      } else {
        queryClient.invalidateQueries({ queryKey: ['user-me'] });
      }
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Erro ao atualizar dados') as string);
    },
  });
}
