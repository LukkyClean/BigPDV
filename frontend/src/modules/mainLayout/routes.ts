import type { RouteRecordRaw } from 'vue-router';

import { MODULOS } from '@/shared/constants/modulos.constants';

const homeRoutes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/modules/mainLayout/views/MainLayout.vue'),
    meta: {
      requiresAuth: true,
    },
    children: [
      {
        path: '',
        name: 'home',
        component: () => import('@/modules/home/views/HomeView.vue'),
        meta: {
          title: 'Início',
          subtitle: 'Resumo de vendas e pendencias',
          tabId: 'home',
          requiresAuth: true,
        },
      },
      {
        path: '/vendas',
        name: 'sales',
        component: () => import('@/modules/home/views/HomeView.vue'),
        meta: {
          title: 'Vendas',
          subtitle: 'Resumo de vendas do sistema',
          tabId: 'sales',
          requiresAuth: true,
        },
      },
      {
        path: '/equipes',
        name: 'employees',
        component: () => import('@/modules/employees/views/EmployeesView.vue'),
        meta: {
          title: 'Gestão de Equipe',
          subtitle: 'Gerencie os colaboradores da sua organização de forma centralizada.',
          tabId: 'employees',
          requiresAuth: true,
        },
      },
      {
        path: '/produtos',
        name: 'products',
        component: () => import('@/modules/products/views/ProductsView.vue'),
        meta: {
          title: 'Produtos',
          subtitle: 'Gerencie os produtos da sua organização de forma centralizada.',
          tabId: 'products',
          requiresAuth: true,
        },
      },
      {
        path: '/clientes',
        name: 'customers',
        component: () => import('@/modules/customers/views/CustomersView.vue'),
        meta: {
          title: 'Clientes',
          subtitle: 'Gerencie os clientes da sua organização de forma centralizada.',
          tabId: 'customers',
          requiresAuth: true,
        },
      },
      {
        path: '/empresa',
        name: 'enterprise',
        component: () => import('@/modules/enterprise/views/EmpresaView.vue'),
        meta: {
          title: 'Empresa',
          subtitle: 'Gerencie a empresa da sua organização de forma centralizada.',
          tabId: 'enterprise',
          requiresAuth: true,
        },
      },
      {
        path: '/fiscal',
        name: 'fiscal',
        component: () => import('@/modules/fiscal/views/FiscalView.vue'),
        meta: {
          title: 'Emissão de Notas Fiscais',
          subtitle: 'Configuração fiscal e emissão de documentos.',
          tabId: 'enterprise',
          requiresAuth: true,
        },
      },
      {
        path: '/servicos',
        name: 'services',
        component: () => import('@/modules/order-service/views/OrdemServicoView.vue'),
        meta: {
          title: 'Serviços',
          subtitle: 'Gerencie os serviços da sua organização de forma centralizada.',
          tabId: 'services',
          requiresAuth: true,
          // Esconder o item do menu NÃO basta: sem esta marca, digitar
          // /servicos na barra de endereço (ou uma aba salva do navegador)
          // abriria a tela de OS numa loja que não tem o módulo. O guard em
          // router/index.ts lê esta flag.
          exigeOrdemServico: true,
        },
      },
      {
        path: '/vendas',
        name: 'sales',
        component: () => import('@/modules/sales/SalesView.vue'),
        meta: {
          title: 'Vendas',
          subtitle: 'Gerencie as vendas da sua organização de forma centralizada.',
          tabId: 'sales',
          requiresAuth: true,
        }
      },
      {
        path: '/relatorios',
        name: 'reports',
        component: () => import('@/modules/reports/views/ReportsDashboard.vue'),
        meta: {
          title: 'Relatórios',
          subtitle: 'Faturamento e desempenho no período.',
          tabId: 'reports',
          requiresAuth: true,
        },
      },
      {
        // Rota-pai com casca própria: as telas de dentro dividem o mesmo
        // container e, mais adiante, o mesmo seletor de período. O `exigeModulo`
        // vai em cada FILHO e não aqui, porque Fluxo de Caixa e Conciliação são
        // de um plano diferente do resto — pôr a trava no pai daria o módulo
        // inteiro a quem contratou só a parte básica.
        path: '/financeiro',
        component: () => import('@/modules/financeiro/views/FinanceiroLayout.vue'),
        meta: { requiresAuth: true },
        children: [
          {
            path: '',
            redirect: { name: 'finance-overview' },
          },
          {
            path: 'visao-geral',
            name: 'finance-overview',
            component: () => import('@/modules/financeiro/views/VisaoGeralView.vue'),
            meta: {
              title: 'Gestão Financeira',
              subtitle: 'O resultado do mês e o movimento do caixa.',
              tabId: 'finance-overview',
              requiresAuth: true,
              exigeModulo: MODULOS.FINANCEIRO,
            },
          },
          {
            path: 'contas-a-pagar',
            name: 'finance-payable',
            component: () =>
              import('@/modules/financeiro/contas-pagar/views/ContasPagarView.vue'),
            meta: {
              title: 'Contas a Pagar',
              subtitle: 'O que a loja deve, para quem e quando vence.',
              tabId: 'finance-payable',
              requiresAuth: true,
              exigeModulo: MODULOS.FINANCEIRO,
            },
          },
          {
            path: 'contas-a-receber',
            name: 'finance-receivable',
            component: () =>
              import('@/modules/financeiro/contas-receber/views/ContasReceberView.vue'),
            meta: {
              title: 'Contas a Receber',
              subtitle: 'O que ainda não entrou: fiado, boleto e cartão a repassar.',
              tabId: 'finance-receivable',
              requiresAuth: true,
              exigeModulo: MODULOS.FINANCEIRO,
            },
          },
          {
            path: 'fluxo-de-caixa',
            name: 'finance-cashflow',
            component: () =>
              import('@/modules/financeiro/fluxo-caixa/views/FluxoCaixaView.vue'),
            meta: {
              title: 'Fluxo de Caixa',
              subtitle: 'A projeção dos próximos 30 e 60 dias.',
              tabId: 'finance-cashflow',
              requiresAuth: true,
              exigeModulo: MODULOS.FINANCEIRO_PRO,
            },
          },
          {
            path: 'conciliacao',
            name: 'finance-reconciliation',
            component: () =>
              import('@/modules/financeiro/conciliacao/views/ConciliacaoView.vue'),
            meta: {
              title: 'Conciliação',
              subtitle: 'Extrato da operadora conferido contra o que a loja registrou.',
              tabId: 'finance-reconciliation',
              requiresAuth: true,
              exigeModulo: MODULOS.FINANCEIRO_PRO,
            },
          },
          {
            path: 'contas-e-cartoes',
            name: 'finance-accounts',
            component: () =>
              import('@/modules/financeiro/contas-bancarias/views/ContasBancariasView.vue'),
            meta: {
              title: 'Contas e Cartões',
              subtitle: 'Onde o dinheiro da loja fica: caixa, bancos e cartões.',
              tabId: 'finance-accounts',
              requiresAuth: true,
              exigeModulo: MODULOS.FINANCEIRO,
            },
          },
          {
            path: 'plano-de-contas',
            name: 'finance-chart-accounts',
            component: () =>
              import('@/modules/financeiro/plano-contas/views/PlanoContasView.vue'),
            meta: {
              title: 'Plano de Contas',
              subtitle: 'As categorias de despesa e de receita da loja.',
              tabId: 'finance-chart-accounts',
              requiresAuth: true,
              exigeModulo: MODULOS.FINANCEIRO,
            },
          },
        ],
      },
    ],
  },
];

export default homeRoutes;
