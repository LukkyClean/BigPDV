<script setup lang="ts">
import type { SegmentField } from '../types/checklist.types'

interface Props {
  campos: SegmentField[]
  dados: Record<string, unknown>
}

const props = defineProps<Props>()
const emit = defineEmits<{ update: [partial: Record<string, unknown>] }>()

/** Campos de opcao (botoes selecionaveis). */
function camposOpcao() {
  return props.campos.filter(c => c.tipo === 'opcao' && c.opcoes?.length)
}

/** Campos de texto/numero (inputs). */
function camposInput() {
  return props.campos.filter(c => c.tipo !== 'opcao')
}

function valorAtual(nome: string): string {
  return (props.dados[nome] as string) ?? ''
}

function setValor(nome: string, valor: string) {
  const atual = valorAtual(nome)
  emit('update', { [nome]: atual === valor ? '' : valor })
}

function setInput(nome: string, valor: string | number) {
  emit('update', { [nome]: valor })
}

function rotuloOpcao(op: string): string {
  return op.charAt(0) + op.slice(1).toLowerCase()
}
</script>

<template>
  <section class="space-y-3">
    <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wide">
      Estado do Veiculo
    </h3>

    <!-- Campos de input (texto/numero/inteiro) -->
    <div v-for="campo in camposInput()" :key="campo.nome" class="space-y-1">
      <label class="text-sm font-medium text-slate-600">{{ campo.label }}</label>
      <input
        :type="campo.tipo === 'inteiro' || campo.tipo === 'numero' ? 'number' : 'text'"
        :value="valorAtual(campo.nome)"
        :placeholder="campo.label"
        class="w-full px-3 py-2.5 text-sm rounded-lg border border-slate-200 focus:border-brand-primary focus:outline-none bg-white"
        @input="setInput(campo.nome, campo.tipo === 'inteiro' ? parseInt(($event.target as HTMLInputElement).value) || '' : ($event.target as HTMLInputElement).value)"
      />
    </div>

    <!-- Campos de opcao (botoes toggle) -->
    <div
      v-for="campo in camposOpcao()"
      :key="campo.nome"
      class="flex flex-col gap-2 p-3 bg-white border border-slate-200 rounded-lg"
    >
      <p class="text-sm font-medium text-slate-700">{{ campo.label }}</p>
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="op in campo.opcoes"
          :key="op"
          type="button"
          class="px-3 py-2 text-xs font-bold rounded-lg border transition-colors min-h-[44px]"
          :class="valorAtual(campo.nome) === op
            ? 'bg-brand-primary text-white border-brand-primary'
            : 'bg-slate-50 border-slate-200 text-slate-500 active:bg-slate-100'"
          @click="setValor(campo.nome, op)"
        >
          {{ rotuloOpcao(op) }}
        </button>
      </div>
    </div>
  </section>
</template>
