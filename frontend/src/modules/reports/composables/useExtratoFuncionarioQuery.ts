import { type MaybeRef, unref, computed } from 'vue';
import { useQuery } from '@tanstack/vue-query';

import { getExtratoFuncionario } from '../report.service';
import { reportKeys } from '../query.keys';

/**
 * O extrato de uma pessoa. `funcionarioId` nulo desabilita a busca.
 *
 * O modal fica montado o tempo todo e só recebe o id quando o dono clica na
 * linha — sem o `enabled`, a query dispararia com `null` toda vez que a tela de
 * relatórios abrisse.
 */
export function useExtratoFuncionarioQuery(
  funcionarioId: MaybeRef<number | null>,
  inicio: MaybeRef<string>,
  fim: MaybeRef<string>,
) {
  return useQuery({
    queryKey: computed(() =>
      reportKeys.extratoFuncionario(unref(funcionarioId) ?? 0, unref(inicio), unref(fim)),
    ),
    queryFn: () => getExtratoFuncionario(unref(funcionarioId)!, unref(inicio), unref(fim)),
    enabled: computed(() => !!unref(funcionarioId) && !!unref(inicio) && !!unref(fim)),
    staleTime: 1000 * 60,
  });
}
