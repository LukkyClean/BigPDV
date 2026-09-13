import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useNetworkConfigStore } from '@/shared/stores/networkConfig.store'
import { setRoleServer, setRoleClient, obterIpLocal, isErroIpLocal } from '@/shared/services/system/tauriConfig.service'
import { verificarSaude } from '@/shared/services/system/health.service'
import { reinitBackendUrl } from '@/api/backendUrl'

export type TipoMaquina = 'servidor' | 'terminal'
export type NetworkConfigStep = 0 | 1 | 2

const currentStep = ref<NetworkConfigStep>(0)
const tipoMaquina = ref<TipoMaquina | null>(null)
const ipLocal = ref<string>('')
const portaConfigurada = ref<number | null>(null)
const modoTerminalOnly = ref(false)
/** O IP informado como "servidor" é desta própria máquina — oferecer configurar como servidor. */
const sugerirServidor = ref(false)

export function useNetworkConfig() {
  const router = useRouter()
  const networkStore = useNetworkConfigStore()

  const isStepTipo = computed(() => currentStep.value === 0)
  const isStepConfig = computed(() => currentStep.value === 1)
  const isStepConexao = computed(() => currentStep.value === 2)

  function selecionarTipo(tipo: TipoMaquina) {
    tipoMaquina.value = tipo
    currentStep.value = 1
  }

  function voltar() {
    if (currentStep.value === 2) {
      currentStep.value = 1
    } else if (currentStep.value === 1) {
      if (modoTerminalOnly.value) {
        // Volta para a tela de erro de conexão
        router.replace({ name: 'erro-conexao' })
      } else {
        currentStep.value = 0
        tipoMaquina.value = null
      }
    }
  }

  async function carregarIpLocal() {
    try {
      ipLocal.value = await obterIpLocal()
    } catch {
      ipLocal.value = 'Não foi possível detectar'
    }
  }

  async function aguardarServidor(maxTentativas = 10): Promise<boolean> {
    let intervaloMs = 1000
    for (let i = 0; i < maxTentativas; i++) {
      const ok = await verificarSaude(3000)
      if (ok) return true
      await new Promise((r) => setTimeout(r, intervaloMs))
      intervaloMs = Math.min(intervaloMs * 1.5, 5000)
    }
    return false
  }

  async function configurarServidor(customPort?: number) {
    networkStore.setTentandoConexao(true)
    networkStore.setErroConexao(null)
    currentStep.value = 2

    try {
      const config = await setRoleServer(customPort)
      portaConfigurada.value = config.server_port
      await reinitBackendUrl()

      const ok = await aguardarServidor()
      if (!ok) {
        networkStore.setErroConexao(
          'O servidor iniciou mas não respondeu ao health check. Verifique se a porta não está bloqueada.',
        )
        return
      }

      finalizarConfiguracao()
    } catch (err: any) {
      networkStore.setErroConexao(err?.toString() || 'Erro ao configurar servidor')
    } finally {
      networkStore.setTentandoConexao(false)
    }
  }

  async function configurarTerminal(serverIp: string, serverPort: number) {
    networkStore.setTentandoConexao(true)
    networkStore.setErroConexao(null)
    sugerirServidor.value = false
    currentStep.value = 2

    try {
      await setRoleClient(serverIp, serverPort)
      await reinitBackendUrl()

      const ok = await verificarSaude(5000)
      if (!ok) {
        networkStore.setErroConexao(
          `Não foi possível conectar ao servidor ${serverIp}:${serverPort}. Verifique o IP, porta e se o servidor está ligado.`,
        )
        return
      }

      finalizarConfiguracao()
    } catch (err: any) {
      if (isErroIpLocal(err)) {
        // Rust recusou: o endereço é desta máquina. Era assim que o servidor virava
        // terminal apontando para o próprio IP de LAN.
        sugerirServidor.value = true
        networkStore.setErroConexao(
          `O endereço ${serverIp} é deste computador. Se o banco de dados fica aqui, configure esta máquina como Servidor.`,
        )
      } else {
        networkStore.setErroConexao(err?.toString() || 'Erro ao configurar terminal')
      }
    } finally {
      networkStore.setTentandoConexao(false)
    }
  }

  function finalizarConfiguracao() {
    networkStore.reset()
    networkStore.setPapel(tipoMaquina.value === 'servidor' ? 'servidor' : 'terminal')
    networkStore.setOnline(true)
    router.replace({ name: 'auth.user' })
  }

  function tentarNovamente() {
    networkStore.setErroConexao(null)
    sugerirServidor.value = false
    currentStep.value = 1
  }

  /** Atalho oferecido quando o IP digitado é desta máquina. */
  async function configurarComoServidor() {
    sugerirServidor.value = false
    modoTerminalOnly.value = false
    tipoMaquina.value = 'servidor'
    await configurarServidor()
  }

  /**
   * Inicia o wizard diretamente no modo terminal (pula step 0).
   * Usado quando o terminal já está configurado e precisa apenas reconfigurar IP/porta.
   */
  async function iniciarModoTerminalOnly() {
    modoTerminalOnly.value = true
    tipoMaquina.value = 'terminal'
    currentStep.value = 1
  }

  function resetConfig() {
    currentStep.value = 0
    tipoMaquina.value = null
    ipLocal.value = ''
    portaConfigurada.value = null
    modoTerminalOnly.value = false
    sugerirServidor.value = false
    networkStore.setErroConexao(null)
    networkStore.setTentandoConexao(false)
  }

  return {
    currentStep,
    tipoMaquina,
    ipLocal,
    portaConfigurada,
    modoTerminalOnly,
    sugerirServidor,

    isStepTipo,
    isStepConfig,
    isStepConexao,

    selecionarTipo,
    voltar,
    carregarIpLocal,
    configurarServidor,
    configurarTerminal,
    tentarNovamente,
    configurarComoServidor,
    iniciarModoTerminalOnly,
    resetConfig,

    tentandoConexao: computed(() => networkStore.tentandoConexao),
    erroConexao: computed(() => networkStore.erroConexao),
  }
}
