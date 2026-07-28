import api from '@/api/axios';

import { BASE_ORDER_SERVICE_URL } from '@/modules/order-service/ordens/constants/core.constant';

/** Veículo com revisão vencida (por data e/ou KM). */
export interface RevisaoPendente {
  objeto_id: number;
  cliente_id: number;
  cliente_nome: string | null;
  cliente_telefone: string | null;
  tem_os_aberta: boolean;
  numero_serie: string;
  marca: string;
  modelo: string;
  proxima_revisao_data: string | null;
  proxima_revisao_km: number | null;
  km_atual: number | null;
  motivo: 'data' | 'km';
}

/** Um ponto do histórico de quilometragem do veículo. */
export interface HistoricoKmItem {
  numero_os: string;
  data: string;
  km_entrada: number;
}

/** Veículos com revisão vencida — GET /ordens-servico/revisoes-pendentes. */
export async function getRevisoesPendentes(): Promise<RevisaoPendente[]> {
  const { data } = await api.get<RevisaoPendente[]>(
    `${BASE_ORDER_SERVICE_URL}/revisoes-pendentes`,
  );
  return data;
}

/** Histórico de KM de um objeto/veículo — GET /ordens-servico/objeto/{id}/historico-km. */
export async function getHistoricoKm(objetoId: number): Promise<HistoricoKmItem[]> {
  const { data } = await api.get<HistoricoKmItem[]>(
    `${BASE_ORDER_SERVICE_URL}/objeto/${objetoId}/historico-km`,
  );
  return data;
}
