<script setup lang="ts">
import { ref, computed } from 'vue'
import { Pencil, Trash2, MapPin } from 'lucide-vue-next'
import {
  TIPOS_DANO,
  corPorTipo,
  type TipoDano,
  type MarcaDano,
} from '../../../types/mapeamentoDanos.types'
import SeletorTipoDano from './SeletorTipoDano.vue'

import imgVistoria from '../../../assets/vistoria-carro.png'

interface Props {
  marcas: MarcaDano[]
  isLocked?: boolean
}

const props = withDefaults(defineProps<Props>(), { isLocked: false })

const emit = defineEmits<{
  'update:marcas': [value: MarcaDano[]]
}>()

// --- Estado do seletor ---
const showSeletor = ref(false)
const seletorPos = ref({ x: 0, y: 0 })
const pendingCoord = ref<{ x: number; y: number } | null>(null)
const editandoMarca = ref<MarcaDano | undefined>(undefined)

function handleImageClick(event: MouseEvent) {
  if (props.isLocked || showSeletor.value) return
  const img = (event.currentTarget as HTMLElement).querySelector('img')
  if (!img) return
  const rect = img.getBoundingClientRect()
  const x = ((event.clientX - rect.left) / rect.width) * 100
  const y = ((event.clientY - rect.top) / rect.height) * 100

  pendingCoord.value = { x, y }
  editandoMarca.value = undefined

  // Posição fixa no viewport (Teleport para body)
  const popoverW = 288 // largura do SeletorTipoDano (~w-72)
  const popoverH = 260 // altura estimada do SeletorTipoDano
  let left = event.clientX + 10
  let top = event.clientY + 10
  // Evitar que saia pela direita
  if (left + popoverW > window.innerWidth) left = event.clientX - popoverW - 10
  // Evitar que saia por baixo
  if (top + popoverH > window.innerHeight) top = event.clientY - popoverH - 10
  seletorPos.value = { x: left, y: top }
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
      id: crypto.randomUUID(),
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
  if (props.isLocked) return
  editandoMarca.value = marca
  pendingCoord.value = null
  showSeletor.value = true
}

function removerMarca(id: string) {
  if (props.isLocked) return
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

/** Contagem por tipo para o badge na legenda. */
const contagemPorTipo = computed(() => {
  const map: Partial<Record<TipoDano, number>> = {}
  for (const m of props.marcas) {
    map[m.tipo] = (map[m.tipo] ?? 0) + 1
  }
  return map
})
</script>

<template>
  <div class="space-y-3">
    <!-- Container da imagem + marcadores -->
    <div
      class="relative border border-slate-200 rounded-lg select-none bg-white"
      :class="{ 'cursor-crosshair': !isLocked }"
    >
      <div class="relative" @click="handleImageClick">
        <!-- Diagrama do veículo -->
        <img
          :src="imgVistoria"
          alt="Diagrama de vistoria do veículo — vista superior, laterais, frente e traseira"
          class="w-full h-auto pointer-events-none select-none"
          draggable="false"
        />

        <!-- Camada de marcadores SVG -->
        <svg
          class="absolute inset-0 w-full h-full pointer-events-none"
          viewBox="0 0 1000 750"
          preserveAspectRatio="none"
        >
          <g
            v-for="m in marcas"
            :key="m.id"
            :class="isLocked ? 'pointer-events-none' : 'pointer-events-auto cursor-pointer'"
            @click.stop="editarMarca(m)"
          >
            <!-- Sombra -->
            <circle
              :cx="m.x * 10"
              :cy="m.y * 7.5"
              r="14"
              fill="black"
              fill-opacity="0.12"
            />
            <!-- Marcador -->
            <circle
              :cx="m.x * 10"
              :cy="m.y * 7.5"
              r="10"
              :fill="corPorTipo(m.tipo)"
              stroke="white"
              stroke-width="2.5"
            />
            <!-- Ponto central -->
            <circle
              :cx="m.x * 10"
              :cy="m.y * 7.5"
              r="3.5"
              fill="white"
            />
          </g>
        </svg>
      </div>

    </div>

    <!-- Seletor via Teleport (sobrepõe qualquer elemento, inclusive footer do modal) -->
    <Teleport to="body">
      <!-- Backdrop invisível para fechar ao clicar fora -->
      <div v-if="showSeletor" class="fixed inset-0 z-9998" @click="fecharSeletor" />
      <div
        v-if="showSeletor"
        class="fixed z-9999"
        :style="editandoMarca
          ? { left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }
          : { left: `${seletorPos.x}px`, top: `${seletorPos.y}px` }"
      >
        <SeletorTipoDano
          :marca="editandoMarca"
          @confirmar="confirmarMarca"
          @cancelar="fecharSeletor"
        />
      </div>
    </Teleport>

    <!-- Instrução -->
    <p v-if="!isLocked && marcas.length === 0" class="text-xs text-slate-400 text-center">
      <MapPin :size="12" class="inline -mt-0.5" />
      Clique sobre o veículo para marcar a localização de um dano
    </p>

    <!-- Legenda com contagem -->
    <div v-if="marcas.length > 0" class="flex flex-wrap gap-3">
      <span
        v-for="t in TIPOS_DANO"
        :key="t.value"
        class="flex items-center gap-1.5 text-xs text-slate-500"
      >
        <span class="w-2.5 h-2.5 rounded-full" :style="{ backgroundColor: t.cor }" />
        {{ t.label }}
        <span v-if="contagemPorTipo[t.value]" class="text-slate-400">({{ contagemPorTipo[t.value] }})</span>
      </span>
    </div>

    <!-- Lista de marcadores -->
    <div v-if="marcas.length > 0" class="space-y-1.5">
      <div
        v-for="(m, idx) in marcas"
        :key="m.id"
        class="flex items-center gap-2 p-2 bg-white border border-slate-200 rounded-lg text-sm"
      >
        <span class="w-3 h-3 rounded-full shrink-0" :style="{ backgroundColor: corPorTipo(m.tipo) }" />
        <span class="text-slate-400 text-xs font-mono w-5 shrink-0">{{ idx + 1 }}</span>
        <span class="font-medium text-slate-700">{{ labelTipo(m.tipo) }}</span>
        <span v-if="m.observacao" class="text-slate-400 text-xs truncate">— {{ m.observacao }}</span>
        <div v-if="!isLocked" class="ml-auto flex items-center gap-1 shrink-0">
          <button
            type="button"
            title="Editar"
            class="p-1 rounded hover:bg-slate-100 text-slate-400 hover:text-brand-primary transition-colors"
            @click="editarMarca(m)"
          >
            <Pencil :size="14" />
          </button>
          <button
            type="button"
            title="Remover"
            class="p-1 rounded hover:bg-red-50 text-slate-400 hover:text-red-500 transition-colors"
            @click="removerMarca(m.id)"
          >
            <Trash2 :size="14" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
