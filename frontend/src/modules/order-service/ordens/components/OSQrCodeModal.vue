<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { Copy, Check, Loader2 } from 'lucide-vue-next'
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue'
import { getChecklistQrUrl } from '../services/checklistToken.service'
import { useToast } from '@/shared/composables/useToast'
import * as QRCode from 'qrcode'

interface Props {
  isOpen: boolean
  osNumber: string
}

const props = defineProps<Props>()
const emit = defineEmits<{ close: [] }>()

const toast = useToast()

const qrUrl = ref('')
const isLoading = ref(false)
const hasCopied = ref(false)
const canvasRef = ref<HTMLCanvasElement | null>(null)

watch(
  () => props.isOpen,
  async (open) => {
    if (!open) return
    isLoading.value = true
    hasCopied.value = false
    try {
      const { url } = await getChecklistQrUrl(props.osNumber)
      qrUrl.value = url
      // Canvas só existe no DOM quando isLoading === false (v-else)
      isLoading.value = false
      await nextTick()
      if (canvasRef.value) {
        await QRCode.toCanvas(canvasRef.value, url, {
          width: 250,
          margin: 2,
          color: { dark: '#1e293b', light: '#ffffff' },
        })
      }
    } catch {
      isLoading.value = false
      toast.error('Erro ao gerar QR code', 'error')
      emit('close')
    }
  },
)

let copyTimeout: ReturnType<typeof setTimeout> | null = null

async function copyLink() {
  try {
    await navigator.clipboard.writeText(qrUrl.value)
    hasCopied.value = true
    toast.success('Link copiado!', 'success')
    if (copyTimeout) clearTimeout(copyTimeout)
    copyTimeout = setTimeout(() => (hasCopied.value = false), 1500)
  } catch {
    toast.error('Falha ao copiar', 'error')
  }
}
</script>

<template>
  <BaseModal
    :is-open="isOpen"
    title="Checklist pelo Celular"
    subtitle="Escaneie o QR code ou copie o link para preencher o checklist"
    size="sm"
    @close="emit('close')"
  >
    <div class="flex flex-col items-center py-4 space-y-5">
      <!-- Loading -->
      <div v-if="isLoading" class="flex flex-col items-center py-8">
        <Loader2 :size="32" class="text-brand-primary animate-spin" />
        <p class="text-sm text-slate-500 mt-3">Gerando QR code...</p>
      </div>

      <!-- QR Code -->
      <template v-else>
        <div class="bg-white p-4 rounded-2xl shadow-sm border border-slate-100">
          <canvas ref="canvasRef" />
        </div>

        <p class="text-xs text-slate-400 text-center max-w-xs">
          Abra a camera do celular e aponte para o QR code, ou copie o link abaixo
        </p>

        <!-- Link copiavel -->
        <div class="w-full flex items-center gap-2 bg-slate-50 rounded-lg border border-slate-200 p-2">
          <p class="flex-1 text-xs text-slate-600 truncate select-all font-mono">
            {{ qrUrl }}
          </p>
          <button
            type="button"
            class="shrink-0 flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-md transition-colors"
            :class="hasCopied
              ? 'bg-emerald-100 text-emerald-700'
              : 'bg-brand-primary text-white hover:bg-brand-primary/90'"
            @click="copyLink"
          >
            <component :is="hasCopied ? Check : Copy" :size="12" />
            {{ hasCopied ? 'Copiado' : 'Copiar' }}
          </button>
        </div>
      </template>
    </div>
  </BaseModal>
</template>
