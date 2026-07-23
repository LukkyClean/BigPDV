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
