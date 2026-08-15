<script setup lang="ts">
import { Eye, Pencil, Power, Box, AlertTriangle, Plus, Minus } from 'lucide-vue-next';
import { computed } from 'vue';

interface Props {
  id: number;
  name: string;
  description: string;
  category: string;
  price: number;
  storage: number;
  image_url: string;
  status: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: 'view', id: number): void;
  (e: 'edit', id: number): void;
  (e: 'toggle', id: number): void;
  (e: 'entrada', id: number): void;
  (e: 'saida', id: number): void;
}>();

const stockStatus = computed(() => {
  if (!props.status) {
    return {
      icon: Box,
      label: 'INATIVO',
      class: 'bg-gray-500',
    };
  } else if (props.storage === 0) {
    return {
      icon: Box,
      label: 'SEM ESTOQUE',
      class: 'bg-red-500',
    };
  } else if (props.storage <= 10) {
    return {
      icon: AlertTriangle,
      label: 'BAIXO ESTOQUE',
      class: 'bg-amber-500',
    };
  }
  return null;
});

const formattedPrice = computed(() => {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(props.price).replace(/\s/g, ' ');
});

const stockDisplay = computed(() => {
  return props.storage === 0 ? '0 un' : `${props.storage} un`;
});

const stockTextColor = computed(() => {
  if (props.storage === 0) return 'text-red-600';
  if (props.storage <= 10) return 'text-amber-600';
  return 'text-gray-600';
});

const isInactive = computed(() => !props.status);
</script>

<template>
  <div
    class="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 border border-gray-100 group"
  >
    <!-- Image Container -->
    <div class="relative w-full h-48 bg-linear-to-br from-gray-50 to-gray-100 overflow-hidden">
      <img
        v-if="image_url"
        :src="image_url"
        :alt="name"
        class="w-full h-full object-contain p-4 transition-transform duration-300 group-hover:scale-105"
      />
      <div v-else class="w-full h-full flex flex-col items-center justify-center text-gray-300">
        <Box :size="48" class="mb-2" />
        <span class="text-xs font-medium text-gray-400">Sem imagem</span>
      </div>

      <!-- Stock Status Badge -->
      <div
        v-if="stockStatus"
        class="absolute top-3 right-3 px-3 py-1.5 rounded-full text-white text-xs font-bold tracking-wide shadow-lg"
        :class="stockStatus.class"
      >
        <div class="flex items-center gap-2">
          <component v-if="stockStatus.icon" :is="stockStatus.icon" :size="12" />
          {{ stockStatus.label }}
        </div>
      </div>
    </div>

    <!-- Card Content -->
    <div class="p-5 space-y-3">
      <!-- Category Badge -->
      <span
        class="inline-block px-3 py-1 bg-brand-primary/10 text-brand-primary text-xs font-semibold uppercase tracking-wide rounded-md border border-brand-primary/30"
      >
        {{ category }}
      </span>

      <!-- Product Name -->
      <h3 class="text-lg font-bold text-gray-900 line-clamp-1 mt-2">
        {{ name }}
      </h3>

      <!-- Product Description -->
      <p class="text-sm text-gray-600 line-clamp-2 min-h-10">
        {{ description }}
      </p>

      <!-- Price and Stock -->
      <div class="flex justify-between items-end pt-3 pb-2 border-t border-gray-100">
        <div>
          <p class="text-xs font-semibold text-gray-500 tracking-wide mb-1">PREÇO</p>
          <p class="text-xl font-bold text-gray-900">{{ formattedPrice }}</p>
        </div>
        <div class="text-right">
          <p class="text-xs font-semibold text-gray-500 tracking-wide mb-1">ESTOQUE</p>
          <p class="text-lg font-bold" :class="stockTextColor">{{ stockDisplay }}</p>
        </div>
      </div>

      <!-- Entrada / Saída rápida -->
      <div class="flex gap-2 pt-2">
        <button
          class="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 border bg-brand-primary text-white border-blue-500 hover:bg-brand-primary-hover hover:border-brand-primary-hover hover:shadow-lg hover:shadow-blue-200 cursor-pointer"
          title="Registrar entrada"
          :disabled="isInactive"
          @click="emit('entrada', id)"
        >
          <Plus :size="15" />
          Entrada
        </button>
        <button
          class="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 border bg-red-50 text-red-600 border-red-200 hover:bg-red-500 hover:text-white hover:border-red-500 hover:shadow-lg hover:shadow-red-100 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          title="Registrar saída"
          :disabled="isInactive || storage === 0"
          @click="emit('saida', id)"
        >
          <Minus :size="15" />
          Saída
        </button>
      </div>

      <!-- Ações secundárias -->
      <div class="flex gap-2">
        <button
          class="flex-1 flex items-center justify-center py-2 rounded-lg font-medium transition-all duration-200 border bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100 hover:border-gray-300 hover:shadow-md cursor-pointer"
          title="Visualizar"
          @click="emit('view', id)"
        >
          <Eye :size="16" />
        </button>
        <button
          class="flex-1 flex items-center justify-center py-2 rounded-lg font-medium transition-all duration-200 border bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100 hover:border-gray-300 hover:shadow-md cursor-pointer"
          title="Editar"
          @click="emit('edit', id)"
        >
          <Pencil :size="16" />
        </button>
        <button
          class="flex-1 flex items-center justify-center py-2 rounded-lg font-medium transition-all duration-200 border bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100 hover:border-gray-300 hover:shadow-md cursor-pointer"
          :title="isInactive ? 'Ativar' : 'Desativar'"
          @click="emit('toggle', id)"
        >
          <Power :size="16" />
        </button>
      </div>
    </div>
  </div>
</template>
