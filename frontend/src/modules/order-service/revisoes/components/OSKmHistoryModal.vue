<script setup lang="ts">
import { computed } from 'vue';
import { Gauge, Loader2 } from 'lucide-vue-next';
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';

import { useHistoricoKm } from '../composables/useRevisao.queries';

interface Props {
  isOpen: boolean;
  objetoId: number | null;
  veiculoLabel?: string;
}

const props = withDefaults(defineProps<Props>(), {
  objetoId: null,
  veiculoLabel: '',
});

defineEmits<{ close: [] }>();

const objetoIdRef = computed(() => (props.isOpen ? props.objetoId : null));
const { data: historico, isLoading } = useHistoricoKm(objetoIdRef);

const linhas = computed(() => historico.value ?? []);

function formatarData(d: string): string {
  return new Date(d).toLocaleDateString('pt-BR');
}

function formatarKm(km: number): string {
  return `${km.toLocaleString('pt-BR')} km`;
}

/** Diferença de KM em relação ao registro anterior (rodados entre visitas). */
function delta(index: number): number | null {
  if (index === 0) return null;
  return linhas.value[index].km_entrada - linhas.value[index - 1].km_entrada;
}
</script>

<template>
  <BaseModal :is-open="isOpen" title="Histórico de KM" size="md" @close="$emit('close')">
    <div class="space-y-4">
      <div class="flex items-center gap-3 border-b border-slate-200 pb-3">
        <div class="bg-brand-primary-light p-2 rounded-lg text-brand-primary">
          <Gauge :size="20" />
        </div>
        <div class="min-w-0">
          <h5 class="text-sm font-bold text-slate-700 truncate">{{ veiculoLabel || 'Veículo' }}</h5>
          <p class="text-xs text-slate-500">Quilometragem registrada nas OS</p>
        </div>
      </div>

      <div v-if="isLoading" class="flex items-center justify-center py-10 text-slate-400">
        <Loader2 :size="20" class="animate-spin" />
      </div>

      <div
        v-else-if="linhas.length === 0"
        class="flex flex-col items-center justify-center py-10 text-slate-400 border-2 border-dashed border-slate-200 rounded-xl bg-slate-50/50"
      >
        <div class="w-14 h-14 bg-slate-100 rounded-full flex items-center justify-center mb-3">
          <Gauge :size="28" stroke-width="1.5" class="text-slate-300" />
        </div>
        <p class="text-sm font-semibold text-slate-500">Sem histórico de KM</p>
        <p class="text-xs text-slate-400 mt-1">Nenhuma OS deste veículo registrou quilometragem.</p>
      </div>

      <div v-else class="space-y-2">
        <div
          v-for="(linha, index) in linhas"
          :key="linha.numero_os"
          class="flex items-center justify-between p-3 bg-white border border-slate-200 rounded-lg"
        >
          <div class="min-w-0">
            <p class="text-sm font-bold text-slate-700">{{ formatarKm(linha.km_entrada) }}</p>
            <p class="text-xs text-slate-500 truncate">{{ linha.numero_os }} · {{ formatarData(linha.data) }}</p>
          </div>
          <span
            v-if="delta(index) !== null"
            class="text-xs font-bold text-emerald-600 shrink-0"
          >
            +{{ (delta(index) as number).toLocaleString('pt-BR') }} km
          </span>
        </div>
      </div>
    </div>
  </BaseModal>
</template>
