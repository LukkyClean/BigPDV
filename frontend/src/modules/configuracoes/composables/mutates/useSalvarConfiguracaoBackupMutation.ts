import { useMutation, useQueryClient } from '@tanstack/vue-query'
import { AxiosError } from 'axios'
import { useToast } from '@/shared/composables/useToast'
import { updateConfiguracaoBackup } from '../../services/backup.service'
import { BACKUP_CONFIGURACAO_KEY } from '../queries/useConfiguracaoBackupQuery'
import type { ConfiguracaoBackupType, ConfiguracaoBackupUpdateType } from '../../types/backup.types'
import type { ApiError } from '@/shared/types/axios.types'

export function useSalvarConfiguracaoBackupMutation() {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation<ConfiguracaoBackupType, AxiosError<ApiError>, ConfiguracaoBackupUpdateType>({
    mutationFn: updateConfiguracaoBackup,
    onSuccess: () => {
      toast.success('Configurações de backup salvas com sucesso!')
      queryClient.invalidateQueries({ queryKey: [BACKUP_CONFIGURACAO_KEY] })
    },
    onError: () => {
      toast.error('Erro ao salvar configurações de backup. Tente novamente.')
    },
  })
}
