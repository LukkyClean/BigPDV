import { REFETCH_REALTIME } from '@/core/config/queryIntervals'

export const BASE_ORDER_SERVICE_URL = "/ordens-servico"
export const BASE_EMPLOYEE_OS_URL = "/funcionarios"
export const BASE_CUSTOMER_OS_URL = "/clientes"

export const ORDER_SERVICE_QUERY_KEY = "order-service-query"
export const ORDER_SERVICE_STATS_QUERY_KEY = "order-service-stats-query"
export const ORDER_SERVICE_QUERY_STALE_TIME = 1000 * 60

export const OS_EMPLOYEE_QUERY_KEY = "os-employee-query"
export const OS_EMPLOYEE_QUERY_STALE_TIME = 1000 * 60

export const OS_CUSTOMER_QUERY_KEY = "os-customer-query"
export const OS_CUSTOMER_QUERY_STALE_TIME = 1000 * 60

// Definição de campos por segmento (metadados): muda raramente -> stale time longo.
export const OS_FIELD_DEFINITION_QUERY_KEY = "os-field-definition-query"
export const OS_FIELD_DEFINITION_STALE_TIME = 1000 * 60 * 30

export const ORDER_SERVICE_REFETCH_INTERVAL = REFETCH_REALTIME

export const DEFAULT_OS_CREATE_VALUES = {
  prioridade: 'NORMAL' as const,
  defeito_relatado: '',
  diagnostico: undefined,
  solucao: undefined,
  senha_aparelho: undefined,
  acessorios: undefined,
  condicoes_aparelho: undefined,
  observacoes: undefined,
  desconto: undefined,
  valor_entrada: 0,
  garantia: undefined,
  data_previsao: undefined,
  cliente_id: undefined,
  funcionario_id: undefined,
  objeto: {
    tipo_equipamento: undefined,
    marca: '',
    modelo: '',
    numero_serie: '',
    imei: '',
    cor: undefined,
    proxima_revisao_data: undefined,
    proxima_revisao_km: undefined,
    dados_adicionais: {} as Record<string, unknown>,
  },
  // Check-in dinâmico no nível da OS (km_entrada, combustível, vistoria)
  dados_adicionais: {} as Record<string, unknown>,
  itens: [] as never[],
}

export const DEFAULT_OS_ITEM_VALUES = {
  tipo: 'SERVICO' as const,
  nome: '',
  unidade_medida: 'UN' as const,
  quantidade: 1,
  valor_unitario: 0,
}

/** Medidas para SERVIÇO: tempo e unidade */
export const MEDIDA_SERVICO_OPTIONS = [
  { value: 'UN', label: 'Unidade (UN)' },
  { value: 'H', label: 'Hora (H)' },
  { value: 'D', label: 'Dia (D)' },
  { value: 'MES', label: 'Mês (MES)' },
  { value: 'OUTROS', label: 'Outros' },
] as const;

/** Medidas para PRODUTO: peso, volume, comprimento */
export const MEDIDA_PRODUTO_OPTIONS = [
  { value: 'UN', label: 'Unidade (UN)' },
  { value: 'KG', label: 'Quilograma (KG)' },
  { value: 'G', label: 'Grama (G)' },
  { value: 'L', label: 'Litro (L)' },
  { value: 'ML', label: 'Mililitro (ML)' },
  { value: 'M', label: 'Metro (M)' },
  { value: 'CM', label: 'Centímetro (CM)' },
  { value: 'M2', label: 'Metro² (M²)' },
  { value: 'M3', label: 'Metro³ (M³)' },
  { value: 'OUTROS', label: 'Outros' },
] as const;

export const DEFAULT_OS_PAGAMENTO_VALUES = {
  forma_pagamento_id: 0,
  valor: 0,
  parcelas: 1,
  bandeira_cartao: undefined,
  detalhes: undefined,
}