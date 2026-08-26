<script setup lang="ts">
import { ref } from 'vue';
import { FlaskConical, Send } from 'lucide-vue-next';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';

import FiscalStats from '../components/FiscalStats.vue';
import FiscalDocumentosTable from '../components/FiscalDocumentosTable.vue';
import FiscalPendenciasPanel from '../components/FiscalPendenciasPanel.vue';
import FiscalEmitirTesteModal from '../components/FiscalEmitirTesteModal.vue';
import FiscalEmitirNFeModal from '../components/FiscalEmitirNFeModal.vue';
import { useFiscalResumoQuery } from '../composables/useFiscalResumoQuery';

interface Props {
  isHomologacao?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  isHomologacao: true,
});

const { data: resumo, isLoading: isResumoLoading } = useFiscalResumoQuery();

const showTesteModal = ref(false);
const showEmitirModal = ref(false);
</script>

<template>
  <div class="flex flex-col gap-6 flex-1 min-h-0">
    <!-- Header NF-e -->
    <div class="flex items-center justify-between">
      <h2 class="text-base font-semibold text-zinc-700">Notas Fiscais Eletrônicas</h2>
      <div class="flex items-center gap-2">
        <BaseButton
          v-if="isHomologacao"
          type="button"
          variant="ghost"
          class="text-sm"
          @click="showTesteModal = true"
        >
          <FlaskConical :size="16" class="mr-1.5" />
          Emitir Teste
        </BaseButton>
        <BaseButton
          type="button"
          variant="primary"
          class="text-sm"
          @click="showEmitirModal = true"
        >
          <Send :size="16" class="mr-1.5" />
          Emitir NF-e
        </BaseButton>
      </div>
    </div>

    <FiscalStats :resumo="resumo" :is-loading="isResumoLoading" />

    <!-- Conteudo -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
      <div class="lg:col-span-2">
        <FiscalDocumentosTable
          tipo-filtro="NFE"
          :is-homologacao="isHomologacao"
        />
      </div>
      <div class="lg:col-span-1">
        <FiscalPendenciasPanel />
      </div>
    </div>

    <!-- Modal emissao de teste -->
    <FiscalEmitirTesteModal
      :is-open="showTesteModal"
      @close="showTesteModal = false"
    />

    <!-- Modal emissao de NF-e -->
    <FiscalEmitirNFeModal
      :is-open="showEmitirModal"
      @close="showEmitirModal = false"
    />
  </div>
</template>
