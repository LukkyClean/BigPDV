<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  TIPOS_DANO,
  corPorTipo,
  type TipoDano,
  type MarcaDano,
} from '../types/mapeamentoDanos.types'
import SeletorTipoDano from './danos/SeletorTipoDano.vue'

import imgVistoria from '../assets/vistoria-carro.png'

interface Props {
  marcas: MarcaDano[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:marcas': [value: MarcaDano[]]
}>()

const showSeletor = ref(false)
const pendingCoord = ref<{ x: number; y: number } | null>(null)
const editandoMarca = ref<MarcaDano | undefined>(undefined)

function handleTap(event: MouseEvent | TouchEvent) {
  if (showSeletor.value) return
  const img = (event.currentTarget as HTMLElement).querySelector('img')
  if (!img) return
  const rect = img.getBoundingClientRect()

  let clientX: number, clientY: number
  if ('touches' in event && event.touches.length > 0) {
    clientX = event.touches[0].clientX
    clientY = event.touches[0].clientY
  } else if ('clientX' in event) {
    clientX = event.clientX
    clientY = event.clientY
  } else {
    return
  }

  const x = ((clientX - rect.left) / rect.width) * 100
  const y = ((clientY - rect.top) / rect.height) * 100

  pendingCoord.value = { x, y }
  editandoMarca.value = undefined
  showSeletor.value = true
}

function confirmarMarca(tipo: TipoDano, observacao: string) {
  if (editandoMarca.value) {
    const atualizadas = props.marcas.map((m) =>
      m.id === editandoMarca.value!.id
        ? { ...m, tipo, observacao: observacao || undefined }
        : m,
    )
    emit('update:marcas', atualizadas)
  } else if (pendingCoord.value) {
    const nova: MarcaDano = {
      id: self.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      x: pendingCoord.value.x,
      y: pendingCoord.value.y,
      tipo,
      observacao: observacao || undefined,
    }
    emit('update:marcas', [...props.marcas, nova])
  }
  fecharSeletor()
}

function editarMarca(marca: MarcaDano) {
  editandoMarca.value = marca
  pendingCoord.value = null
  showSeletor.value = true
}

function removerMarca(id: string) {
  emit('update:marcas', props.marcas.filter((m) => m.id !== id))
}

function fecharSeletor() {
  showSeletor.value = false
  pendingCoord.value = null
  editandoMarca.value = undefined
}

function labelTipo(tipo: TipoDano): string {
  return TIPOS_DANO.find((t) => t.value === tipo)?.label ?? tipo
}

const contagemPorTipo = computed(() => {
  const map: Partial<Record<TipoDano, number>> = {}
  for (const m of props.marcas) {
    map[m.tipo] = (map[m.tipo] ?? 0) + 1
  }
  return map
})
</script>

<template>
  <section class="space-y-3">
    <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wide">
      Mapeamento de Danos
    </h3>

    <!-- Container da imagem -->
    <div class="relative border border-slate-200 rounded-xl select-none overflow-hidden bg-white">
      <div class="relative" @click="handleTap">
        <img
          :src="imgVistoria"
          alt="Diagrama de vistoria do veículo"
          class="w-full h-auto pointer-events-none select-none"
          draggable="false"
        />

        <!-- Marcadores -->
        <svg
          class="absolute inset-0 w-full h-full pointer-events-none"
          viewBox="0 0 1000 750"
          preserveAspectRatio="none"
        >
          <g
            v-for="m in marcas"
            :key="m.id"
            class="pointer-events-auto cursor-pointer"
            @click.stop="editarMarca(m)"
          >
            <circle
              :cx="m.x * 10"
              :cy="m.y * 7.5"
              r="16"
              fill="black"
              fill-opacity="0.12"
            />
            <circle
              :cx="m.x * 10"
              :cy="m.y * 7.5"
              r="12"
              :fill="corPorTipo(m.tipo)"
              stroke="white"
              stroke-width="3"
            />
            <circle
              :cx="m.x * 10"
              :cy="m.y * 7.5"
              r="4"
              fill="white"
            />
          </g>
        </svg>
      </div>

      <p v-if="marcas.length === 0" class="text-xs text-slate-400 text-center py-2">
        Toque sobre o veículo para marcar um dano
      </p>
    </div>

    <!-- Legenda com contagem -->
    <div v-if="marcas.length > 0" class="flex flex-wrap gap-3">
      <span
        v-for="t in TIPOS_DANO"
        :key="t.value"
        class="flex items-center gap-1.5 text-xs text-slate-500"
      >
        <span class="w-3 h-3 rounded-full" :style="{ backgroundColor: t.cor }" />
        {{ t.label }}
        <span v-if="contagemPorTipo[t.value]" class="text-slate-400">({{ contagemPorTipo[t.value] }})</span>
      </span>
    </div>

    <!-- Lista de marcadores -->
    <div v-if="marcas.length > 0" class="space-y-2">
      <div
        v-for="(m, idx) in marcas"
        :key="m.id"
        class="flex items-center gap-2.5 p-3 bg-white border border-slate-200 rounded-xl"
      >
        <span class="w-4 h-4 rounded-full shrink-0" :style="{ backgroundColor: corPorTipo(m.tipo) }" />
        <span class="text-slate-400 text-xs font-mono w-5 shrink-0">{{ idx + 1 }}</span>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-slate-700">{{ labelTipo(m.tipo) }}</p>
          <p v-if="m.observacao" class="text-xs text-slate-400 truncate">{{ m.observacao }}</p>
        </div>
        <div class="flex items-center gap-1 shrink-0">
          <button
            type="button"
            class="w-9 h-9 flex items-center justify-center rounded-lg bg-slate-50 text-slate-400 active:bg-slate-100"
            @click.stop="editarMarca(m)"
          >
            ✎
          </button>
          <button
            type="button"
            class="w-9 h-9 flex items-center justify-center rounded-lg bg-slate-50 text-red-400 active:bg-red-50"
            @click.stop="removerMarca(m.id)"
          >
            ✕
          </button>
        </div>
      </div>
    </div>

    <!-- Bottom sheet seletor -->
    <SeletorTipoDano
      v-if="showSeletor"
      :marca="editandoMarca"
      @confirmar="confirmarMarca"
      @cancelar="fecharSeletor"
    />
  </section>
</template>
