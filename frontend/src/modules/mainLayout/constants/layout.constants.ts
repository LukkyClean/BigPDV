import {
  ShoppingCart,
  LayoutDashboard,
  Tags,
  Users,
  Building,
  IdCard,
  Wrench,
  ChartColumn,
  Wallet,
  FileText,
} from 'lucide-vue-next';

import { SidebarSection } from '../types/layout.types';
import { PERMISSIONS } from '@/shared/constants/permissions.constants';
import { MODULOS } from '@/shared/constants/modulos.constants';
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
      {
        // Vizinho de Relatórios de propósito: um olha para trás (quanto vendi),
        // o outro para o compromisso (quanto devo, quanto tenho a receber).
        //
        // O `id` do pai não é rota — grupo não navega, quem navega são os
        // filhos. Ver SidebarItemGroup.
        id: 'finance',
        icon: Wallet,
        label: 'Gestão Financeira',
        requiredPermission: PERMISSIONS.finance,
        requiredModule: MODULOS.FINANCEIRO,
        children: [
          {
            id: 'finance-overview',
            label: 'Visão Geral',
            requiredPermission: PERMISSIONS.finance,
            requiredModule: MODULOS.FINANCEIRO,
          },
          {
            id: 'finance-analysis',
            label: 'Análise',
            // Basta `view`: é leitura, e não expõe documento de folha nenhum.
            requiredPermission: PERMISSIONS.finance,
            // PRO junto com Fluxo de Caixa e Conciliação. A linha é: base
            // guarda e controla o dinheiro; pro avisa e aconselha.
            requiredModule: MODULOS.FINANCEIRO_PRO,
          },
          {
            id: 'finance-payable',
            label: 'Contas a Pagar',
            // Mostra aluguel e salário. Exige `manage` porque não existe motivo
            // para alguém só consultar a folha de pagamento da loja.
            requiredPermission: PERMISSIONS.manageFinance,
            requiredModule: MODULOS.FINANCEIRO,
          },
          {
            id: 'finance-receivable',
            label: 'Contas a Receber',
            // Basta `view`: cobrar quem ficou para o fim do mês é tarefa de
            // atendimento, e não abre a despesa da loja junto.
            requiredPermission: PERMISSIONS.finance,
            requiredModule: MODULOS.FINANCEIRO,
          },
          {
            id: 'finance-cashflow',
            label: 'Fluxo de Caixa',
            requiredPermission: PERMISSIONS.finance,
            requiredModule: MODULOS.FINANCEIRO_PRO,
          },
          {
            id: 'finance-reconciliation',
            label: 'Conciliação',
            requiredPermission: PERMISSIONS.manageFinance,
            requiredModule: MODULOS.FINANCEIRO_PRO,
          },
          {
            id: 'finance-statement',
            label: 'Extrato',
            // Basta `view`, como o Contas a Receber: conferir o dinheiro que
            // andou é o trabalho de fechar o mês, e a tela não expõe salário —
            // mostra movimento, não o documento de RH.
            requiredPermission: PERMISSIONS.finance,
            // FINANCEIRO e não PRO: conferir o próprio dinheiro não é recurso
            // avançado.
            requiredModule: MODULOS.FINANCEIRO,
          },
          {
            id: 'finance-chart-accounts',
            label: 'Plano de Contas',
            requiredPermission: PERMISSIONS.manageFinance,
            requiredModule: MODULOS.FINANCEIRO,
          },
        ],
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
        // SOME enquanto recursoDisponivel('nfe') for false -- e nao aparece com
        // cadeado, como faz a Gestao Financeira. A diferenca e deliberada: NF-e
        // ainda nao e vendida no plano START, entao anunciar cria expectativa de
        // algo que o cliente nao tem como comprar. Ver `featureFlag` em
        // layout.types.ts.
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
