import { ref, watch, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { useNetworkConfigStore } from '@/shared/stores/networkConfig.store'
import { verificarSaude } from '@/shared/services/system/health.service'
import { tentarReconectar } from '@/shared/services/system/reconexao.service'
import { tauriDisponivel, getConfig } from '@/shared/services/system/tauriConfig.service'

const INTERVALO_PING_MS = 30_000 // 30 segundos
const MAX_FALHAS_CONSECUTIVAS = 3

/**
 * Monitoramento contínuo de saúde do backend (só no runtime Tauri).
 *
 * - Alimenta `networkStore.online` para o badge de status.
 * - Terminal: após 3 falhas seguidas tenta reconectar (redescoberta mDNS — cobre
 *   o servidor que trocou de IP) antes de bloquear na tela de erro.
 * - Servidor: após 3 falhas seguidas bloqueia na tela de erro em modo servidor,
 *   onde o operador pode religar o serviço local.
 *
 * @param appReady - Ref que indica se o app terminou o startup
 */
export function useHealthMonitor(appReady: Readonly<import('vue').Ref<boolean>>) {
  const router = useRouter()
  const networkStore = useNetworkConfigStore()

  const falhasConsecutivas = ref(0)
  let intervalId: ReturnType<typeof setInterval> | null = null
  let ativo = false
  let verificando = false

  async function verificarConexao() {
    if (networkStore.semConexaoBackend || verificando) return
    verificando = true

    try {
      // Tenta até 2 vezes antes de contar como falha (tolera microcortes de rede)
      let ok = await verificarSaude(5000)
      if (!ok) {
        await new Promise((r) => setTimeout(r, 2000))
        ok = await verificarSaude(5000)
      }
      networkStore.setOnline(ok)

      if (ok) {
        falhasConsecutivas.value = 0
        return
      }

      falhasConsecutivas.value++
      if (falhasConsecutivas.value < MAX_FALHAS_CONSECUTIVAS) return

      if (networkStore.papel === 'terminal') {
        const resultado = await tentarReconectar()
        if (resultado.ok) {
          falhasConsecutivas.value = 0
          if (resultado.novoEndereco) {
            toast.success('Servidor localizado em novo endereço', {
              description: `${resultado.novoEndereco.ip}:${resultado.novoEndereco.port}`,
            })
          }
          return
        }
        try {
          const config = await getConfig()
          networkStore.setConfigAtual(config.server_ip, config.server_port)
        } catch {
          // config já pode estar no store via startup
        }
      }

      networkStore.setSemConexaoBackend(true)
      router.replace({ name: 'erro-conexao' })
    } finally {
      verificando = false
    }
  }

  function iniciarMonitoramento() {
    if (intervalId) return
    falhasConsecutivas.value = 0
    intervalId = setInterval(verificarConexao, INTERVALO_PING_MS)
  }

  function pararMonitoramento() {
    if (intervalId) {
      clearInterval(intervalId)
      intervalId = null
    }
  }

  async function setup() {
    if (!tauriDisponivel()) return

    try {
      const config = await getConfig()
      ativo = config.configured
      if (!networkStore.papel) {
        networkStore.setPapel(config.is_server ? 'servidor' : 'terminal')
      }
    } catch {
      return
    }

    if (!ativo) return

    // Aguarda appReady para não conflitar com aguardarBackend do startup
    if (appReady.value) {
      iniciarMonitoramento()
    } else {
      const unwatch = watch(appReady, (ready) => {
        if (ready) {
          unwatch()
          // Só inicia se não entrou em erro no startup
          if (!networkStore.semConexaoBackend) {
            iniciarMonitoramento()
          }
        }
      })
    }
  }

  // Quando o erro é limpo (reconexão bem-sucedida), retoma o monitoramento
  watch(
    () => networkStore.semConexaoBackend,
    (emErro) => {
      if (!emErro && ativo) {
        falhasConsecutivas.value = 0
        iniciarMonitoramento()
      } else if (emErro) {
        pararMonitoramento()
      }
    },
  )

  // Máquina configurada pelo wizard nesta sessão (não estava configurada no startup):
  // passa a monitorar assim que o papel é definido.
  watch(
    () => networkStore.papel,
    (novoPapel) => {
      if (novoPapel && !ativo && tauriDisponivel()) {
        ativo = true
        if (appReady.value && !networkStore.semConexaoBackend) iniciarMonitoramento()
      }
    },
  )

  setup()

  onBeforeUnmount(() => {
    pararMonitoramento()
  })
}
