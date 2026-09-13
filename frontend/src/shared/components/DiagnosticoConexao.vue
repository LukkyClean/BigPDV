<script setup lang="ts">
/**
 * @component DiagnosticoConexao
 * @description Painel "Diagnóstico de conexão": papel da máquina, URL da API em
 *   uso, IPs locais, estado do serviço local e log de rede. Usado na tela de erro
 *   de conexão e em Configurações › Rede e Conexão. Fora do Tauri mostra só o básico.
 */
import { ref, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { toast } from 'vue-sonner'
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue'
import { useNetworkConfigStore } from '@/shared/stores/networkConfig.store'
import { getBackendApiUrl } from '@/api/backendUrl'
import { tentarReconectar } from '@/shared/services/system/reconexao.service'
import {
  tauriDisponivel,
  diagnosticoRede,
  reiniciarBackendLocal,
  repararServicoLocal,
  type DiagnosticoRede,
} from '@/shared/services/system/tauriConfig.service'

withDefaults(defineProps<{ compacto?: boolean }>(), { compacto: false })

const networkStore = useNetworkConfigStore()
const { online, ultimaVerificacao } = storeToRefs(networkStore)

const diagnostico = ref<DiagnosticoRede | null>(null)
const carregando = ref(false)
const acaoEmCurso = ref<'reiniciar' | 'reparar' | 'buscar' | null>(null)
const mostrarLog = ref(false)

const papelLabel = computed(() => {
  switch (diagnostico.value?.papel) {
    case 'servidor':
      return 'Servidor (o banco de dados está nesta máquina)'
    case 'terminal':
      return 'Terminal (conecta a um servidor na rede local)'
    case 'nao_configurado':
      return 'Não configurado'
    default:
      return tauriDisponivel() ? '—' : 'Navegador (desenvolvimento)'
  }
})

const ultimaVerificacaoLabel = computed(() =>
  ultimaVerificacao.value ? ultimaVerificacao.value.toLocaleTimeString('pt-BR') : 'ainda não verificado',
)

async function carregar() {
  if (!tauriDisponivel()) return
  carregando.value = true
  try {
    diagnostico.value = await diagnosticoRede()
  } catch (e) {
    console.warn('[diagnostico] falha ao carregar:', e)
  } finally {
    carregando.value = false
  }
}

async function reiniciarServico() {
  acaoEmCurso.value = 'reiniciar'
  try {
    const status = await reiniciarBackendLocal()
    if (status.saudavel) {
      toast.success('Serviço local respondendo', { description: `Porta ${status.porta}` })
      networkStore.setOnline(true)
    } else {
      toast.error('O serviço ainda não respondeu', {
        description: status.detalhe ?? 'Tente "Reparar serviço" ou reinicie o computador.',
      })
    }
  } catch (e) {
    toast.error('Não foi possível reiniciar o serviço', { description: String(e) })
  } finally {
    acaoEmCurso.value = null
    await carregar()
  }
}

async function repararServico() {
  acaoEmCurso.value = 'reparar'
  try {
    const status = await repararServicoLocal()
    toast.success('Serviço reinstalado', {
      description: status.saudavel ? `Respondendo na porta ${status.porta}` : 'Aguardando o serviço subir…',
    })
  } catch (e) {
    toast.error('Falha ao reparar o serviço', { description: String(e) })
  } finally {
    acaoEmCurso.value = null
    await carregar()
  }
}

async function buscarServidor() {
  acaoEmCurso.value = 'buscar'
  try {
    const resultado = await tentarReconectar()
    if (resultado.ok) {
      toast.success('Servidor encontrado', {
        description: resultado.novoEndereco
          ? `Novo endereço: ${resultado.novoEndereco.ip}:${resultado.novoEndereco.port}`
          : 'Conexão restabelecida',
      })
      networkStore.setSemConexaoBackend(false)
    } else {
      toast.error('Nenhum servidor respondeu na rede local')
    }
  } finally {
    acaoEmCurso.value = null
    await carregar()
  }
}

onMounted(carregar)

defineExpose({ carregar })
</script>

<template>
  <div class="space-y-4 text-left">
    <div class="flex items-center justify-between">
      <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Diagnóstico de conexão</p>
      <button
        type="button"
        class="text-xs text-brand-primary hover:underline cursor-pointer disabled:opacity-50"
        :disabled="carregando"
        @click="carregar"
      >
        {{ carregando ? 'Atualizando…' : 'Atualizar' }}
      </button>
    </div>

    <div class="bg-zinc-50 rounded-xl p-4 grid gap-2 text-xs">
      <div class="flex justify-between gap-4">
        <span class="text-zinc-500">Papel desta máquina</span>
        <span class="font-semibold text-zinc-700 text-right">{{ papelLabel }}</span>
      </div>
      <div class="flex justify-between gap-4">
        <span class="text-zinc-500">Endereço da API em uso</span>
        <span class="font-mono font-semibold text-zinc-700 text-right break-all">
          {{ diagnostico?.api_url ?? getBackendApiUrl() }}
        </span>
      </div>
      <div class="flex justify-between gap-4">
        <span class="text-zinc-500">Status</span>
        <span
          class="font-semibold"
          :class="online === null ? 'text-zinc-500' : online ? 'text-emerald-600' : 'text-red-600'"
        >
          {{ online === null ? 'não verificado' : online ? 'Online' : 'Sem resposta' }}
          <span class="text-zinc-400 font-normal">· {{ ultimaVerificacaoLabel }}</span>
        </span>
      </div>

      <template v-if="diagnostico">
        <div class="flex justify-between gap-4">
          <span class="text-zinc-500">IPs desta máquina</span>
          <span class="font-mono text-zinc-700 text-right">
            {{ diagnostico.ips_locais.length ? diagnostico.ips_locais.join(', ') : 'nenhum (rede desconectada?)' }}
          </span>
        </div>
        <template v-if="diagnostico.papel === 'servidor'">
          <div class="flex justify-between gap-4">
            <span class="text-zinc-500">Serviço StartBigServer (tarefa do Windows)</span>
            <span class="font-semibold text-zinc-700">
              {{ diagnostico.tarefa_instalada === null ? 'não foi possível consultar' : diagnostico.tarefa_instalada ? 'instalado' : 'não instalado' }}
            </span>
          </div>
          <div class="flex justify-between gap-4">
            <span class="text-zinc-500">Backend local na porta {{ diagnostico.server_port }}</span>
            <span class="font-semibold" :class="diagnostico.backend_local_responde ? 'text-emerald-600' : 'text-red-600'">
              {{ diagnostico.backend_local_responde ? 'respondendo' : 'sem resposta' }}
            </span>
          </div>
          <div v-if="!compacto" class="flex justify-between gap-4">
            <span class="text-zinc-500">Pasta de dados</span>
            <span class="font-mono text-zinc-700 text-right break-all">{{ diagnostico.data_dir ?? 'padrão do usuário' }}</span>
          </div>
        </template>
        <div v-else-if="diagnostico.papel === 'terminal'" class="flex justify-between gap-4">
          <span class="text-zinc-500">Servidor configurado</span>
          <span class="font-mono font-semibold text-zinc-700">{{ diagnostico.server_ip }}:{{ diagnostico.server_port }}</span>
        </div>
        <div v-if="!compacto" class="flex justify-between gap-4">
          <span class="text-zinc-500">Arquivo de configuração</span>
          <span class="font-mono text-zinc-700 text-right break-all">{{ diagnostico.config_path }}</span>
        </div>
      </template>
    </div>

    <div v-if="diagnostico" class="flex flex-wrap gap-2">
      <template v-if="diagnostico.papel === 'servidor'">
        <BaseButton size="sm" :disabled="acaoEmCurso !== null" @click="reiniciarServico">
          {{ acaoEmCurso === 'reiniciar' ? 'Reiniciando…' : 'Reiniciar serviço' }}
        </BaseButton>
        <BaseButton size="sm" variant="secondary" :disabled="acaoEmCurso !== null" @click="repararServico">
          {{ acaoEmCurso === 'reparar' ? 'Reparando…' : 'Reparar serviço' }}
        </BaseButton>
      </template>
      <BaseButton
        v-else-if="diagnostico.papel === 'terminal'"
        size="sm"
        :disabled="acaoEmCurso !== null"
        @click="buscarServidor"
      >
        {{ acaoEmCurso === 'buscar' ? 'Procurando…' : 'Buscar servidor na rede' }}
      </BaseButton>
    </div>

    <div v-if="diagnostico && !compacto">
      <button
        type="button"
        class="text-xs text-brand-primary hover:underline cursor-pointer"
        @click="mostrarLog = !mostrarLog"
      >
        {{ mostrarLog ? 'Ocultar log de rede' : 'Ver log de rede' }}
      </button>
      <pre
        v-if="mostrarLog"
        class="mt-2 max-h-56 overflow-auto rounded-lg bg-zinc-900 text-zinc-100 text-[11px] p-3 whitespace-pre-wrap"
      >{{ diagnostico.log_recente || 'Sem registros ainda.' }}</pre>
      <p v-if="mostrarLog && diagnostico.log_path" class="text-[10px] text-zinc-400 mt-1 font-mono break-all">
        {{ diagnostico.log_path }}
      </p>
    </div>

    <p v-if="!tauriDisponivel()" class="text-xs text-zinc-400">
      Diagnóstico completo disponível apenas no aplicativo instalado.
    </p>
  </div>
</template>
