import type { Component } from 'vue';
import type { CustomerUnionReadSchemaDataType } from '@/shared/schemas/customer/customer.schema';

// ── Re-exports dos tipos Zod (backward compatibility) ──────────────────────

export type {
  CustomerPFCreateDataType as ClientePFCreate,
  CustomerPJCreateDataType as ClientePJCreate,
  CustomerPFUpdateDataType as ClientePFUpdate,
  CustomerPJUpdateDataType as ClientePJUpdate,
  CustomerUpdateDataType as ClienteUpdate,
  EnderecoCreateDataType as EnderecoCreate,
  EnderecoUpdateDataType as EnderecoUpdate,
} from '../schemas/customerMutate.schema';

export type {
  CustomerUnionReadSchemaDataType as ClienteRead,
  CustomerPFReadSchemaDataType as ClientePFRead,
  CustomerPJReadSchemaDataType as ClientePJRead,
} from '@/shared/schemas/customer/customer.schema';

// ── Enums ──────────────────────────────────────────────────────────────────

export type TipoCliente = 'PF' | 'PJ';
export type CustomersTypes = 'PF' | 'PJ' | 'active' | 'inactive' | null;
export type Gender = 'MASCULINO' | 'FEMININO' | 'OUTRO';
export type FilterStatus = 'todos' | 'ativos' | 'inativos';
export type FilterTipo = CustomersTypes;
export type ClienteFilterTipo = CustomersTypes;
export type ClienteFilterStatus = 'todos' | 'ativos' | 'inativos';
export type CustomersStatus = 'PF' | 'PJ' | 'active' | 'inactive';

export type State =
  | 'AC' | 'AL' | 'AP' | 'AM' | 'BA' | 'CE' | 'DF' | 'ES'
  | 'GO' | 'MA' | 'MT' | 'MS' | 'MG' | 'PA' | 'PB' | 'PR'
  | 'PE' | 'PI' | 'RJ' | 'RN' | 'RS' | 'RO' | 'RR' | 'SC'
  | 'SP' | 'SE' | 'TO';

// ── Union Type (alias para Zod-inferred) ───────────────────────────────────

export type Cliente = CustomerUnionReadSchemaDataType;

// ── Stats ──────────────────────────────────────────────────────────────────

export interface ClienteStatCard {
  id: string;
  icon: Component;
  label: string;
  value: number;
  colorClass: string;
}

export interface Stats {
  total: number;
  ativos: number;
  pf: number;
  pj: number;
}

export interface ClienteStatsData {
  total: number;
  ativos: number;
  pf: number;
  pj: number;
}

// ── UI Types ───────────────────────────────────────────────────────────────

export interface ClienteTableColumn {
  key: string;
  label: string;
  sortable?: boolean;
  align?: 'left' | 'center' | 'right';
}

export type ClienteFormatted = Cliente & {
  displayName: string;
  displayDoc: string;
  displayPhone: string;
  initial: string;
  sortName: string;
};

export interface ClienteAction {
  id: string;
  icon: Component;
  label: string;
  action: () => void;
  variant: 'primary' | 'secondary' | 'outline';
}

export interface ObjetoHistorico {
  objeto: string;
  marca: string | null;
  modelo: string | null;
  numero_serie: string | null;
  cor?: string | null;
  dados_adicionais?: Record<string, unknown> | null;
}

// ── Constantes ─────────────────────────────────────────────────────────────

export const GENEROS: { value: Gender; label: string }[] = [
  { value: 'MASCULINO', label: 'Masculino' },
  { value: 'FEMININO', label: 'Feminino' },
  { value: 'OUTRO', label: 'Outro' },
];
