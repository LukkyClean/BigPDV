import api from '@/api/axios';

import { OrderServiceReadSchema, OrderServiceReadDataType } from '../schemas/orderServiceQuery.schema';

import { OrderServiceUpdateRequest, OsCancelUpdateRequest, OsObjetoUpdateRequest, OsItemUpdateRequest, OsReadyUpdateRequest } from '../types/requests.type';

import { BASE_ORDER_SERVICE_URL } from '../constants/core.constant';
import { safeParseResponse } from '@/shared/utils/parse.utils';

export async function updateOrderService(orderService: OrderServiceUpdateRequest): Promise<OrderServiceReadDataType> {
    const { data } = await api.put<OrderServiceReadDataType>(`${BASE_ORDER_SERVICE_URL}/${orderService.osNumber}`, orderService.updatedOS)
    return safeParseResponse(OrderServiceReadSchema, data, 'updateOrderService');
}

export async function updateObjetoOS(objetoOs: OsObjetoUpdateRequest): Promise<OrderServiceReadDataType> {
    const { data } = await api.put<OrderServiceReadDataType>(`${BASE_ORDER_SERVICE_URL}/${objetoOs.osNumber}/objeto`, objetoOs.updatedObjeto)
    return safeParseResponse(OrderServiceReadSchema, data, 'updateObjetoOS');
}

export async function updateItemOS(itemOs: OsItemUpdateRequest): Promise<OrderServiceReadDataType> {
    const { data } = await api.put<OrderServiceReadDataType>(`${BASE_ORDER_SERVICE_URL}/${itemOs.osNumber}/itens/${itemOs.osItemId}`, itemOs.updatedItem)
    return safeParseResponse(OrderServiceReadSchema, data, 'updateItemOS');
}

export async function updateReadyOS(readyOs: OsReadyUpdateRequest): Promise<OrderServiceReadDataType> {
    const { data } = await api.put<OrderServiceReadDataType>(`${BASE_ORDER_SERVICE_URL}/${readyOs.osNumber}/finalizar`, readyOs.readyOs)
    return safeParseResponse(OrderServiceReadSchema, data, 'updateReadyOS');
}

export async function updateCancelOS(cancelOs: OsCancelUpdateRequest): Promise<OrderServiceReadDataType> {
    const { data } = await api.put<OrderServiceReadDataType>(`${BASE_ORDER_SERVICE_URL}/${cancelOs.osNumber}/cancelar`, cancelOs.cancelOs)
    return safeParseResponse(OrderServiceReadSchema, data, 'updateCancelOS');
}

export async function updateReopen(
    { osNumber, codigoGerente, clientePagou }:
    { osNumber: string; codigoGerente?: string; clientePagou?: boolean },
): Promise<OrderServiceReadDataType> {
    const body: Record<string, unknown> = {};
    if (codigoGerente) body.codigo_gerente = codigoGerente;
    // Só envia quando explicitamente "não pagou" — o backend assume true (mantém
    // o crédito) por padrão, preservando o comportamento atual.
    if (clientePagou === false) body.cliente_pagou = false;
    const { data } = await api.put<OrderServiceReadDataType>(
        `${BASE_ORDER_SERVICE_URL}/${osNumber}/reabrir`,
        Object.keys(body).length ? body : undefined,
    )
    return safeParseResponse(OrderServiceReadSchema, data, 'updateReopen');
}
