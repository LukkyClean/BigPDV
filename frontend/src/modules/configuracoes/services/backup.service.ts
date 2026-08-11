import api from '@/api/axios'
import type {
  BackupInfoType,
  BackupCriadoComCotaType,
  CicloNuvemInfoType,
  ConfiguracaoBackupType,
  ConfiguracaoBackupUpdateType,
  PrepareRestoreResponseType,
  ConfirmRestoreResponseType,
  DownloadChainResponseType,
} from '../types/backup.types'

const BASE_URL = '/backup'

export async function listarBackups(): Promise<BackupInfoType[]> {
  const response = await api.get<BackupInfoType[]>(`${BASE_URL}/`)
  return response.data
}

export async function getUltimoBackup(): Promise<BackupInfoType | null> {
  const response = await api.get<BackupInfoType>(`${BASE_URL}/ultimo`, {
    validateStatus: (status) => status === 200 || status === 204,
  })
  if (response.status === 204) return null
  return response.data
}

export async function criarBackup(): Promise<BackupCriadoComCotaType> {
  const response = await api.post<BackupCriadoComCotaType>(`${BASE_URL}/criar`, null, {
    timeout: 120_000,
  })
  return response.data
}

export async function getConfiguracaoBackup(): Promise<ConfiguracaoBackupType> {
  const response = await api.get<ConfiguracaoBackupType>(`${BASE_URL}/configuracao`)
  return response.data
}

export async function updateConfiguracaoBackup(
  data: ConfiguracaoBackupUpdateType,
): Promise<ConfiguracaoBackupType> {
  const response = await api.put<ConfiguracaoBackupType>(`${BASE_URL}/configuracao`, data)
  return response.data
}

export async function listarCiclosNuvem(): Promise<CicloNuvemInfoType[]> {
  const response = await api.get<CicloNuvemInfoType[]>(`${BASE_URL}/ciclos-nuvem`)
  return response.data
}

export async function baixarBackupNuvem(ciclo: string): Promise<DownloadChainResponseType> {
  const response = await api.get<DownloadChainResponseType>(`${BASE_URL}/download/${ciclo}`)
  return response.data
}

export async function prepararRestauracao(ciclo: string): Promise<PrepareRestoreResponseType> {
  const response = await api.post<PrepareRestoreResponseType>(
    `${BASE_URL}/preparar-restauracao/${ciclo}`,
  )
  return response.data
}

export async function confirmarRestauracao(
  ciclo: string,
  preRestoreBackup: string,
): Promise<ConfirmRestoreResponseType> {
  const response = await api.post<ConfirmRestoreResponseType>(
    `${BASE_URL}/confirmar-restauracao/${ciclo}`,
    null,
    { params: { pre_restore_backup: preRestoreBackup } },
  )
  return response.data
}
