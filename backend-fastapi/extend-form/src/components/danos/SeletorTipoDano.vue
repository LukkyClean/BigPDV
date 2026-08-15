<script setup lang="ts">
import { ref, watch } from 'vue'
import { TIPOS_DANO, type TipoDano, type MarcaDano } from '../../types/mapeamentoDanos.types'

interface Props {
  marca?: MarcaDano
}

const props = defineProps<Props>()

const emit = defineEmits<{
  confirmar: [tipo: TipoDano, observacao: string]
  cancelar: []
}>()

const tipoSelecionado = ref<TipoDano | null>(null)
const observacao = ref('')

watch(
  () => props.marca,
  (m) => {
    if (m) {
      tipoSelecionado.value = m.tipo
      observacao.value = m.observacao ?? ''
    } else {
      tipoSelecionado.value = null
      observacao.value = ''
    }
  },
  { immediate: true },
)

function confirmar() {
  if (!tipoSelecionado.value) return
  emit('confirmar', tipoSelecionado.value, observacao.value.trim())
}
</script>

<template>
  <!-- Bottom sheet para mobile -->
  <div class="fixed inset-0 z-50 flex flex-col justify-end" @click.self="emit('cancelar')">
    <!-- Backdrop -->
    <div class="absolute inset-0 bg-black/30" @click="emit('cancelar')" />

    <!-- Sheet -->
    <div class="relative z-10 bg-white rounded-t-2xl p-5 space-y-4 animate-slide-up">
      <div class="flex items-center justify-between">
        <h3 class="text-base font-bold text-slate-700">
          {{ marca ? 'Editar dano' : 'Tipo de dano' }}
        </h3>
        <button
          type="button"
          class="w-8 h-8 flex items-center justify-center rounded-full bg-slate-100 text-slate-400"
          @click="emit('cancelar')"
        >
          ✕
        </button>
      </div>

      <div class="grid grid-cols-2 gap-2">
        <button
          v-for="t in TIPOS_DANO"
          :key="t.value"
          type="button"
          class="flex items-center gap-2.5 px-4 py-3 rounded-xl border text-sm font-semibold transition-colors min-h-12"
          :class="tipoSelecionado === t.value
            ? 'border-slate-700 bg-slate-50 text-slate-800'
            : 'border-slate-200 text-slate-500 active:bg-slate-50'"
          @click="tipoSelecionado = t.value"
        >
          <span class="w-4 h-4 rounded-full shrink-0" :style="{ backgroundColor: t.cor }" />
          {{ t.label }}
        </button>
      </div>

      <input
        v-model="observacao"
        type="text"
        placeholder="Observação (opcional)"
        maxlength="120"
        class="w-full px-4 py-3 text-sm rounded-xl border border-slate-200 focus:border-brand-primary focus:outline-none"
      />

      <div class="flex gap-3">
        <button
          type="button"
          class="flex-1 py-3 text-sm font-semibold rounded-xl border border-slate-200 text-slate-500 active:bg-slate-50"
          @click="emit('cancelar')"
        >
          Cancelar
        </button>
        <button
          type="button"
          :disabled="!tipoSelecionado"
          class="flex-1 py-3 text-sm font-bold rounded-xl bg-brand-primary text-white disabled:opacity-40 active:bg-brand-primary/90"
          @click="confirmar"
        >
          {{ marca ? 'Salvar' : 'Marcar' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.animate-slide-up {
  animation: slideUp 0.25s ease-out;
}
@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}
</style>
