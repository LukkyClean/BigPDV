export type TipoDano = 'amassado' | 'risco' | 'quebrado' | 'ferrugem' | 'outro'

export interface MarcaDano {
  id: string
  x: number           // 0-100 (% da largura da imagem)
  y: number           // 0-100 (% da altura da imagem)
  tipo: TipoDano
  observacao?: string
}

export const TIPOS_DANO: { value: TipoDano; label: string; cor: string }[] = [
  { value: 'amassado', label: 'Amassado', cor: '#f97316' },
  { value: 'risco', label: 'Risco', cor: '#eab308' },
  { value: 'quebrado', label: 'Quebrado', cor: '#ef4444' },
  { value: 'ferrugem', label: 'Ferrugem', cor: '#92400e' },
  { value: 'outro', label: 'Outro', cor: '#6b7280' },
]

export function corPorTipo(tipo: TipoDano): string {
  return TIPOS_DANO.find((t) => t.value === tipo)?.cor ?? '#6b7280'
}
