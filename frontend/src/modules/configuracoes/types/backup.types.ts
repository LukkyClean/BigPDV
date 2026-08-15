export interface BackupInfoType {
  arquivo: string
  criado_em: string
  tamanho_bytes: number
  completo: boolean
}

export interface BackupCriadoComCotaType {
  arquivo: string
  criado_em: string
  tamanho_bytes: number
  backups_restantes_hoje: number
}

export interface ConfiguracaoBackupType {
  id: number
  empresa_id: number
  backup_automatico_ativo: boolean
  frequencia: 'diario' | '8horas' | '12horas'
  horario: string
  data_atualizacao: string
}

export interface ConfiguracaoBackupUpdateType {
  backup_automatico_ativo?: boolean
  frequencia?: 'diario' | '8horas' | '12horas'
  horario?: string
}

export interface PrepareRestoreResponseType {
  status: 'restore_backup_outdated' | 'equals' | 'ready'
  details: string | null
  ciclo: string | null
  pre_restore_backup: string | null
}

export interface ConfirmRestoreResponseType {
  status: 'confirmed' | 'error'
  details: string | null
  ciclo: string | null
}

export interface CicloNuvemInfoType {
  ciclo: string
  quantidade_backups: number
  ultimo_envio: string
  arquivos: string[]
}

export interface DownloadChainResponseType {
  status: string
  details: string | null
  ciclo: string | null
  ordered_files: string[] | null
  restaura_ate: string | null
  cadeia_completa: boolean | null
  indisponiveis: string[] | null
  total_bytes: number | null
}
