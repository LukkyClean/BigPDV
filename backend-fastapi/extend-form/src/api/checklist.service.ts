import api from './axios'
import type { ChecklistDados } from '../types/checklist.types'

export async function getChecklistData(
  osNumber: string,
  token: string,
): Promise<ChecklistDados> {
  const { data } = await api.get<ChecklistDados>(
    `/checklist/dados/${osNumber}`,
    { params: { token } },
  )
  return data
}

export async function saveChecklistData(
  osNumber: string,
  token: string,
  dadosAdicionais: Record<string, unknown>,
): Promise<ChecklistDados> {
  const { data } = await api.put<ChecklistDados>(
    `/checklist/dados/${osNumber}`,
    { dados_adicionais: dadosAdicionais },
    { params: { token } },
  )
  return data
}
