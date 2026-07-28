<script setup lang="ts">
import { ref, computed } from 'vue';
import { Plus } from 'lucide-vue-next';

import { TAB_OPTIONS } from '../ordens/constants/ordemServico.constants';

import PageReview from '@/shared/components/layout/PageReview/PageReview.vue';
import BaseTab2 from '@/shared/components/ui/BaseTab2/BaseTab2.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';

import OrdensServicoTab from './tabs/OrdensServicoTab.vue';
import ServicosTab from './tabs/ServicosTab.vue';
import RevisoesPendentesTab from './tabs/RevisoesPendentesTab.vue';

import { useServicoModal } from '../servicos/composables/useServicoModal';
import { useOSCreateFlow } from '../ordens/composables/useOSCreateFlow';
import { useCapacidades } from '../shared/segmento/useCapacidades';

const { openCreateModal } = useServicoModal();
const { openNovaOS } = useOSCreateFlow();
const { temRevisoes } = useCapacidades();

const activeTab = ref('ordens');

// Aba "Revisões" (pós-venda): só para segmentos que declaram a capacidade.
const tabOptions = computed(() =>
  temRevisoes.value
    ? [...TAB_OPTIONS, { id: 'revisoes', label: 'Revisões' }]
    : TAB_OPTIONS,
);

const pageTitle = computed(() => {
  if (activeTab.value === 'revisoes') return 'Revisões Pendentes';
  return activeTab.value === 'ordens' ? 'Ordens de Serviço' : 'Cadastro de Serviços';
});

const pageDescription = computed(() => {
  if (activeTab.value === 'revisoes') return 'Veículos com revisão vencida por data e/ou KM.';
  return activeTab.value === 'ordens'
    ? 'Gerencie as ordens de serviço da sua organização.'
    : 'Gerencie o catálogo de serviços da sua organização.';
});

function handleAddClick() {
  if (activeTab.value === 'ordens') {
    openNovaOS();
  } else {
    openCreateModal();
  }
}
</script>

<template>
  <div class="p-4 md:p-6 lg:p-8 space-y-6 md:space-y-8">
    <div class="flex flex-col flex-wrap sm:flex-row sm:justify-between sm:items-end gap-4">
      <PageReview
        :title="pageTitle"
        :description="pageDescription"
      />

      <div class="flex gap-5">
        <BaseTab2 :options="tabOptions" v-model="activeTab" />
        <BaseButton
          v-if="activeTab !== 'revisoes'"
          variant="primary"
          size="md"
          type="button"
          class="flex gap-1"
          @click="handleAddClick"
        >
          <Plus :size="20" />
          {{ activeTab === 'ordens' ? 'Nova OS' : 'Novo Serviço' }}
        </BaseButton>
      </div>
    </div>

    <OrdensServicoTab v-if="activeTab === 'ordens'" />
    <RevisoesPendentesTab v-else-if="activeTab === 'revisoes'" />
    <ServicosTab v-else />
  </div>
</template>
