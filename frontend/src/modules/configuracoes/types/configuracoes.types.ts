import type { Component } from 'vue'

export type SecaoId =
  | 'seguranca'
  | 'regras-de-vendas'
  | 'gestao-financeira'
  | 'produtos-estoque'
  | 'ordens-de-servico'
  | 'clientes-cadastro'
  | 'integracoes-apis'
  | 'terminais'
  | 'impressao'
  | 'formatos-exibicao'
  | 'backup-dados'
  | 'suporte'

export interface SecaoConfiguracao {
  id: SecaoId
  label: string
  icone: Component
}

export interface SecaoExposta {
  form?: Record<string, unknown>
  isDirty?: boolean
  resetar?: () => void
}
