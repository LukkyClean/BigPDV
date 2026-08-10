<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getChecklistData, saveChecklistData } from './api/checklist.service'
import type { ChecklistDados } from './types/checklist.types'
import ChecklistForm from './components/ChecklistForm.vue'
import AprovacaoArte from './components/AprovacaoArte.vue'
import SuccessScreen from './components/SuccessScreen.vue'
import { aplicarCorDaEmpresa, urlDaLogo } from './theme/aplicarTema'

type AppState = 'loading' | 'form' | 'submitting' | 'success' | 'error'

const state = ref<AppState>('loading')
const errorMessage = ref('')
const checklistData = ref<ChecklistDados | null>(null)
const dadosAdicionais = ref<Record<string, unknown>>({})
const showRetryHint = ref(false)

// Extrai params da URL (decodeURIComponent para tokens com caracteres encoded)
const params = new URLSearchParams(window.location.search)
const osNumber = params.get('os') || ''
const token = decodeURIComponent(params.get('token') || '')

onMounted(async () => {
  if (!osNumber || !token) {
    errorMessage.value = 'Link invalido. Escaneie o QR code novamente no sistema.'
    state.value = 'error'
    return
  }

  let loadingTimeout: ReturnType<typeof setTimeout> | null = null
  loadingTimeout = setTimeout(() => { showRetryHint.value = true }, 8000)

  try {
    const data = await getChecklistData(osNumber, token)
    checklistData.value = data
    dadosAdicionais.value = { ...data.dados_adicionais }
    // Quem escaneou o QR é cliente da loja, não do StartBig: a página passa a
    // ter a cor e a marca dela assim que os dados chegam.
    aplicarCorDaEmpresa(data.cor_tema)
    state.value = 'form'
  } catch (err: any) {
    const status = err?.response?.status
    if (status === 403) {
      errorMessage.value = 'Token expirado ou invalido. Gere um novo QR code no sistema.'
    } else if (status === 404) {
      errorMessage.value = 'Ordem de Servico nao encontrada.'
    } else {
      errorMessage.value = 'Erro ao conectar com o servidor. Verifique se esta na mesma rede.'
    }
    state.value = 'error'
  } finally {
    if (loadingTimeout) clearTimeout(loadingTimeout)
  }
})

async function handleSubmit() {
  state.value = 'submitting'
  try {
    await saveChecklistData(osNumber, token, dadosAdicionais.value)
    state.value = 'success'
  } catch (err: any) {
    const status = err?.response?.status
    if (status === 403) {
      errorMessage.value = 'Token expirado. Gere um novo QR code no sistema.'
    } else if (status === 409) {
      errorMessage.value = err?.response?.data?.detail || 'OS nao pode ser editada.'
    } else {
      errorMessage.value = 'Erro ao enviar. Tente novamente.'
    }
    state.value = 'error'
  }
}

function handleRetry() {
  state.value = 'form'
  errorMessage.value = ''
}

function reloadPage() {
  window.location.reload()
}

/**
 * Logo da loja, e só ela. Quem escaneou o QR é cliente da loja, não do StartBig:
 * numa loja que ainda não subiu logo, mostrar a marca do produto confunde mais
 * do que o espaço vazio resolve. Sem logo, o `v-if` do cabeçalho tira a imagem
 * inteira — o `gap` do flex não deixa buraco.
 */
const logoExibida = computed(() => urlDaLogo(checklistData.value?.url_logo))
const nomeExibido = computed(() => checklistData.value?.empresa_nome || 'StartBig')

/**
 * O que esta página é, decidido pela capacidade do segmento e não por um
 * `if segmento === 'serigrafia'`. Um segmento novo que declare `aprovacao_arte`
 * no registry ganha esta tela sem tocar neste arquivo.
 */
const aprovaArte = computed(
  () => checklistData.value?.definicao?.capacidades?.includes('aprovacao_arte') ?? false,
)

const tituloPagina = computed(() => (aprovaArte.value ? 'Aprovação de Arte' : 'Vistoria de Entrada'))
</script>

<template>
  <div class="min-h-dvh flex flex-col">
    <!-- Header -->
    <header class="bg-brand-primary text-white px-4 py-4 shadow-md">
      <div class="max-w-xl mx-auto flex items-center gap-3">
        <img
          v-if="logoExibida"
          :src="logoExibida"
          :alt="nomeExibido"
          class="h-9 rounded-full bg-white object-contain"
        />
        <div>
          <h1 class="text-lg font-bold">{{ tituloPagina }}</h1>
          <p v-if="checklistData" class="text-sm text-white/80 mt-0.5">
            {{ checklistData.numero_os }}
            <span v-if="checklistData.placa"> &mdash; {{ checklistData.placa }}</span>
            <span v-if="checklistData.marca || checklistData.modelo">
              ({{ [checklistData.marca, checklistData.modelo].filter(Boolean).join(' ') }})
            </span>
          </p>
        </div>
      </div>
    </header>

    <!-- Content -->
    <main class="flex-1 px-4 py-5 max-w-xl mx-auto w-full">
      <!-- Loading -->
      <div v-if="state === 'loading'" class="flex flex-col items-center justify-center py-20">
        <div class="w-10 h-10 border-4 border-brand-primary/30 border-t-brand-primary rounded-full animate-spin" />
        <p class="text-sm text-slate-500 mt-4">Carregando checklist...</p>
        <button
          v-if="showRetryHint"
          class="mt-4 px-5 py-2.5 bg-brand-primary text-white text-sm font-semibold rounded-xl"
          @click="reloadPage"
        >
          Tentar novamente
        </button>
      </div>

      <!-- Aprovação de arte (segmento declara a capacidade) -->
      <AprovacaoArte
        v-else-if="(state === 'form' || state === 'submitting') && aprovaArte"
        :fotos="checklistData?.fotos ?? []"
        v-model:dados-adicionais="dadosAdicionais"
        :is-submitting="state === 'submitting'"
        @submit="handleSubmit"
      />

      <!-- Form -->
      <ChecklistForm
        v-else-if="state === 'form' || state === 'submitting'"
        :definicao="checklistData!.definicao!"
        v-model:dados-adicionais="dadosAdicionais"
        :is-submitting="state === 'submitting'"
        @submit="handleSubmit"
      />

      <!-- Success -->
      <SuccessScreen
        v-else-if="state === 'success'"
        :numero-os="osNumber"
      />

      <!-- Error -->
      <div v-else-if="state === 'error'" class="flex flex-col items-center justify-center py-20 text-center">
        <div class="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
          <svg class="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h2 class="text-lg font-bold text-slate-700 mb-2">Algo deu errado</h2>
        <p class="text-sm text-slate-500 mb-6 max-w-xs">{{ errorMessage }}</p>
        <button
          v-if="checklistData"
          class="px-6 py-3 bg-brand-primary text-white text-sm font-semibold rounded-xl"
          @click="handleRetry"
        >
          Tentar novamente
        </button>
      </div>
    </main>
  </div>
</template>
