export const dashboardKeys = {
  all: ['dashboard'] as const,
  stats: (periodo: string) => [...dashboardKeys.all, 'stats', periodo] as const,
  osVencendo: () => [...dashboardKeys.all, 'os-vencendo'] as const,
  estoqueBaixo: () => [...dashboardKeys.all, 'estoque-baixo'] as const,
  ultimasVendas: () => [...dashboardKeys.all, 'ultimas-vendas'] as const,
  tendencia: (periodo: string) => [...dashboardKeys.all, 'tendencia', periodo] as const,
  meuResumo: (periodo: string) => [...dashboardKeys.all, 'meu-resumo', periodo] as const,
  minhaTendencia: (periodo: string) => [...dashboardKeys.all, 'minha-tendencia', periodo] as const,
  minhasOSVencendo: () => [...dashboardKeys.all, 'minhas-os-vencendo'] as const,
  minhasUltimasVendas: () => [...dashboardKeys.all, 'minhas-ultimas-vendas'] as const,
  minhaFila: () => [...dashboardKeys.all, 'minha-fila'] as const,
  minhasOSAtrasadas: () => [...dashboardKeys.all, 'minhas-os-atrasadas'] as const,
  osAguardandoRetirada: () => [...dashboardKeys.all, 'os-aguardando-retirada'] as const,
  minhaAtividadeHoje: () => [...dashboardKeys.all, 'minha-atividade-hoje'] as const,
  rankingFuncionarios: (periodo: string) => [...dashboardKeys.all, 'ranking-funcionarios', periodo] as const,
  osPorStatus: () => [...dashboardKeys.all, 'os-por-status'] as const,
  formasPagamento: (periodo: string) => [...dashboardKeys.all, 'formas-pagamento', periodo] as const,
  osAtrasadasEmpresa: () => [...dashboardKeys.all, 'os-atrasadas-empresa'] as const,
};

export const DASHBOARD_STALE_TIME = 1000 * 60;

export { REFETCH_DASHBOARD } from '@/core/config/queryIntervals';
