<script setup lang="ts">
import { ref, watch } from 'vue'
import { X } from 'lucide-vue-next'
import { TIPOS_DANO, type TipoDano, type MarcaDano } from '../../../types/mapeamentoDanos.types'

interface Props {
  /** Marca existente para modo edição. Se undefined, é criação. */
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
  <div class="bg-white border border-slate-200 rounded-xl shadow-lg p-4 space-y-3 w-72 z-50">
    <div class="flex items-center justify-between">
      <h6 class="text-sm font-bold text-slate-700">
        {{ marca ? 'Editar dano' : 'Tipo de dano' }}
      </h6>
      <button
        type="button"
        class="p-1 rounded hover:bg-slate-100 text-slate-400"
        @click="emit('cancelar')"
      >
        <X :size="16" />
      </button>
    </div>

    <div class="grid grid-cols-2 gap-1.5">
      <button
        v-for="t in TIPOS_DANO"
        :key="t.value"
        type="button"
        class="flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-semibold transition-colors text-left"
        :class="tipoSelecionado === t.value
          ? 'border-slate-700 bg-slate-50 text-slate-800'
          : 'border-slate-200 text-slate-500 hover:border-slate-300'"
        @click="tipoSelecionado = t.value"
      >
        <span class="w-3 h-3 rounded-full shrink-0" :style="{ backgroundColor: t.cor }" />
        {{ t.label }}
      </button>
    </div>

    <input
      v-model="observacao"
      type="text"
      placeholder="Observação (opcional)"
      maxlength="120"
      class="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 focus:border-brand-primary focus:outline-none"
    />

    <div class="flex gap-2">
      <button
        type="button"
        class="flex-1 py-2 text-xs font-semibold rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 transition-colors"
        @click="emit('cancelar')"
      >
        Cancelar
      </button>
      <button
        type="button"
        :disabled="!tipoSelecionado"
        class="flex-1 py-2 text-xs font-bold rounded-lg bg-brand-primary text-white disabled:opacity-40 transition-colors hover:bg-brand-primary/90"
        @click="confirmar"
      >
        {{ marca ? 'Salvar' : 'Marcar' }}
      </button>
    </div>
  </div>
</template>
