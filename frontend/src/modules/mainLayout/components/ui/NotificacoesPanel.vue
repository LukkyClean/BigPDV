<script setup lang="ts">
import { ref, computed } from 'vue'
import { PackageX, Clock, Megaphone, Plus, X, Send, CheckCheck } from 'lucide-vue-next'
import { useNotificacoesStore } from '@/shared/stores/notificacoes.store'
import { useAuthStore } from '@/shared/stores/auth.store'
import { storeToRefs } from 'pinia'
import { criarComunicado, marcarComunicadoLido } from '../../services/comunicado.service'
import { useOSCreateFlow } from '@/modules/order-service/ordens/composables/useOSCreateFlow'
import type { OrderServiceReadDataType } from '@/modules/order-service/ordens/schemas/orderServiceQuery.schema'

defineProps<{ style?: Record<string, string> }>()
const emit = defineEmits<{ close: [] }>()

const store = useNotificacoesStore()
const authStore = useAuthStore()
const { osAbandono, osAtrasadas, comunicados, osVistos, temOsNaoVistas } = storeToRefs(store)

const showForm = ref(false)
const titulo = ref('')
const mensagem = ref('')
const enviando = ref(false)
const expandidos = ref<Set<number>>(new Set())

const CARGOS_GERENCIAIS = ['administrador', 'gerente']

const isMasterOuGerente = computed(() => {
  if (authStore.userData?.is_master) return true
  const cargo = authStore.userData?.cargo?.nome?.toLowerCase() ?? ''
  return CARGOS_GERENCIAIS.some((c) => cargo.includes(c))
})

function formatarData(d: string | null | undefined) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('pt-BR')
}

function diasDesde(d: string | null | undefined) {
  if (!d) return 0
  return Math.floor((Date.now() - new Date(d).getTime()) / 86400000)
}

function diasAte(d: string | null | undefined) {
  if (!d) return 0
  return Math.floor((new Date(d).getTime() - Date.now()) / 86400000)
}

async function enviarComunicado() {
  if (!titulo.value.trim() || !mensagem.value.trim()) return
  enviando.value = true
  try {
    const novo = await criarComunicado(titulo.value.trim(), mensagem.value.trim())
    store.adicionarComunicado(novo)
    titulo.value = ''
    mensagem.value = ''
    showForm.value = false
  } finally {
    enviando.value = false
  }
}

function clicarComunicado(id: number, lido: boolean) {
  const novos = new Set(expandidos.value)
  if (novos.has(id)) {
    novos.delete(id)
  } else {
    novos.add(id)
    if (!lido) {
      store.marcarComunicadoLido(id)
      marcarComunicadoLido(id).catch(() => {})
    }
  }
  expandidos.value = novos
}

const semNotificacoes = computed(() =>
  osAbandono.value.length === 0 &&
  osAtrasadas.value.length === 0 &&
  comunicados.value.length === 0
)

const { openExistingOS } = useOSCreateFlow()

function abrirOS(os: OrderServiceReadDataType) {
  openExistingOS(os)
  emit('close')
}
</script>

<template>
  <div
    :style="style"
    class="fixed z-50 w-84"
    style="width: 340px"
  >
    <!-- Seta de conexão com o ícone -->
    <div class="absolute -top-1.5 right-3.5 w-3 h-3 bg-white border-l border-t border-zinc-200 rotate-45 z-10" />

    <!-- Conteúdo do painel -->
    <div class="bg-white border border-zinc-200 rounded-xl shadow-lg overflow-hidden">

    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-zinc-100">
      <div>
        <p class="text-sm font-bold text-zinc-800">Notificações</p>
        <p v-if="store.totalNaoLidas > 0" class="text-xs text-red-500 mt-0.5 font-medium">
          {{ store.totalNaoLidas }} não lida{{ store.totalNaoLidas > 1 ? 's' : '' }}
        </p>
        <p v-else class="text-xs text-zinc-400 mt-0.5">Tudo em dia</p>
      </div>
      <div class="flex items-center gap-1">
        <button
          v-if="temOsNaoVistas"
          class="p-1.5 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 rounded-lg transition-colors"
          title="Marcar OS como lidas"
          @click="store.marcarOsVistas()"
        >
          <CheckCheck :size="15" />
        </button>
        <button
          v-if="isMasterOuGerente && !showForm"
          class="flex items-center gap-1 text-xs text-brand-primary hover:bg-blue-50 px-2 py-1 rounded-lg transition-colors"
          @click="showForm = true"
        >
          <Plus :size="13" />
          Comunicado
        </button>
      </div>
      <button v-if="showForm" class="text-zinc-400 hover:text-zinc-600" @click="showForm = false">
        <X :size="16" />
      </button>
    </div>

    <!-- Form de novo comunicado -->
    <div v-if="showForm" class="px-4 py-3 border-b border-zinc-100 bg-zinc-50">
      <input
        v-model="titulo"
        maxlength="100"
        placeholder="Título do comunicado"
        class="w-full text-sm border border-zinc-200 rounded-lg px-3 py-2 mb-2 focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary bg-white"
      />
      <textarea
        v-model="mensagem"
        maxlength="2000"
        rows="3"
        placeholder="Mensagem para todos os funcionários..."
        class="w-full text-sm border border-zinc-200 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary bg-white"
      />
      <button
        :disabled="!titulo.trim() || !mensagem.trim() || enviando"
        class="mt-2 w-full flex items-center justify-center gap-2 text-sm font-medium bg-brand-primary text-white rounded-lg px-3 py-2 disabled:opacity-50 hover:opacity-90 transition-opacity"
        @click="enviarComunicado"
      >
        <Send :size="14" />
        {{ enviando ? 'Enviando...' : 'Enviar para todos' }}
      </button>
    </div>

    <!-- Lista de notificações -->
    <div class="max-h-80 overflow-y-auto [scrollbar-width:none]">
      <div v-if="semNotificacoes" class="flex flex-col items-center gap-2 py-10 text-zinc-400">
        <PackageX :size="32" stroke-width="1.5" />
        <p class="text-sm">Nenhuma notificação</p>
      </div>

      <!-- Comunicados -->
      <template v-for="c in comunicados" :key="`com-${c.id}`">
        <div
          class="flex items-start gap-3 px-4 py-3 border-b border-zinc-50 cursor-pointer transition-colors"
          :class="c.lido && !expandidos.has(c.id) ? 'opacity-50 hover:opacity-70' : 'hover:bg-zinc-50'"
          @click="clicarComunicado(c.id, c.lido)"
        >
          <div class="mt-0.5 w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
            <Megaphone :size="15" class="text-blue-600" />
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <p class="text-xs font-semibold text-zinc-800 truncate flex-1">{{ c.titulo }}</p>
              <span v-if="!c.lido" class="w-2 h-2 rounded-full bg-blue-500 shrink-0" />
            </div>
            <p class="text-xs text-zinc-500 mt-0.5" :class="expandidos.has(c.id) ? '' : 'line-clamp-2'">{{ c.mensagem }}</p>
            <p class="text-[11px] text-zinc-400 mt-1">
              {{ c.autor?.nome ?? 'Sistema' }} · {{ formatarData(c.criado_em) }}
            </p>
          </div>
        </div>
      </template>

      <!-- OS Atrasadas -->
      <div
        v-for="os in osAtrasadas"
        :key="`atrasada-${os.numero_os}`"
        class="flex items-start gap-3 px-4 py-3 border-b border-zinc-50 transition-colors cursor-pointer"
        :class="osVistos.has(os.id) ? 'opacity-40 hover:opacity-60' : 'hover:bg-zinc-50'"
        @click="abrirOS(os)"
      >
        <div class="mt-0.5 w-8 h-8 rounded-full bg-red-100 flex items-center justify-center shrink-0">
          <Clock :size="15" class="text-red-600" />
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-xs font-semibold text-zinc-800 truncate">
            OS atrasada · {{ os.numero_os }}
          </p>
          <p class="text-xs text-zinc-500 mt-0.5 truncate">
            {{ os.objeto?.marca }} {{ os.objeto?.modelo }}
          </p>
          <p class="text-[11px] text-red-600 mt-1 font-medium">
            Previsão {{ formatarData(os.data_previsao) }} · {{ Math.abs(diasAte(os.data_previsao)) }} dias em atraso
          </p>
        </div>
      </div>

      <!-- OS em Abandono -->
      <div
        v-for="os in osAbandono"
        :key="`abandono-${os.numero_os}`"
        class="flex items-start gap-3 px-4 py-3 border-b border-zinc-50 transition-colors cursor-pointer"
        :class="osVistos.has(os.id) ? 'opacity-40 hover:opacity-60' : 'hover:bg-zinc-50'"
        @click="abrirOS(os)"
      >
        <div class="mt-0.5 w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center shrink-0">
          <PackageX :size="15" class="text-amber-600" />
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-xs font-semibold text-zinc-800 truncate">
            Equipamento em abandono · {{ os.numero_os }}
          </p>
          <p class="text-xs text-zinc-500 mt-0.5 truncate">
            {{ os.objeto?.marca }} {{ os.objeto?.modelo }}
          </p>
          <p class="text-[11px] text-amber-600 mt-1 font-medium">
            Criada {{ formatarData(os.data_criacao) }} · há {{ diasDesde(os.data_criacao) }} dias sem resolução
          </p>
        </div>
      </div>
    </div>
  </div>
  </div>
</template>
