import type { OsStatusEnumDataType, OsPriorityEnumDataType, OsEquipTypeEnumDataType } from '../schemas/enums/osEnums.schema';
import type { FilterOption } from '@/shared/types/filter.types';

export const OS_STATUS_OPTIONS = [
  { value: 'ABERTA' as OsStatusEnumDataType, label: 'Aberta', color: 'blue' },
  { value: 'EM_ANDAMENTO' as OsStatusEnumDataType, label: 'Em Andamento', color: 'yellow' },
  { value: 'AGUARDANDO_PECAS' as OsStatusEnumDataType, label: 'Aguardando Peças', color: 'orange' },
  { value: 'AGUARDANDO_APROVACAO' as OsStatusEnumDataType, label: 'Aguardando Aprovação', color: 'yellow' },
  { value: 'AGUARDANDO_RETIRADA' as OsStatusEnumDataType, label: 'Aguardando Retirada', color: 'indigo' },
  { value: 'FINALIZADA' as OsStatusEnumDataType, label: 'Finalizada', color: 'green' },
  { value: 'CANCELADA' as OsStatusEnumDataType, label: 'Cancelada', color: 'red' },
] as const;

export const OS_PRIORIDADE_OPTIONS = [
  { value: 'BAIXA' as OsPriorityEnumDataType, label: 'Baixa', color: 'gray' },
  { value: 'NORMAL' as OsPriorityEnumDataType, label: 'Normal', color: 'blue' },
  { value: 'ALTA' as OsPriorityEnumDataType, label: 'Alta', color: 'orange' },
  { value: 'URGENTE' as OsPriorityEnumDataType, label: 'Urgente', color: 'red' },
] as const;

export const DEFAULT_OS_STATUS: OsStatusEnumDataType = 'ABERTA';
export const DEFAULT_OS_PRIORIDADE: OsPriorityEnumDataType = 'NORMAL';
export const DEFAULT_GARANTIA_DIAS = 90;

export const OS_BASE_URL = '/ordens-servico';
export const OS_FOTOS_URL = '/ordens-servico-fotos';

export const OS_ITEMS_PER_PAGE = 10;

export const OS_STALE_TIME = 1000 * 60 * 2;
export const OS_LIST_STALE_TIME = 1000 * 60 * 2;
export const OS_STATS_STALE_TIME = 1000 * 60 * 5;

export const SEARCH_DEBOUNCE_MS = 300;

export const STORAGE_KEY_OS_FILTER = 'os_filter_status';

export const OBJETO_HISTORY_LIMIT = 20;

export const REOPEN_MODES = {
  NONE: 'NONE',
  TEXT_ONLY: 'TEXT_ONLY',
  FULL: 'FULL',
} as const;

export type ReopenMode = typeof REOPEN_MODES[keyof typeof REOPEN_MODES];

export const OS_EQUIP_TYPE_OPTIONS = [
  { value: 'CELULAR' as OsEquipTypeEnumDataType, label: 'Celular' },
  { value: 'TABLET' as OsEquipTypeEnumDataType, label: 'Tablet' },
  { value: 'COMPUTADOR' as OsEquipTypeEnumDataType, label: 'Computador' },
  { value: 'NOTEBOOK' as OsEquipTypeEnumDataType, label: 'Notebook' },
  { value: 'IMPRESSORA' as OsEquipTypeEnumDataType, label: 'Impressora' },
  { value: 'MONITOR' as OsEquipTypeEnumDataType, label: 'Monitor' },
  { value: 'SCANNER' as OsEquipTypeEnumDataType, label: 'Scanner' },
  { value: 'OUTROS' as OsEquipTypeEnumDataType, label: 'Outros' },
] as const;

export const TAB_OPTIONS = [
  { id: 'ordens', label: 'Ordens de Serviço' },
  { id: 'servicos', label: 'Cadastro de Serviços' },
];

export const OS_STATUS_FILTER_CONFIG: Record<string, FilterOption> = {
  ABERTA:               { label: 'Aberta',              class: 'bg-blue-50 text-blue-600',       color: 'bg-blue-500'    },
  EM_ANDAMENTO:         { label: 'Em Andamento',         class: 'bg-amber-50 text-amber-700',     color: 'bg-amber-500'   },
  AGUARDANDO_PECAS:     { label: 'Aguardando Peças',     class: 'bg-orange-50 text-orange-700',   color: 'bg-orange-500'  },
  AGUARDANDO_APROVACAO: { label: 'Aguardando Aprovação', class: 'bg-purple-50 text-purple-700',   color: 'bg-purple-500'  },
  AGUARDANDO_RETIRADA:  { label: 'Aguardando Retirada',  class: 'bg-indigo-50 text-indigo-700',   color: 'bg-indigo-500'  },
  FINALIZADA:           { label: 'Finalizada',           class: 'bg-emerald-50 text-emerald-700', color: 'bg-emerald-500' },
  CANCELADA:            { label: 'Cancelada',            class: 'bg-red-50 text-red-700',         color: 'bg-red-500'     },
};
