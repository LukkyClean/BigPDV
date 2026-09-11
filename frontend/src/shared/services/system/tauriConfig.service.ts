/**
 * @fileoverview Ponte de configuração com o Tauri
 * @description Invoca os commands Rust de configuração server/client e de
 * supervisão do backend local. Fora do runtime Tauri (navegador),
 * tauriDisponivel() retorna false.
 */

import { invoke, isTauri } from '@tauri-apps/api/core'

export interface AppConfig {
  is_server: boolean
  server_ip: string
  server_port: number
  configured: boolean
  /** `erp-api.exe --install` concluiu nesta máquina (tarefa agendada existe). */
  servico_instalado: boolean
  /** Pasta de dados usada pela tarefa/sidecar (`%LOCALAPPDATA%\StartBigERP\data`). */
  data_dir: string | null
}

/** Espelho de `backend::StatusBackend` (Rust). */
export interface StatusBackend {
  modo: 'nenhum' | 'externo' | 'aguardando_tarefa' | 'sidecar' | 'falhou'
  detalhe: string | null
  porta: number
  saudavel: boolean
  tarefa_instalada: boolean | null
  data_dir: string | null
  segundos_aguardando: number | null
}

/** Espelho de `network::config::DiagnosticoRede` (Rust). */
export interface DiagnosticoRede {
  papel: 'servidor' | 'terminal' | 'nao_configurado'
  api_url: string
  server_ip: string
  server_port: number
  configured: boolean
  ips_locais: string[]
  data_dir: string | null
  tarefa_instalada: boolean | null
  backend_local_responde: boolean
  config_path: string
  log_path: string | null
  log_recente: string
}

/** Prefixo do erro devolvido por `set_role_client` quando o IP é desta máquina. */
export const ERRO_IP_LOCAL = 'IP_LOCAL'

export function isErroIpLocal(err: unknown): boolean {
  return typeof err === 'string' && err.startsWith(ERRO_IP_LOCAL)
}

export function tauriDisponivel(): boolean {
  return isTauri()
}

export async function getConfig(): Promise<AppConfig> {
  return invoke<AppConfig>('get_config')
}

export async function getApiUrl(): Promise<string> {
  return invoke<string>('get_api_url')
}

export async function setRoleServer(customPort?: number): Promise<AppConfig> {
  return invoke<AppConfig>('set_role_server', { customPort: customPort ?? null })
}

export async function setRoleClient(serverIp: string, serverPort: number): Promise<AppConfig> {
  return invoke<AppConfig>('set_role_client', { serverIp, serverPort })
}

export async function obterIpLocal(): Promise<string> {
  return invoke<string>('obter_ip_local')
}

export async function isDevMode(): Promise<boolean> {
  return invoke<boolean>('is_dev_mode')
}

export async function iniciarDescobertaServidores(): Promise<void> {
  return invoke<void>('iniciar_descoberta_servidores')
}

export async function statusBackend(): Promise<StatusBackend> {
  return invoke<StatusBackend>('status_backend')
}

/** Religa o backend local (tarefa agendada via UAC ou sidecar). Só em servidor. */
export async function reiniciarBackendLocal(): Promise<StatusBackend> {
  return invoke<StatusBackend>('reiniciar_backend_local')
}

/** Reinstala a tarefa agendada (firewall + triggers + data_dir). Só em servidor. */
export async function repararServicoLocal(): Promise<StatusBackend> {
  return invoke<StatusBackend>('reparar_servico_local')
}

export async function diagnosticoRede(): Promise<DiagnosticoRede> {
  return invoke<DiagnosticoRede>('diagnostico_rede')
}

export async function lerLogRede(maxLinhas = 200): Promise<string> {
  return invoke<string>('ler_log_rede', { maxLinhas })
}
