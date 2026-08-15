<script setup lang="ts">
import type { SegmentInspectionGroup } from '../types/checklist.types'

interface Props {
  grupos: SegmentInspectionGroup[]
  selecionados: Record<string, string>
}

const props = defineProps<Props>()
const emit = defineEmits<{ 'update:selecionados': [value: Record<string, string>] }>()

const ESTADOS: { value: string; label: string; selected: string }[] = [
  { value: 'OK', label: 'OK', selected: 'bg-emerald-500 text-white border-emerald-500' },
  { value: 'N_OK', label: 'N/OK', selected: 'bg-amber-500 text-white border-amber-500' },
  { value: 'REPARAR', label: 'Reparar', selected: 'bg-red-500 text-white border-red-500' },
]

function rotulo(slug: string): string {
  const s = slug.replace(/_/g, ' ')
  return s.charAt(0).toUpperCase() + s.slice(1)
}

function chaveItem(grupoIdx: number, item: string): string {
  return `${grupoIdx}_${item}`
}

function setEstado(grupoIdx: number, item: string, estado: string) {
  const key = chaveItem(grupoIdx, item)
  const atual = props.selecionados[key]
  const novos = { ...props.selecionados, [key]: atual === estado ? '' : estado }
  emit('update:selecionados', novos)
}
</script>

<template>
  <section v-for="(grupo, gi) in grupos" :key="grupo.titulo" class="space-y-3">
    <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wide">
      {{ grupo.titulo }}
    </h3>

    <div class="space-y-2">
      <div
        v-for="item in grupo.itens"
        :key="item"
        class="flex flex-col gap-2 p-3 bg-white border border-slate-200 rounded-lg"
      >
        <p class="text-sm font-medium text-slate-700">{{ rotulo(item) }}</p>
        <div class="flex gap-1.5">
          <button
            v-for="estado in ESTADOS"
            :key="estado.value"
            type="button"
            class="flex-1 py-2.5 text-xs font-bold rounded-lg border transition-colors min-h-[44px]"
            :class="selecionados[chaveItem(gi, item)] === estado.value
              ? estado.selected
              : 'bg-slate-50 border-slate-200 text-slate-400 active:bg-slate-100'"
            @click="setEstado(gi, item, estado.value)"
          >
            {{ estado.label }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
