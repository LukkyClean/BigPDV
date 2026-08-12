import { useQuery } from '@tanstack/vue-query'
import { getConfiguracaoBackup } from '../../services/backup.service'
import { REFETCH_CONFIG } from '@/core/config/queryIntervals'

export const BACKUP_CONFIGURACAO_KEY = 'backup-configuracao'

export function useConfiguracaoBackupQuery() {
  return useQuery({
    queryKey: [BACKUP_CONFIGURACAO_KEY],
    queryFn: getConfiguracaoBackup,
    staleTime: REFETCH_CONFIG,
  })
}
