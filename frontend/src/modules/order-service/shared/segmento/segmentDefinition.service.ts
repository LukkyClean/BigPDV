import api from '@/api/axios';

import { BASE_ORDER_SERVICE_URL } from '@/modules/order-service/ordens/constants/core.constant';
import type { SegmentDefinitionResponse } from './segmentDefinition.type';

/**
 * Busca a definição de campos dinâmicos do segmento da empresa logada.
 * O backend decide o segmento pela empresa (single-tenant), então não há params.
 */
export async function getSegmentDefinition(): Promise<SegmentDefinitionResponse> {
  const { data } = await api.get<SegmentDefinitionResponse>(
    `${BASE_ORDER_SERVICE_URL}/definicao-campos`,
  );
  return data;
}
