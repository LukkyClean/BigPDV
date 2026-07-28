/**
 * @fileoverview Permission keys and endpoint mapping
 * @description Centralizes permission references for UI and API resources
 */

export const PERMISSIONS = {
  all: 'all',
  dashboard: 'view_dashboard',
  sales: 'view_sales',
  storage: 'view_storage',
  services: 'servico',
  customers: 'cliente',
  products: 'produto',
  catalog: 'view_catalog',
  enterprise: 'empresa',
  employees: 'funcionario',
  positions: 'cargo',
  suppliers: 'fornecedor',
  reports: 'view_reports',
} as const;

export type PermissionKey = typeof PERMISSIONS[keyof typeof PERMISSIONS];

export const ENDPOINT_PERMISSION_MAP = {
  cargos: PERMISSIONS.positions,
  funcionarios: PERMISSIONS.employees,
  produtos: PERMISSIONS.products,
  fornecedores: PERMISSIONS.suppliers,
  servicos: PERMISSIONS.services,
  clientes: PERMISSIONS.customers,
  empresas: PERMISSIONS.enterprise,
} as const;

export const PERMISSION_ALIASES: Partial<Record<PermissionKey, string[]>> = {
  [PERMISSIONS.dashboard]: ['view_dashboard', 'manage_dashboard', 'delete_dashboard'],
  [PERMISSIONS.sales]: ['view_sales', 'manage_sales', 'delete_sales'],
  [PERMISSIONS.storage]: ['view_storage', 'manage_storage', 'delete_storage'],
  [PERMISSIONS.services]: ['view_services', 'manage_services', 'delete_services'],
  [PERMISSIONS.customers]: ['view_customers', 'manage_customers', 'delete_customers'],
  [PERMISSIONS.products]: ['view_products', 'manage_products', 'delete_products'],
  [PERMISSIONS.catalog]: ['view_catalog', 'manage_catalog', 'delete_catalog'],
  [PERMISSIONS.enterprise]: ['view_enterprise', 'manage_enterprise', 'delete_enterprise'],
  [PERMISSIONS.employees]: ['view_employees', 'manage_employees', 'delete_employees'],
  [PERMISSIONS.positions]: ['view_positions', 'manage_positions', 'delete_positions'],
  [PERMISSIONS.reports]: ['view_reports', 'manage_reports'],
};
