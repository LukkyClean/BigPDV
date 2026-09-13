/**
 * @fileoverview Health check do backend
 * @description Verifica conectividade com o backend via GET /api/health.
 * Usa axios puro (sem interceptors de auth).
 */

import axios from 'axios'
import { getBackendApiUrl } from '@/api/backendUrl'

export async function verificarSaude(timeoutMs = 5000): Promise<boolean> {
  try {
    const { data } = await axios.get(`${getBackendApiUrl()}/health`, { timeout: timeoutMs })
    return data.status === 'ok'
  } catch {
    return false
  }
}

export interface OpcoesAguardarBackend {
  /** Tempo máximo total de espera. */
  maxMs?: number
  /** Chamado a cada tentativa com os segundos decorridos (para a tela de loading). */
  onProgress?: (segundos: number) => void
  /** Se devolver true, a espera é interrompida (ex.: Tauri avisou que o sidecar falhou). */
  abortar?: () => boolean
}

/**
 * Aguarda o backend ficar disponível.
 * - Servidor (serviço local): até 120 s. No boot, a tarefa agendada dispara 30 s
 *   após o Windows subir e o onefile de 42 MB ainda extrai e roda migrations —
 *   os ~38 s antigos eram "cara ou coroa" e derrubavam o servidor no wizard.
 * - Terminal (servidor remoto): ~5 s — se está fora, a redescoberta mDNS é o
 *   próximo passo, não esperar mais.
 */
export async function aguardarBackend(
  isServer: boolean,
  opcoes: OpcoesAguardarBackend = {},
): Promise<boolean> {
  const maxMs = opcoes.maxMs ?? (isServer ? 120_000 : 5_000)
  const intervaloMs = isServer ? 2_000 : 1_500
  const inicio = Date.now()

  while (true) {
    if (await verificarSaude(3000)) return true

    const decorrido = Date.now() - inicio
    opcoes.onProgress?.(Math.round(decorrido / 1000))
    if (opcoes.abortar?.()) return false
    if (decorrido + intervaloMs > maxMs) return false

    await new Promise((r) => setTimeout(r, intervaloMs))
  }
}
