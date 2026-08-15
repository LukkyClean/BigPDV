import { useMutation, useQueryClient } from '@tanstack/vue-query'
import { AxiosError } from 'axios'
import { useToast } from '@/shared/composables/useToast'
import { criarBackup } from '../../services/backup.service'
import { BACKUP_ULTIMO_KEY } from '../queries/useUltimoBackupQuery'
import { BACKUP_LISTA_KEY } from '../queries/useListarBackupsQuery'
import type { BackupCriadoComCotaType } from '../../types/backup.types'
import type { ApiError } from '@/shared/types/axios.types'

export function useCriarBackupMutation() {
  const toast = useToast()
  const queryClient = useQueryClient()

  return useMutation<BackupCriadoComCotaType, AxiosError<ApiError>>({
    mutationFn: criarBackup,
    onSuccess: (data) => {
      toast.success('Backup criado com sucesso!', `Arquivo: ${data.arquivo}`)
      queryClient.invalidateQueries({ queryKey: [BACKUP_ULTIMO_KEY] })
      queryClient.invalidateQueries({ queryKey: [BACKUP_LISTA_KEY] })
    },
    onError: (error) => {
      const detail = error.response?.data?.detail
      if (detail === 'LIMITE_BACKUP_DIARIO') {
        toast.warning('Limite diário atingido', 'Você já realizou o máximo de backups manuais permitidos hoje.')
      } else {
        toast.error('Erro ao criar backup', 'Tente novamente mais tarde.')
      }
    },
  })
}
