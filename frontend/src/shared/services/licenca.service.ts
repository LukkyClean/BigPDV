/**
 * @fileoverview Serviço de verificação de licença.
 * Usa axios puro (sem interceptor 401) pois executa antes da autenticação.
 */

import axios from 'axios';
import { getApiBaseUrl } from '@/api/backendUrl';
import { obterHwid } from '@/shared/services/system/hwid.service';

export interface LicencaStatusResponse {
  status: 'online_valid' | 'offline_valid';
  dias_restantes?: number;
  /** Só presente quando a licença é um trial. Ausente = licença paga. */
  trial?: boolean;
}

export interface LicencaErroResponse {
  codigo: string;
  mensagem: string;
}

/**
 * Verifica o status da licença via GET /licenca/status.
 * Endpoint público (sem autenticação).
 */
export async function verificarLicenca(): Promise<LicencaStatusResponse> {
  const { data } = await axios.get<LicencaStatusResponse>(
    `${getApiBaseUrl()}/licenca/status`,
  );
  return data;
}

/**
 * Desconecta a sessão da licença na API StartBig.
 * Chamado no logout e no encerramento da aplicação.
 * Nunca propaga erro — falhas são silenciosas.
 */
export async function desconectarLicenca(): Promise<void> {
  try {
    const hwid = await obterHwid();
    await axios.post(
      `${getApiBaseUrl()}/licenca/desconectar?hwid=${encodeURIComponent(hwid)}`,
      null,
      { signal: AbortSignal.timeout(2000) },
    );
  } catch {
    // Silencioso — não bloqueia o fluxo de encerramento
  }
}

/**
 * Retorna a URL completa do endpoint de desconexão com HWID.
 * Usada pelo sendBeacon no beforeunload (fecho de janela).
 *
 * @param hwid - Hardware ID do terminal (deve ser pré-cacheado, pois
 *               beforeunload é síncrono e não pode aguardar async).
 */
export function getDesconectarUrl(hwid: string): string {
  return `${getApiBaseUrl()}/licenca/desconectar?hwid=${encodeURIComponent(hwid)}`;
}
