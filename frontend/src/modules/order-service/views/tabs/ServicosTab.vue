<script setup lang="ts">
import { ref } from 'vue';
import BaseConfirmModal from '@/shared/components/commons/BaseConfirmModal/BaseConfirmModal.vue';
import ServicoStats from '../../servicos/components/ServicoStats.vue';
import ServicoTable from '../../servicos/components/ServicoTable.vue';
import { useServicosQuery, useServicosStatsQuery } from '../../servicos/composables/useServicosQuery';
import { useToggleServicoAtivoMutation } from '../../servicos/composables/useServicosMutations';
import { useServicoModal } from '../../servicos/composables/useServicoModal';
import type { ServiceReadZod } from '../../servicos/schemas/servicos.schema';

import { useRoute, useRouter } from 'vue-router';
import { watch } from 'vue';

const { searchQuery, activeFilterQuery, currentPage, setPage, services, totalPages, totalItems, isLoading, isError } = useServicosQuery();
const { stats, isLoading: isStatsLoading } = useServicosStatsQuery();
const { openEditModal, openViewModal } = useServicoModal();
const toggleAtivoMutation = useToggleServicoAtivoMutation();

const route = useRoute();
const router = useRouter();

// Auto-open edit modal if query param 'editar' is present
watch(
  () => [services.value, route.query.editar] as const,
  ([list, editarId]) => {
    if (editarId && list && list.length > 0) {
      const id = Number(editarId);
      const servico = list.find((s) => s.id === id);
      if (servico) {
        openEditModal(servico);
        // Remove from query so it doesn't re-open on refresh
        router.replace({ query: { ...route.query, editar: undefined } });
      }
    }
  },
  { immediate: true }
);

const isStatusModalOpen = ref(false);
const servicoToToggle = ref<ServiceReadZod | null>(null);

function handleEdit(servico: ServiceReadZod) {
  openEditModal(servico);
}

function handleView(servico: ServiceReadZod) {
  openViewModal(servico);
}

function handleToggleStatus(servico: ServiceReadZod) {
  servicoToToggle.value = servico;
  isStatusModalOpen.value = true;
}

function handleCloseStatusModal() {
  isStatusModalOpen.value = false;
  servicoToToggle.value = null;
}

function handleConfirmStatusToggle() {
  if (!servicoToToggle.value) return;

  toggleAtivoMutation.mutate(servicoToToggle.value.id, {
    onSuccess: () => {
      handleCloseStatusModal();
    },
  });
}
</script>

<template>
  <div class="space-y-6">

    <ServicoStats :stats="stats" :loading="isStatsLoading" />

    <ServicoTable
      :servicos="services ?? []"
      :is-loading="isLoading"
      :is-error="isError"
      :current-page="currentPage"
      :total-pages="totalPages"
      :total-items="totalItems"
      v-model:search="searchQuery"
      v-model:status-filter="activeFilterQuery"
      @view="handleView"
      @edit="handleEdit"
      @toggle-status="handleToggleStatus"
      @update:current-page="setPage"
    />

    <BaseConfirmModal
      :is-open="isStatusModalOpen"
      :title="(servicoToToggle?.ativo ? 'Desativar' : 'Ativar') + ' Serviço?'"
      :description="`Deseja realmente ${servicoToToggle?.ativo ? 'desativar' : 'ativar'} o serviço <b>${servicoToToggle?.descricao}</b>?`"
      :confirm-text="servicoToToggle?.ativo ? 'DESATIVAR' : 'ATIVAR'"
      :is-danger="servicoToToggle?.ativo"
      :is-loading="toggleAtivoMutation.isPending.value"
      @close="handleCloseStatusModal"
      @confirm="handleConfirmStatusToggle"
    />
  </div>
</template>
