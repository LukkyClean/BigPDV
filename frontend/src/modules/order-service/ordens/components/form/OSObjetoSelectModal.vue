<script setup lang="ts">
import { computed } from 'vue';
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { ChevronRight, X } from 'lucide-vue-next';
import type { ObjetoHistorico } from '@/modules/customers/types/clientes.types';
import { useObjetoLabels } from '@/modules/order-service/shared/segmento/useObjetoLabels';

interface Props {
  isOpen: boolean;
  objetos: ObjetoHistorico[];
}

defineProps<Props>();

const emit = defineEmits<{
  close: [];
  select: [objeto: ObjetoHistorico];
}>();

// Ícone e rótulos vêm do segmento (oficina → Veículo/Placa/Car; informática →
// Equipamento/Nº de Série/Smartphone; novos segmentos herdam sem mexer aqui).
const { objetoIcon, labelSingular, labelPlural, labelIdentificador } = useObjetoLabels();

const titulo = computed(() => `${labelSingular.value} já cadastrado?`);
const subtitulo = computed(
  () => `Este cliente já trouxe ${labelPlural.value.toLowerCase()} antes. `
    + `Selecione um para agilizar o cadastro ou continue com um novo.`,
);
const rotuloNovo = computed(() => `Não, é um novo ${labelSingular.value.toLowerCase()}`);

function nomeObjeto(objeto: ObjetoHistorico): string {
  return [objeto.marca, objeto.modelo].filter(Boolean).join(' ') || objeto.objeto || labelSingular.value;
}

function handleSelect(objeto: ObjetoHistorico) {
  emit('select', objeto);
}

function handleSkip() {
  emit('close');
}
</script>

<template>
  <BaseModal
    :is-open="isOpen"
    :title="titulo"
    :subtitle="subtitulo"
    size="lg"
    @close="handleSkip"
  >
    <div class="space-y-4 max-h-100 overflow-y-auto px-1 custom-scrollbar">
      <button
        v-for="(objeto, idx) in objetos"
        :key="idx"
        type="button"
        class="w-full bg-white border border-slate-200 rounded-xl p-4 flex items-center justify-between hover:border-brand-primary hover:bg-brand-primary-light group transition-all text-left shadow-sm cursor-pointer"
        @click="handleSelect(objeto)"
      >
        <div class="flex items-center gap-4">
          <div class="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 group-hover:bg-brand-primary-light group-hover:text-brand-primary transition-colors">
            <component :is="objetoIcon" :size="20" />
          </div>
          <div>
            <h4 class="font-bold text-slate-800 text-sm group-hover:text-brand-primary">{{ nomeObjeto(objeto) }}</h4>
            <div class="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
              <span
                v-if="objeto.numero_serie"
                class="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-600 group-hover:bg-brand-primary/20 group-hover:text-brand-primary/80"
              >
                {{ labelIdentificador }}: {{ objeto.numero_serie }}
              </span>
            </div>
          </div>
        </div>
        <div class="text-slate-300 group-hover:text-brand-primary">
          <ChevronRight :size="20" />
        </div>
      </button>
    </div>

    <template #footer>
      <div class="flex justify-between w-full">
        <BaseButton variant="secondary" @click="handleSkip">
          <X :size="16" class="mr-2" />
          {{ rotuloNovo }}
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: #e4e4e7; border-radius: 20px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background-color: #d4d4d8; }
</style>
