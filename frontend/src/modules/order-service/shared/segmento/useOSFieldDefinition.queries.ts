import { useQuery } from '@tanstack/vue-query';

import { getSegmentDefinition } from './segmentDefinition.service';

import {
  OS_FIELD_DEFINITION_QUERY_KEY,
  OS_FIELD_DEFINITION_STALE_TIME,
} from '@/modules/order-service/ordens/constants/core.constant';

/**
 * Query da definição de campos do segmento da empresa logada.
 * Base do frontend metadados-driven (renderiza campos/vistoria pelo contrato).
 */
export function useOSFieldDefinition() {
  return useQuery({
    queryKey: [OS_FIELD_DEFINITION_QUERY_KEY],
    queryFn: getSegmentDefinition,
    staleTime: OS_FIELD_DEFINITION_STALE_TIME,
  });
}
