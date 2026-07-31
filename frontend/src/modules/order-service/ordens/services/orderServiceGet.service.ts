import api from '@/api/axios';

import { OrderServiceParamsDataType } from '../schemas/orderServiceQuery.schema';
import {
  OrderServiceReadSchema,
  OrderServicePaginationSchema,
  OrderServiceStatsSchema,
  OrderServiceReadDataType,
  OrderServicePaginationDataType,
  OrderServiceStatsDataType,
} from '../schemas/orderServiceQuery.schema';

import { BASE_ORDER_SERVICE_URL } from '../constants/core.constant';
import { safeParseResponse } from '@/shared/utils/parse.utils';

export async function getAllOs(
  query: OrderServiceParamsDataType,
): Promise<OrderServicePaginationDataType> {
  const params: Record<string, string | number | boolean> = {};
  if (query.search) params.search = query.search;
  if (query.priority_sort !== undefined) params.priority_sort = query.priority_sort;
  if (query.status) params.status = query.status;
  if (query.situacao_equipamento) params.situacao_equipamento = query.situacao_equipamento;
  if (query.page) params.page = query.page;
  if (query.limit) params.limit = query.limit;

  const { data } = await api.get<OrderServicePaginationDataType>(`${BASE_ORDER_SERVICE_URL}/`, {
    params,
  });
  return safeParseResponse(OrderServicePaginationSchema, data, 'getAllOs');
}

export async function getUniqueOS(numero_os: string): Promise<OrderServiceReadDataType> {
  const { data } = await api.get<OrderServiceReadDataType>(
    `${BASE_ORDER_SERVICE_URL}/${numero_os}`,
  );
  return safeParseResponse(OrderServiceReadSchema, data, 'getUniqueOS');
}

export async function getOsByClienteId(
  clienteId: number,
  page: number = 1,
  limit: number = 10,
): Promise<OrderServicePaginationDataType> {
  const { data } = await api.get<OrderServicePaginationDataType>(
    `${BASE_ORDER_SERVICE_URL}/cliente/${clienteId}`,
    { params: { page, limit } },
  );
  return safeParseResponse(OrderServicePaginationSchema, data, 'getOsByClienteId');
}

export async function getStatsOS(): Promise<OrderServiceStatsDataType> {
  const { data } = await api.get<OrderServiceStatsDataType>(`${BASE_ORDER_SERVICE_URL}/stats`);
  return safeParseResponse(OrderServiceStatsSchema, data, 'getStatsOS');
}

export async function getOsAbandono(): Promise<OrderServiceReadDataType[]> {
  const { data } = await api.get<OrderServiceReadDataType[]>(`${BASE_ORDER_SERVICE_URL}/abandono`);
  return data;
}

export async function getOsAtrasadas(): Promise<OrderServiceReadDataType[]> {
  const { data } = await api.get<OrderServiceReadDataType[]>(`${BASE_ORDER_SERVICE_URL}/atrasadas`);
  return data;
}
