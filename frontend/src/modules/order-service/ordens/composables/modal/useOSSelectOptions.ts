import { computed, type ComputedRef } from 'vue';

import type { SelectOption } from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import { useOsEmployeesGet } from '../request/relationship/useOSRelationshipGet.queries';
import { OS_PRIORIDADE_OPTIONS, OS_STATUS_OPTIONS } from '../../constants/ordemServico.constants';

interface UseOSSelectOptionsParams {
  currentStatus: ComputedRef<string | undefined>;
  /**
   * O modal está aberto? Só então vale buscar a lista de funcionários.
   *
   * Opcional para não quebrar quem já chamava, mas o `OSFormModal` passa — sem
   * isso a busca roda em toda tela do sistema, porque ele é montado sem condição
   * no `MainLayout`.
   */
  ativo?: ComputedRef<boolean>;
}

export function useOSSelectOptions({ currentStatus, ativo }: UseOSSelectOptionsParams) {
  const employeesQuery = useOsEmployeesGet(ativo);

  const funcionariosOptions = computed<SelectOption[]>(() => {
    const raw = employeesQuery.data.value as unknown;
    const list = Array.isArray(raw) ? (raw as { id: number; nome: string }[]) : [];

    return [
      { value: '', label: '-- Selecione --' },
      ...list.map((employee) => ({ value: String(employee.id), label: employee.nome })),
    ];
  });

  const statusOptions = computed<SelectOption[]>(() => {
    if (currentStatus.value === 'FINALIZADA' || currentStatus.value === 'CANCELADA') {
      return OS_STATUS_OPTIONS
        .filter((status) => status.value === currentStatus.value)
        .map((status) => ({ value: status.value, label: status.label }));
    }

    return OS_STATUS_OPTIONS
      .filter((status) => status.value !== 'FINALIZADA' && status.value !== 'CANCELADA')
      .map((status) => ({ value: status.value, label: status.label }));
  });

  const prioridadeOptions = computed<SelectOption[]>(() =>
    OS_PRIORIDADE_OPTIONS.map((priority) => ({ value: priority.value, label: priority.label })),
  );

  return {
    funcionariosOptions,
    statusOptions,
    prioridadeOptions,
  };
}
