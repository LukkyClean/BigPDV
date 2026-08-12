import { useQuery } from '@tanstack/vue-query'
import { getUltimoBackup } from '../../services/backup.service'
import { REFETCH_CONFIG } from '@/core/config/queryIntervals'

export const BACKUP_ULTIMO_KEY = 'backup-ultimo'

export function useUltimoBackupQuery() {
  return useQuery({
    queryKey: [BACKUP_ULTIMO_KEY],
    queryFn: getUltimoBackup,
    staleTime: REFETCH_CONFIG,
    refetchInterval: REFETCH_CONFIG,
  })
}
