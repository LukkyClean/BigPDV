export interface SegmentField {
  nome: string
  label: string
  tipo: 'texto' | 'numero' | 'inteiro' | 'opcao' | 'booleano'
  obrigatorio: boolean
  escopo: 'objeto' | 'os'
  opcoes?: string[]
}

export interface SegmentInspectionGroup {
  titulo: string
  estados: string[]
  itens: string[]
}

export interface SegmentDefinition {
  segmento: string
  rotulo_objeto_singular: string
  rotulo_objeto_plural: string
  identificador: { nome: string; label: string; regex: string | null }
  capacidades: string[]
  veiculo: SegmentField[]
  checkin: SegmentField[]
  acessorios: string[]
  vistoria: SegmentInspectionGroup[]
}

export interface ChecklistDados {
  numero_os: string
  placa: string | null
  marca: string | null
  modelo: string | null
  definicao: SegmentDefinition | null
  dados_adicionais: Record<string, unknown>
  /** Fotos anexadas à OS — na aprovação de arte, são o mockup que o cliente vê. */
  fotos?: string[]
  /** Identidade visual da loja — quem o cliente reconhece do outro lado do QR. */
  empresa_nome?: string | null
  cor_tema?: string | null
  url_logo?: string | null
}
