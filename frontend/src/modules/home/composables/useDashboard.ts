import { ref, computed } from 'vue';
import { TrendingUp, Wrench, Users, CreditCard } from 'lucide-vue-next';

import { formatCurrency, formatVariacao } from '@/shared/utils/finance';
import { useDashboardStatsQuery } from './queries/useDashboardStatsQuery';
import { useOSVencendoQuery } from './queries/useOSVencendoQuery';
import { useEstoqueBaixoQuery } from './queries/useEstoqueBaixoQuery';
import { useUltimasVendasQuery } from './queries/useUltimasVendasQuery';

import { useOrdemServico } from '@/shared/composables/useOrdemServico';

import type { StatCardData, PeriodFilter } from '../types/dashboard.types';

const PERIOD_LABELS: Record<PeriodFilter, string> = {
  hoje: 'hoje',
  semana: 'esta semana',
  mes: 'este mês',
};

export function useDashboard() {
  const activePeriod = ref<PeriodFilter>('hoje');
  const { usaOrdemServico } = useOrdemServico();

  // Queries
  const statsQuery = useDashboardStatsQuery(activePeriod);
  const osVencendoQuery = useOSVencendoQuery();
  const estoqueBaixoQuery = useEstoqueBaixoQuery();
  const ultimasVendasQuery = useUltimasVendasQuery();

  // Stats cards computados a partir dos dados da API
  const stats = computed<StatCardData[]>(() => {
    const data = statsQuery.data.value;
    if (!data) return [];

    const cards: StatCardData[] = [
      {
        id: 'vendas-totais',
        icon: TrendingUp,
        // QUANTAS vendas, não quanto venderam.
        //
        // O valor ja aparece inteiro no numero-heroi de faturamento, logo
        // abaixo, com a quebra "Vendas R$ X · Servicos R$ Y". Repetir o mesmo
        // R$ aqui gastava um dos quatro cards do painel sem acrescentar nada —
        // e a contagem e a informacao que faltava para o dono ler o movimento
        // do dia (dez vendas de R$ 33 e um dia diferente de uma de R$ 330).
        //
        // Backend antigo nao manda `vendas_count`: nesse caso o card volta a
        // mostrar o valor, em vez de afirmar "0 vendas".
        label: data.vendas_count === undefined ? 'Vendas Totais' : 'Vendas Finalizadas',
        value:
          data.vendas_count === undefined
            ? formatCurrency(data.vendas_total)
            : String(data.vendas_count),
        change: formatVariacao(data.vendas_count_variacao ?? data.vendas_total_variacao),
        isPositive: (data.vendas_count_variacao ?? data.vendas_total_variacao) >= 0,
        isEmpty: data.vendas_count === undefined ? data.vendas_total === 0 : data.vendas_count === 0,
        emptyLabel: 'Sem vendas',
      },
      {
        id: 'ordens-servico',
        icon: Wrench,
        // Conta OS FINALIZADAS no período — o painel é de resultados, e o
        // faturamento de serviços ao lado usa a mesma âncora.
        label: 'OS Finalizadas',
        value: String(data.os_count),
        change: formatVariacao(data.os_count_variacao),
        isPositive: data.os_count_variacao >= 0,
        isEmpty: data.os_count === 0,
        emptyLabel: 'Nenhuma finalizada',
      },
      {
        id: 'novos-clientes',
        icon: Users,
        label: 'Novos Clientes',
        value: String(data.novos_clientes),
        change: formatVariacao(data.novos_clientes_variacao),
        isPositive: data.novos_clientes_variacao >= 0,
        isEmpty: data.novos_clientes === 0,
        emptyLabel: 'Nenhum novo',
      },
      {
        id: 'ticket-medio',
        icon: CreditCard,
        label: 'Ticket Médio',
        value: formatCurrency(data.ticket_medio),
        change: formatVariacao(data.ticket_medio_variacao),
        isPositive: data.ticket_medio_variacao >= 0,
        isEmpty: data.ticket_medio === 0,
        emptyLabel: 'Sem movimento',
      },
    ];

    // Numa loja sem Ordem de Servico, "OS Finalizadas: 0" nao e informacao — e
    // um lembrete diario de um modulo que ela nao tem. O padrao de
    // `usaOrdemServico` e TRUE, entao para oficina, informatica e serigrafia o
    // painel continua exatamente igual.
    return usaOrdemServico.value ? cards : cards.filter((c) => c.id !== 'ordens-servico');
  });

  // Dados crus das metricas — usados pelo numero-heroi (Faturamento total).
  const statsData = computed(() => statsQuery.data.value ?? null);

  const osVencendo = computed(() => osVencendoQuery.data.value?.items ?? []);
  const estoqueBaixo = computed(() => estoqueBaixoQuery.data.value?.items ?? []);
  const ultimasVendas = computed(() => ultimasVendasQuery.data.value?.items ?? []);

  const periodDescription = computed(
    () => `Confira os resultados da loja para ${PERIOD_LABELS[activePeriod.value]}.`,
  );

  function setPeriod(period: PeriodFilter): void {
    activePeriod.value = period;
  }

  return {
    activePeriod,
    stats,
    statsData,
    setPeriod,
    periodDescription,
    osVencendo,
    estoqueBaixo,
    ultimasVendas,
    isLoadingStats: statsQuery.isLoading,
    isLoadingOS: osVencendoQuery.isLoading,
    isLoadingEstoque: estoqueBaixoQuery.isLoading,
    isLoadingVendas: ultimasVendasQuery.isLoading,
    isErrorStats: statsQuery.isError,
    isErrorOS: osVencendoQuery.isError,
    isErrorEstoque: estoqueBaixoQuery.isError,
    isErrorVendas: ultimasVendasQuery.isError,
  };
}
