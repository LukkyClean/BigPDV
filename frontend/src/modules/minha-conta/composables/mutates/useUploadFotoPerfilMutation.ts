import { useMutation, useQueryClient } from '@tanstack/vue-query';
import { AxiosError } from 'axios';

import type { ApiError } from '@/shared/types/axios.types';
import type { UserResponse } from '@/shared/types/auth.types';
import { uploadFotoPerfil } from '../../services/minhaConta.service';
import { useToast } from '@/shared/composables/useToast';
import { getErrorMessage } from '@/shared/utils/error.utils';

export function useUploadFotoPerfilMutation() {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation<UserResponse, AxiosError<ApiError>, File>({
    mutationFn: uploadFotoPerfil,
    onSuccess: (usuarioAtualizado) => {
      toast.success('Foto atualizada com sucesso!');
      // Só o url_perfil desta resposta é confiável: cargo/permissões vêm
      // incompletos aqui (são montados apenas no GET /me). Por isso mesclamos
      // apenas o campo alterado no cache — sobrescrever o objeto inteiro
      // zerava cargo.permissoes e esvaziava a sidebar. Atualizar direto no
      // cache (sem refetch) evita o cache do webview que exigia reload manual.
      const anterior = queryClient.getQueryData<UserResponse>(['user-me']);
      if (anterior) {
        queryClient.setQueryData<UserResponse>(['user-me'], {
          ...anterior,
          url_perfil: usuarioAtualizado.url_perfil,
        });
      } else {
        queryClient.invalidateQueries({ queryKey: ['user-me'] });
      }
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Erro ao atualizar foto') as string);
    },
  });
}
