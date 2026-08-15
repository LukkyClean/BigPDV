import api from '@/api/axios'

interface ChecklistTokenResponse {
  url: string
  token: string
}

export async function getChecklistQrUrl(
  osNumber: string,
): Promise<ChecklistTokenResponse> {
  const { data } = await api.get<ChecklistTokenResponse>(
    `/checklist/token/${osNumber}`,
  )
  return data
}
