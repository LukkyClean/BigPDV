/**
 * @fileoverview Rotina única de reconexão ao backend.
 * @description Usada no startup (App.vue), no monitor de saúde e na tela de erro.
 * Para um terminal: pinga o endereço salvo → se falhar, redescobre o servidor por
 * mDNS → se o endereço mudou (DHCP), regrava a configuração e testa de novo.
 * Para um servidor: só pinga o serviço local (quem religa é o Tauri).
 */

import { reinitBackendUrl } from '@/api/backendUrl'
import { tentarAutoDiscovery } from '@/modules/network-config/composables/useAutoDiscovery'
import { verificarSaude } from '@/shared/services/system/health.service'
import {
  getConfig,
  setRoleClient,
  tauriDisponivel,
} from '@/shared/services/system/tauriConfig.service'
import { useNetworkConfigStore } from '@/shared/stores/networkConfig.store'

export interface ResultadoReconexao {
  ok: boolean
  /** Preenchido quando a reconexão exigiu trocar o endereço salvo. */
  novoEndereco?: { ip: string; port: number }
  /** A descoberta achou o servidor rodando NESTA máquina (papel corrigido pelo Tauri). */
  servidorLocal?: boolean
}

export interface OpcoesReconexao {
  timeoutDiscoveryMs?: number
  timeoutPingMs?: number
}

export async function tentarReconectar(opcoes: OpcoesReconexao = {}): Promise<ResultadoReconexao> {
  const timeoutPing = opcoes.timeoutPingMs ?? 5000
  const store = useNetworkConfigStore()

  const marcar = (ok: boolean) => {
    store.setOnline(ok)
    return ok
  }

  if (marcar(await verificarSaude(timeoutPing))) return { ok: true }
  if (!tauriDisponivel()) return { ok: false }

  const config = await getConfig()
  if (config.is_server) {
    return { ok: false }
  }

  const servidor = await tentarAutoDiscovery(opcoes.timeoutDiscoveryMs)
  if (!servidor) return { ok: false }

  if (servidor.local) {
    // O servidor está nesta máquina: `get_api_url` (Rust) corrige o papel ao
    // reler o config. Não gravamos terminal apontando para nós mesmos.
    await reinitBackendUrl()
    const ok = marcar(await verificarSaude(timeoutPing))
    return { ok, servidorLocal: true }
  }

  const mesmoEndereco = servidor.ip === config.server_ip && servidor.port === config.server_port
  if (!mesmoEndereco) {
    await setRoleClient(servidor.ip, servidor.port)
    await reinitBackendUrl()
    store.setConfigAtual(servidor.ip, servidor.port)
  }

  const ok = marcar(await verificarSaude(timeoutPing))
  return mesmoEndereco ? { ok } : { ok, novoEndereco: { ip: servidor.ip, port: servidor.port } }
}
