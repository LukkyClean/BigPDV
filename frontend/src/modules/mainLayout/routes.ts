import type { RouteRecordRaw } from 'vue-router';

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
        component: () => import('@/modules/fiscal/views/FiscalLayout.vue'),
        // `exigeRecurso` é herdado pelas filhas na checagem do beforeEach:
        // o guard olha `to.meta`, que o vue-router monta mesclando os metas
        // de toda a cadeia de rotas casadas.
        meta: { requiresAuth: true, exigeRecurso: 'nfe' },
        children: [
          {
            path: '',
            name: 'fiscal',
            component: () => import('@/modules/fiscal/views/FiscalConfiguracoesView.vue'),
            meta: {
              title: 'Centro Fiscal',
              subtitle: 'Certificado e Ambientes de Emissão',
              tabId: 'fiscal',
              requiresAuth: true,
            },
          },
          {
            path: 'configuracoes',
            name: 'fiscal-configuracoes',
            redirect: { name: 'fiscal' },
          },
          {
            path: 'nfe',
            name: 'fiscal-nfe',
            component: () => import('@/modules/fiscal/views/FiscalNFeView.vue'),
            meta: {
              title: 'NF-e',
              subtitle: 'Notas Fiscais Eletrônicas',
              tabId: 'fiscal-nfe',
              requiresAuth: true,
            },
          },
          {
            path: 'nfce',
            name: 'fiscal-nfce',
            component: () => import('@/modules/fiscal/views/FiscalNFCeView.vue'),
            meta: {
              title: 'NFC-e',
              subtitle: 'Notas Fiscais de Consumidor',
              tabId: 'fiscal-nfce',
              requiresAuth: true,
            },
          },
          {
            path: 'nfse',
            name: 'fiscal-nfse',
            component: () => import('@/modules/fiscal/views/FiscalNFSeView.vue'),
            meta: {
              title: 'NFS-e',
              subtitle: 'Notas Fiscais de Serviço',
              tabId: 'fiscal-nfse',
              requiresAuth: true,
            },
          },
        ],
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
    ],
  },
];

export default homeRoutes;
