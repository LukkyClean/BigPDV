/**
 * @fileoverview Constants for cargo (position) UI
 * @description Permission matrix configuration and card themes
 */

import {
  LayoutDashboard,
  ShoppingCart,
  Package,
  Wrench,
  Users,
  Tags,
  BarChart3,
  Building,
  IdCard,
  ShieldCheck,
} from 'lucide-vue-next';

import { PERMISSIONS } from '@/shared/constants/permissions.constants';
import type { FilterOption } from '@/shared/types/filter.types';
import type {
  AccessLevelDefinition,
  AccessLevelId,
  PermissionMatrixItem,
  PositionCardTheme,
} from '../types/positions.types';

export const POSITION_CARD_THEMES: PositionCardTheme[] = [
  {
    accent: 'bg-blue-500',
    iconBg: 'bg-blue-50 text-blue-600',
    ring: 'ring-blue-200/60',
    glow: 'shadow-blue-100',
  },
];

export const ACCESS_LEVELS: AccessLevelDefinition[] = [
  {
    id: 'administrator',
    label: 'Administrador',
    description: 'Acesso total aos modulos e configuracoes sensiveis.',
    badge: 'Nivel maximo',
    gradient: 'from-indigo-600 to-blue-600',
    minRatio: 0.85,
    filterColor: 'bg-indigo-500',
  },
  {
    id: 'manager',
    label: 'Gestor',
    description: 'Controle amplo com foco em performance e time.',
    badge: 'Nivel avancado',
    gradient: 'from-emerald-500 to-teal-500',
    minRatio: 0.55,
    filterColor: 'bg-emerald-500',
  },
  {
    id: 'operational',
    label: 'Operacional',
    description: 'Permissoes essenciais para rotina e processos.',
    badge: 'Nivel operacional',
    gradient: 'from-amber-500 to-orange-500',
    minRatio: 0.25,
    filterColor: 'bg-amber-500',
  },
  {
    id: 'restricted',
    label: 'Restrito',
    description: 'Acesso limitado para funcoes especificas.',
    badge: 'Nivel inicial',
    gradient: 'from-zinc-500 to-zinc-700',
    minRatio: 0,
    filterColor: 'bg-zinc-500',
  },
];

export const PERMISSION_MATRIX: PermissionMatrixItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    description: 'Indicadores e visao geral',
    icon: LayoutDashboard,
    viewKey: 'view_dashboard',
    manageKey: 'manage_dashboard',
    deleteKey: 'delete_dashboard',
  },
  {
    id: 'sales',
    label: 'Vendas',
    description: 'Operacoes comerciais e PDV',
    icon: ShoppingCart,
    viewKey: 'view_sales',
    manageKey: 'manage_sales',
    deleteKey: 'delete_sales',
  },
  {
    id: 'storage',
    label: 'Estoque',
    description: 'Controle de inventario e entradas',
    icon: Package,
    viewKey: 'view_storage',
    manageKey: 'manage_storage',
    deleteKey: 'delete_storage',
  },
  {
    id: 'services',
    label: 'Servicos',
    description: 'Gestao de atendimentos e OS',
    icon: Wrench,
    viewKey: 'view_services',
    manageKey: 'manage_services',
    deleteKey: 'delete_services',
  },
  {
    id: 'customers',
    label: 'Clientes',
    description: 'Carteira de clientes e historico',
    icon: Users,
    viewKey: 'view_customers',
    manageKey: 'manage_customers',
    deleteKey: 'delete_customers',
  },
  {
    id: 'products',
    label: 'Produtos',
    description: 'Cadastro e catalogo interno',
    icon: Tags,
    viewKey: 'view_products',
    manageKey: 'manage_products',
    deleteKey: 'delete_products',
  },
  {
    id: 'reports',
    label: 'Relatorios',
    description: 'Faturamento, ranking e comissoes',
    icon: BarChart3,
    viewKey: 'view_reports',
    manageKey: 'manage_reports',
    // Read-only: sem acao de excluir.
  },
  {
    id: 'enterprise',
    label: 'Empresa',
    description: 'Dados e configuracoes gerais',
    icon: Building,
    viewKey: 'view_enterprise',
    manageKey: 'manage_enterprise',
    deleteKey: 'delete_enterprise',
  },
  {
    id: 'employees',
    label: 'Equipe',
    description: 'Funcionarios, jornadas e acessos',
    icon: IdCard,
    viewKey: 'view_employees',
    manageKey: 'manage_employees',
    deleteKey: 'delete_employees',
  },
  {
    id: 'roles',
    label: 'Cargos',
    description: 'Permissoes e perfis internos',
    icon: ShieldCheck,
    viewKey: 'view_positions',
    manageKey: 'manage_positions',
    deleteKey: 'delete_positions',
  },
];

export const PERMISSION_KEYS = Array.from(
  new Set(
    PERMISSION_MATRIX.flatMap((item) =>
      [item.viewKey, item.manageKey, item.deleteKey].filter(
        (key): key is string => Boolean(key),
      ),
    ),
  ),
);

export const MODULE_PERMISSION_MAP: Partial<Record<PermissionMatrixItem['id'], string>> = {
  sales: 'venda',
  services: PERMISSIONS.services,
  customers: PERMISSIONS.customers,
  products: PERMISSIONS.products,
  enterprise: PERMISSIONS.enterprise,
  employees: PERMISSIONS.employees,
  roles: PERMISSIONS.positions,
};

export function buildPermissionDefaults(): Record<string, boolean> {
  return PERMISSION_KEYS.reduce(
    (acc, key) => {
      acc[key] = false;
      return acc;
    },
    {} as Record<string, boolean>,
  );
}

export function applyEndpointPermissions(permissoes: Record<string, boolean>) {
  const updated = { ...permissoes };

  PERMISSION_MATRIX.forEach((module) => {
    const permissionKey = MODULE_PERMISSION_MAP[module.id];
    if (!permissionKey) return;

    const hasAny = [module.viewKey, module.manageKey, module.deleteKey].some(
      (key) => key && updated[key],
    );

    updated[permissionKey] = hasAny;
  });

  return updated;
}

export function getPermissionStats(
  permissoes: Record<string, boolean> | undefined,
) {
  if (permissoes?.all === true) {
    const total = PERMISSION_KEYS.length;
    return { enabled: total, total, ratio: 1 };
  }
  const enabled = PERMISSION_KEYS.reduce(
    (count, key) => count + (permissoes?.[key] ? 1 : 0),
    0,
  );
  const total = PERMISSION_KEYS.length;
  const ratio = total ? enabled / total : 0;
  return { enabled, total, ratio };
}

export function getAccessLevel(
  permissoes: Record<string, boolean> | undefined,
): AccessLevelDefinition {
  const { ratio } = getPermissionStats(permissoes);
  return (
    ACCESS_LEVELS.find((level) => ratio >= level.minRatio) ||
    ACCESS_LEVELS[ACCESS_LEVELS.length - 1]
  );
}

export const POSITION_LEVEL_FILTERS: Record<AccessLevelId, FilterOption> =
  ACCESS_LEVELS.reduce(
    (acc, level) => {
      acc[level.id] = {
        label: level.label,
        class: '',
        color: level.filterColor,
      };
      return acc;
    },
    {} as Record<AccessLevelId, FilterOption>,
  );
