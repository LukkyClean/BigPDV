import { useQuery } from '@tanstack/vue-query';
import { dashboardService } from '../../services/dashboard.service';
import { dashboardKeys, DASHBOARD_STALE_TIME, REFETCH_DASHBOARD } from '../../constants/dashboard.constants';
import { useOrdemServico } from '@/shared/composables/useOrdemServico';

export function useOSAtrasadasEmpresaQuery() {
  const { usaOrdemServico } = useOrdemServico();

  return useQuery({
    queryKey: dashboardKeys.osAtrasadasEmpresa(),
    queryFn: () => dashboardService.getOSAtrasadasEmpresa(),
    // Loja sem Ordem de Servico nao consulta OS.
    //
    // Esconder o componente com `v-if` NAO para a consulta: ela continuaria
    // batendo no servidor a cada `refetchInterval`, para sempre, para buscar um
    // dado que ninguem vai ver. Numa loja de PDV isso e polling puro no vazio.
    //
    // O padrao de `usaOrdemServico` e TRUE (ver useOrdemServico), entao quem tem
    // OS -- oficina, informatica, serigrafia -- nao muda em nada.
    enabled: usaOrdemServico,
    staleTime: DASHBOARD_STALE_TIME,
    refetchInterval: REFETCH_DASHBOARD,
  });
}
