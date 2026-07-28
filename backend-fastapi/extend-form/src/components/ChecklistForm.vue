<script setup lang="ts">
import type { SegmentDefinition } from '../types/checklist.types'
import type { MarcaDano } from '../types/mapeamentoDanos.types'
import CheckinSection from './CheckinSection.vue'
import AcessoriosSection from './AcessoriosSection.vue'
import VistoriaSection from './VistoriaSection.vue'
import MapeamentoDanosSection from './MapeamentoDanosSection.vue'

interface Props {
  definicao: SegmentDefinition
  dadosAdicionais: Record<string, unknown>
  isSubmitting: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:dadosAdicionais': [value: Record<string, unknown>]
  submit: []
}>()

function patch(partial: Record<string, unknown>) {
  emit('update:dadosAdicionais', { ...props.dadosAdicionais, ...partial })
}
</script>

<template>
  <form @submit.prevent="emit('submit')" class="space-y-6 pb-24">
    <!-- Check-in: combustivel, pneus, estepe, KM etc -->
    <CheckinSection
      :campos="definicao.checkin"
      :dados="dadosAdicionais"
      @update="patch"
    />

    <!-- Acessorios presentes -->
    <AcessoriosSection
      v-if="definicao.acessorios.length"
      :acessorios="definicao.acessorios"
      :selecionados="(dadosAdicionais.acessorios as Record<string, boolean>) ?? {}"
      :outros-texto="(dadosAdicionais.acessorios_outros as string) ?? ''"
      @update:selecionados="patch({ acessorios: $event })"
      @update:outros-texto="patch({ acessorios_outros: $event })"
    />

    <!-- Grupos de inspecao -->
    <VistoriaSection
      v-if="definicao.vistoria.length"
      :grupos="definicao.vistoria"
      :selecionados="(dadosAdicionais.vistoria as Record<string, string>) ?? {}"
      @update:selecionados="patch({ vistoria: $event })"
    />

    <!-- Mapeamento de danos -->
    <MapeamentoDanosSection
      v-if="definicao.vistoria.length"
      :marcas="(dadosAdicionais.mapeamento_danos as MarcaDano[]) ?? []"
      @update:marcas="patch({ mapeamento_danos: $event })"
    />

    <!-- Submit fixo no rodape -->
    <div class="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 p-4 shadow-lg">
      <div class="max-w-xl mx-auto">
        <button
          type="submit"
          :disabled="isSubmitting"
          class="w-full py-3.5 bg-brand-primary text-white text-sm font-bold rounded-xl transition-colors disabled:opacity-60 active:bg-brand-primary/90"
        >
          <span v-if="isSubmitting" class="flex items-center justify-center gap-2">
            <span class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Enviando...
          </span>
          <span v-else>Enviar Checklist</span>
        </button>
      </div>
    </div>
  </form>
</template>
