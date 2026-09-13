import { ref, onUnmounted } from 'vue'
import { invoke, isTauri } from '@tauri-apps/api/core'
import { listen, type UnlistenFn } from '@tauri-apps/api/event'

export interface ServidorDescobertoPayload {
  app: string
  role: string
  ip: string
  port: number
  /** O servidor anunciado roda NESTA máquina — nunca gravar terminal apontando para ele. */
  local: boolean
}

export type EstadoDescoberta = 'buscando' | 'encontrado' | 'timeout' | 'inativo'

const TIMEOUT_DESCOBERTA_MS = 12_000

/**
 * Composable reativo para auto-discovery no wizard de configuracao.
 * Gerencia o ciclo de vida do listener Tauri e expoe estado reativo.
 */
export function useAutoDiscovery() {
  const estado = ref<EstadoDescoberta>('inativo')
  const servidorEncontrado = ref<ServidorDescobertoPayload | null>(null)

  let unlisten: UnlistenFn | null = null
  let timeoutId: ReturnType<typeof setTimeout> | null = null

  async function iniciarBusca(): Promise<void> {
    if (!isTauri()) {
      estado.value = 'timeout'
      return
    }

    estado.value = 'buscando'
    servidorEncontrado.value = null

    unlisten = await listen<ServidorDescobertoPayload>(
      'server_discovered',
      (event) => {
        if (event.payload.app === 'startbig' && event.payload.role === 'server') {
          servidorEncontrado.value = event.payload
          estado.value = 'encontrado'
          limparTimeout()
        }
      },
    )

    try {
      await invoke('iniciar_descoberta_servidores')
    } catch (e) {
      console.warn('[auto-discovery] Erro ao invocar descoberta:', e)
    }

    timeoutId = setTimeout(() => {
      if (estado.value === 'buscando') {
        estado.value = 'timeout'
      }
    }, TIMEOUT_DESCOBERTA_MS)
  }

  function limparTimeout() {
    if (timeoutId) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
  }

  function pararBusca() {
    limparTimeout()
    if (unlisten) {
      unlisten()
      unlisten = null
    }
    estado.value = 'inativo'
    servidorEncontrado.value = null

    if (isTauri()) {
      invoke('parar_descoberta_servidores').catch((e) => {
        console.warn('[auto-discovery] Erro ao invocar parar_descoberta_servidores:', e)
      })
    }
  }

  function reiniciarBusca() {
    limparTimeout()
    if (unlisten) {
      unlisten()
      unlisten = null
    }
    iniciarBusca()
  }

  onUnmounted(() => {
    pararBusca()
  })

  return {
    estado,
    servidorEncontrado,
    iniciarBusca,
    pararBusca,
    reiniciarBusca,
  }
}

/**
 * Funcao utilitaria (nao-reativa) para auto-discovery.
 * Retorna o payload do servidor encontrado ou null apos timeout.
 * Usada no App.vue para tentar auto-discovery antes de mostrar tela de erro.
 */
export async function tentarAutoDiscovery(
  timeoutMs = TIMEOUT_DESCOBERTA_MS,
): Promise<ServidorDescobertoPayload | null> {
  if (!isTauri()) return null

  return new Promise(async (resolve) => {
    let resolvido = false

    const unlisten = await listen<ServidorDescobertoPayload>(
      'server_discovered',
      (event) => {
        if (!resolvido && event.payload.app === 'startbig' && event.payload.role === 'server') {
          resolvido = true
          unlisten()
          resolve(event.payload)
        }
      },
    )

    try {
      await invoke('iniciar_descoberta_servidores')
    } catch {
      // Ignora — o listener pode ja estar ativo via production setup
    }

    setTimeout(() => {
      if (!resolvido) {
        resolvido = true
        unlisten()
        resolve(null)
      }
    }, timeoutMs)
  })
}
