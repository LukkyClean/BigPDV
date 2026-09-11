import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ConfigAtual {
  ip: string
  port: number
}

export type PapelMaquina = 'servidor' | 'terminal'

/**
 * Estado de rede/conexão do app (papel da máquina, bloqueio por falta de backend,
 * status do último health). Não é persistido — a fonte de verdade do papel é o
 * `system-config.json` lido pelo Tauri.
 */
export const useNetworkConfigStore = defineStore('network-config', () => {
  const necessitaConfiguracao = ref(false)
  const tentandoConexao = ref(false)
  const erroConexao = ref<string | null>(null)
  /** Sem backend alcançável — vale para terminal (servidor remoto) e servidor (serviço local). */
  const semConexaoBackend = ref(false)
  const configAtual = ref<ConfigAtual | null>(null)
  const papel = ref<PapelMaquina | null>(null)

  /** Resultado do último health check (null = ainda não verificado). */
  const online = ref<boolean | null>(null)
  const ultimaVerificacao = ref<Date | null>(null)

  /** Mensagem exibida na tela de loading durante o startup (ex.: "Iniciando servidor local… 12 s"). */
  const statusStartup = ref<string | null>(null)

  function setNecessitaConfiguracao(valor: boolean) {
    necessitaConfiguracao.value = valor
  }

  function setTentandoConexao(valor: boolean) {
    tentandoConexao.value = valor
  }

  function setErroConexao(erro: string | null) {
    erroConexao.value = erro
  }

  function setSemConexaoBackend(valor: boolean) {
    semConexaoBackend.value = valor
  }

  function setConfigAtual(ip: string, port: number) {
    configAtual.value = { ip, port }
  }

  function setPapel(valor: PapelMaquina | null) {
    papel.value = valor
  }

  function setOnline(valor: boolean) {
    online.value = valor
    ultimaVerificacao.value = new Date()
  }

  function setStatusStartup(mensagem: string | null) {
    statusStartup.value = mensagem
  }

  function reset() {
    necessitaConfiguracao.value = false
    tentandoConexao.value = false
    erroConexao.value = null
    semConexaoBackend.value = false
    configAtual.value = null
    statusStartup.value = null
  }

  return {
    necessitaConfiguracao,
    tentandoConexao,
    erroConexao,
    semConexaoBackend,
    configAtual,
    papel,
    online,
    ultimaVerificacao,
    statusStartup,
    setNecessitaConfiguracao,
    setTentandoConexao,
    setErroConexao,
    setSemConexaoBackend,
    setConfigAtual,
    setPapel,
    setOnline,
    setStatusStartup,
    reset,
  }
})
