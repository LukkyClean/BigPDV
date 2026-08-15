<script setup lang="ts">

interface Props {
  acessorios: string[]
  selecionados: Record<string, boolean>
  outrosTexto: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:selecionados': [value: Record<string, boolean>]
  'update:outrosTexto': [value: string]
}>()

function rotulo(slug: string): string {
  const s = slug.replace(/_/g, ' ')
  return s.charAt(0).toUpperCase() + s.slice(1)
}

function toggle(key: string) {
  const novoValor = !props.selecionados[key]
  const novos = { ...props.selecionados, [key]: novoValor }

  // Ao desmarcar "outros", limpa a descricao
  if (key === 'outros' && !novoValor) {
    emit('update:outrosTexto', '')
  }

  emit('update:selecionados', novos)
}
</script>

<template>
  <section class="space-y-3">
    <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wide">
      Acessorios Presentes
    </h3>

    <div class="grid grid-cols-2 gap-2">
      <button
        v-for="ac in acessorios"
        :key="ac"
        type="button"
        class="flex items-center gap-2.5 p-3 rounded-lg border text-sm text-left transition-colors min-h-[44px]"
        :class="selecionados[ac]
          ? 'bg-blue-50 border-brand-primary/30 text-brand-primary font-semibold'
          : 'bg-white border-slate-200 text-slate-600 active:bg-slate-50'"
        @click="toggle(ac)"
      >
        <span
          class="w-5 h-5 rounded flex items-center justify-center shrink-0 border-2 transition-colors"
          :class="selecionados[ac]
            ? 'bg-brand-primary border-brand-primary text-white'
            : 'border-slate-300 bg-white'"
        >
          <svg v-if="selecionados[ac]" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </span>
        {{ rotulo(ac) }}
      </button>
    </div>

    <!-- Descricao livre para "Outros" -->
    <input
      v-if="selecionados['outros']"
      type="text"
      :value="outrosTexto"
      placeholder="Descreva os outros acessorios..."
      maxlength="120"
      class="w-full px-3 py-2.5 text-sm rounded-lg border border-slate-200 focus:border-brand-primary focus:outline-none bg-white"
      @input="emit('update:outrosTexto', ($event.target as HTMLInputElement).value)"
    />
  </section>
</template>
