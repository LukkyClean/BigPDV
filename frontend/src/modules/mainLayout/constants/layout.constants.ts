import {
  ShoppingCart,
  LayoutDashboard,
  Tags,
  Users,
  Building,
  IdCard,
  Wrench,
  ChartColumn,
  FileText,
} from 'lucide-vue-next';

import { SidebarSection } from '../types/layout.types';
import { PERMISSIONS } from '@/shared/constants/permissions.constants';
import { recursoDisponivel } from '@/shared/config/planos';

export const SIDEBAR_SECTIONS: SidebarSection[] = [
  {
    title: 'MENU PRINCIPAL',
    options: [
      {
        id: 'home',
        icon: LayoutDashboard,
        label: 'Início',
        requiredPermission: PERMISSIONS.dashboard,
      },
      {
        id: 'sales',
        icon: ShoppingCart,
        label: 'Vendas',
        requiredPermission: PERMISSIONS.sales,
      },
      {
        id: 'services',
        icon: Wrench,
        label: 'Serviços',
        requiredPermission: PERMISSIONS.services,
      },
      {
        id: 'customers',
        icon: Users,
        label: 'Clientes',
        requiredPermission: PERMISSIONS.customers,
      },
      {
        id: 'products',
        icon: Tags,
        label: 'Produtos',
        requiredPermission: PERMISSIONS.products,
      },
      {
        id: 'reports',
        icon: ChartColumn,
        label: 'Relatórios',
        requiredPermission: PERMISSIONS.reports,
      },
    ],
  },
  {
    title: 'EMPRESA',
    options: [
      {
        id: 'enterprise',
        icon: Building,
        label: 'Dados da Empresa',
        requiredPermission: PERMISSIONS.enterprise,
      },
      {
        id: 'fiscal',
        icon: FileText,
        label: 'Centro Fiscal',
        requiredPermission: PERMISSIONS.enterprise,
        featureFlag: () => recursoDisponivel('nfe'),
        children: [
          { id: 'fiscal-nfe', label: 'NF-e' },
          { id: 'fiscal-nfce', label: 'NFC-e' },
          { id: 'fiscal-nfse', label: 'NFS-e' },
        ],
      },
      {
        id: 'employees',
        icon: IdCard,
        label: 'Gestão de Equipe',
        requiredPermission: PERMISSIONS.employees,
      },
    ],
  },
] as const;
