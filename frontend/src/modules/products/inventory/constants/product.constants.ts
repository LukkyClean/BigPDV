import { FilterOption } from "@/shared/types/filter.types";

export const PRODUTO_FISCAL_QUERY_KEY = 'produto-fiscal';

export const FILTER_CONFIG: Record<string, FilterOption> = {
    active: {
        label: 'Ativos',
        class: 'bg-emerald-50 text-emerald-600 border border-emerald-200',
        color: 'bg-emerald-500'
    },
    inactive: {
        label: 'Desativados',
        class: 'bg-red-50 text-red-600 border border-red-200',
        color: 'bg-red-500'
    }
}

export const SORT_FILTER_CONFIG: Record<string, FilterOption> = {
    'a-z': {
        label: 'A-Z',
        class: 'bg-blue-50 text-blue-600 border border-blue-200',
        color: 'bg-blue-500'
    },
    'z-a': {
        label: 'Z-A',
        class: 'bg-blue-50 text-blue-600 border border-blue-200',
        color: 'bg-blue-500'
    }
}