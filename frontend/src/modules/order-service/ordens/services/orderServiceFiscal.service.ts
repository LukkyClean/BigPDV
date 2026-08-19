import api from '@/api/axios';
import { BASE_ORDER_SERVICE_URL } from '../constants/core.constant';
import type { OsNotaFiscalUpdate, OsNotaFiscalRead } from '../types/notaFiscal.type';
import type { ResultadoVerificacaoFiscal } from '@/shared/types/fiscal.types';

export async function getOsNotaFiscal(osNumero: string): Promise<OsNotaFiscalRead | null> {
  try {
    const { data } = await api.get<OsNotaFiscalRead>(
      `${BASE_ORDER_SERVICE_URL}/${osNumero}/fiscal`,
    );
    return data;
  } catch (err: any) {
    if (err?.response?.status === 404) return null;
    throw err;
  }
}

export async function upsertOsNotaFiscal(
  osNumero: string,
  dados: OsNotaFiscalUpdate,
): Promise<OsNotaFiscalRead> {
  const { data } = await api.put<OsNotaFiscalRead>(
    `${BASE_ORDER_SERVICE_URL}/${osNumero}/fiscal`,
    dados,
  );
  return data;
}

export async function verificarFiscalOS(
  osNumero: string,
  tipoDocumento: string = 'ambos',
): Promise<ResultadoVerificacaoFiscal> {
  const { data } = await api.get<ResultadoVerificacaoFiscal>(
    `${BASE_ORDER_SERVICE_URL}/${osNumero}/verificar-fiscal`,
    { params: { tipo_documento: tipoDocumento } },
  );
  return data;
}

export async function emitirFiscalOS(
  osNumero: string,
  tipoDocumento: string = 'ambos',
): Promise<void> {
  await api.post(
    `${BASE_ORDER_SERVICE_URL}/${osNumero}/emitir-fiscal`,
    null,
    { params: { tipo_documento: tipoDocumento } },
  );
}
