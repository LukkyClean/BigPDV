import { useQuery } from '@tanstack/vue-query'
import type { Ref } from 'vue'
import { listarBackups } from '../../services/backup.service'

export const BACKUP_LISTA_KEY = 'backup-lista'

export function useListarBackupsQuery(enabled: Ref<boolean>) {
  return useQuery({
    queryKey: [BACKUP_LISTA_KEY],
    queryFn: listarBackups,
    staleTime: 1000 * 60 * 2,
    enabled,
  })
}
