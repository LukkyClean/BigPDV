<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { Eye, EyeOff, ShieldAlert } from 'lucide-vue-next'
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue'
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue'

/**
 * Modal de PIN do gerente, compartilhado por todas as aprovações.
 *
 * O SUBTÍTULO E O TEXTO SÃO CONFIGURÁVEIS, com o desconto como padrão.
 *
 * Eles nasceram chumbados em "Desconto acima do limite configurado" porque o
 * desconto era o único caso. Hoje sangria, cancelamento, reabertura e abertura
 * de caixa usam este mesmo modal — e o operador do caixa lia "o desconto
 * informado excede o limite permitido" ao abrir o turno, sem desconto nenhum na
 * tela. O padrão mantém as telas antigas exatamente como estão; quem tem outro
 * motivo passa o seu.
 */
const props = withDefaults(defineProps<{
  isOpen: boolean
  isLoading?: boolean
  motivo?: string
  descricao?: string
}>(), {
  motivo: 'Desconto acima do limite configurado',
  descricao: 'O desconto informado excede o limite permitido. Insira o PIN do gerente para autorizar.',
})

const emit = defineEmits<{
  (e: 'confirmar', pin: string): void
  (e: 'cancelar'): void
}>()

const pin = ref('')
const showPin = ref(false)

const pinInputRef = ref<HTMLInputElement | null>(null)

watch(() => props.isOpen, (aberto) => {
  if (aberto) {
    pin.value = ''
    showPin.value = false
    focarPin()
  }
})

/**
 * O cursor nasce no PIN.
 *
 * O `autofocus` do HTML já estava aqui e não bastava: ele vale para o elemento
 * que existe quando a página carrega, e este campo nasce dentro de um modal com
 * transição, muito depois. Quem era interrompido no meio de uma venda tinha que
 * largar o teclado e clicar no campo para digitar a senha do gerente.
 */
function focarPin() {
  const tentar = () => {
    const input = pinInputRef.value
    if (!input) return false
    input.focus()
    return document.activeElement === input
  }

  nextTick(() => {
    if (tentar()) return
    requestAnimationFrame(() => void tentar())
  })
}

function handleConfirmar() {
  if (!pin.value.trim()) return
  const pinValue = pin.value
  pin.value = ''
  emit('confirmar', pinValue)
}

function handleCancelar() {
  pin.value = ''
  showPin.value = false
  emit('cancelar')
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') handleConfirmar()
  if (e.key === 'Escape') handleCancelar()
}
</script>

<template>
  <BaseModal :is-open="isOpen" title="Aprovação do Gerente" size="sm" overlay>
    <template #header>
      <div class="flex items-center justify-between px-6 py-4 border-b border-zinc-200">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 bg-amber-100 rounded-lg flex items-center justify-center shrink-0">
            <ShieldAlert :size="18" class="text-amber-600" />
          </div>
          <div>
            <h2 class="text-sm font-bold text-zinc-800">Aprovação do Gerente</h2>
            <p class="text-xs text-zinc-500">{{ motivo }}</p>
          </div>
        </div>
      </div>
    </template>

    <div class="px-6 py-5">
      <p class="text-sm text-zinc-600 mb-4">{{ descricao }}</p>
      <label class="text-xs font-medium text-zinc-700 block mb-1.5">PIN do gerente</label>
      <div class="relative">
        <input
          ref="pinInputRef"
          v-model="pin"
          :type="showPin ? 'text' : 'password'"
          class="w-full border border-zinc-200 rounded-lg px-3 py-2.5 pr-10 bg-zinc-50 text-sm text-zinc-800 focus:outline-none focus:ring-2 focus:ring-brand-primary/30"
          placeholder="Digite o PIN..."
          autofocus
          @keydown="handleKeydown"
        />
        <button
          type="button"
          class="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
          @click="showPin = !showPin"
        >
          <component :is="showPin ? EyeOff : Eye" :size="15" />
        </button>
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-end gap-3">
        <BaseButton variant="secondary" size="md" @click="handleCancelar">Cancelar</BaseButton>
        <BaseButton
          variant="primary"
          size="md"
          :loading="isLoading"
          :disabled="!pin.trim()"
          @click="handleConfirmar"
        >
          Confirmar
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
