import type {
  OsStatusEnumDataType,
  OsPriorityEnumDataType,
  OsEquipTypeEnumDataType,
  OsEquipSituacaoEnumDataType,
} from '../schemas/enums/osEnums.schema';
import type { FilterOption } from '@/shared/types/filter.types';

/**
 * Chave do "estado" que a OS exibe ao usuário.
 *
 * A coluna Status da tabela junta, de propósito, duas dimensões que no banco são
 * campos separados:
 *   - `status`               → onde a OS está no fluxo (ABERTA → … → FINALIZADA)
 *   - `situacao_equipamento` → o desfecho do objeto, gravado só na finalização
 *
 * SEM_REPARO e CONDENADO NÃO são status novos: uma OS condenada continua
 * FINALIZADA, e o faturamento, o `data_finalizacao` e os relatórios dependem
 * disso. Eles apenas substituem o rótulo "Finalizada" para quem lê a tabela.
 */
export type OsEstadoKey = OsStatusEnumDataType | 'SEM_REPARO' | 'CONDENADO';

export interface OsEstadoConfig {
  label: string;
  /** fundo + texto do badge */
  badge: string;
  /** borda, para os badges contornados */
  border: string;
  /** pontinho colorido do menu de filtro */
  dot: string;
}

/**
 * Fonte ÚNICA de rótulo e cor do estado da OS — tabela, histórico do cliente,
 * resumo da OS e menu de filtro saem todos daqui. Não recriar mapas locais em
 * componente: era assim que a mesma OS aparecia indigo num lugar e teal noutro.
 */
export const OS_ESTADO_CONFIG: Record<OsEstadoKey, OsEstadoConfig> = {
  ABERTA:               { label: 'Aberta',               badge: 'bg-blue-50 text-blue-600',       border: 'border-blue-200',    dot: 'bg-blue-500'    },
  EM_ANDAMENTO:         { label: 'Em Andamento',         badge: 'bg-amber-50 text-amber-700',     border: 'border-amber-200',   dot: 'bg-amber-500'   },
  AGUARDANDO_PECAS:     { label: 'Aguardando Peças',     badge: 'bg-orange-50 text-orange-700',   border: 'border-orange-200',  dot: 'bg-orange-500'  },
  AGUARDANDO_APROVACAO: { label: 'Aguardando Aprovação', badge: 'bg-purple-50 text-purple-700',   border: 'border-purple-200',  dot: 'bg-purple-500'  },
  AGUARDANDO_RETIRADA:  { label: 'Aguardando Retirada',  badge: 'bg-indigo-50 text-indigo-700',   border: 'border-indigo-200',  dot: 'bg-indigo-500'  },
  FINALIZADA:           { label: 'Finalizada',           badge: 'bg-emerald-50 text-emerald-700', border: 'border-emerald-200', dot: 'bg-emerald-500' },
  CANCELADA:            { label: 'Cancelada',            badge: 'bg-red-50 text-red-700',         border: 'border-red-200',     dot: 'bg-red-500'     },
  SEM_REPARO:           { label: 'Sem Reparo',           badge: 'bg-amber-50 text-amber-700',     border: 'border-amber-200',   dot: 'bg-amber-400'   },
  CONDENADO:            { label: 'Condenado',            badge: 'bg-red-50 text-red-700',         border: 'border-red-200',     dot: 'bg-red-600'     },
};

/** Desfechos filtráveis. No backend viram `situacao_equipamento`, não `status`. */
export const OS_DESFECHO_KEYS = ['SEM_REPARO', 'CONDENADO'] as const;

/** Distingue, na chave escolhida no filtro, um desfecho de um status do fluxo. */
export function isDesfechoKey(key: string): key is OsEquipSituacaoEnumDataType {
  return (OS_DESFECHO_KEYS as readonly string[]).includes(key);
}

export const OS_STATUS_OPTIONS: { value: OsStatusEnumDataType; label: string }[] = (
  [
    'ABERTA',
    'EM_ANDAMENTO',
    'AGUARDANDO_PECAS',
    'AGUARDANDO_APROVACAO',
    'AGUARDANDO_RETIRADA',
    'FINALIZADA',
    'CANCELADA',
  ] as const
).map((value) => ({ value, label: OS_ESTADO_CONFIG[value].label }));

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

/**
 * Estados que NÃO viram opção de filtro.
 *
 * CANCELADA sai porque na prática da loja a OS não é cancelada: ou ela é
 * entregue Sem Reparo / Condenado, ou finaliza reparada. O rótulo continua no
 * mapa acima — OS canceladas antigas ainda precisam de badge na tabela, e o
 * botão "Cancelar OS" segue existindo; o que some é só o atalho no menu.
 */
const OS_FILTRO_OCULTOS: readonly OsEstadoKey[] = ['CANCELADA'];

/**
 * Opções do menu de filtro — derivadas do mapa acima, na mesma ordem: primeiro
 * os status do fluxo, depois os desfechos ("Sem Reparo" / "Condenado").
 */
export const OS_STATUS_FILTER_CONFIG: Record<string, FilterOption> = Object.fromEntries(
  (Object.keys(OS_ESTADO_CONFIG) as OsEstadoKey[])
    .filter((key) => !OS_FILTRO_OCULTOS.includes(key))
    .map((key) => [
      key,
      {
        label: OS_ESTADO_CONFIG[key].label,
        class: OS_ESTADO_CONFIG[key].badge,
        color: OS_ESTADO_CONFIG[key].dot,
      },
    ]),
);
