<script setup lang="ts">
import { ref, computed } from 'vue';
import { FlaskConical, Send, Activity } from 'lucide-vue-next';


import PageReview from '@/shared/components/layout/PageReview/PageReview.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';

import FiscalStats from '../components/listagem/FiscalStats.vue';
import FiscalDocumentosTable from '../components/listagem/FiscalDocumentosTable.vue';
import FiscalPendenciasPanel from '../components/shared/FiscalPendenciasPanel.vue';
import FiscalEmitirTesteModal from '../components/emitir/FiscalEmitirTesteModal.vue';
import FiscalEmitirNFeModal from '../components/emitir/FiscalEmitirNFeModal.vue';
import FiscalDocumentoDetailsDrawer from '../components/detalhes/FiscalDocumentoDetailsDrawer.vue';
import FiscalResolucaoProdutosDrawer from '../components/shared/FiscalResolucaoProdutosDrawer.vue';
import { useFiscalResumoQuery } from '../composables/useFiscalResumoQuery';
import { useFiscalPendenciasQuery } from '../composables/useFiscalPendenciasQuery';

interface Props {
  isHomologacao?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  isHomologacao: true,
});

const { data: resumo, isLoading: isResumoLoading } = useFiscalResumoQuery();
const { data: pendencias } = useFiscalPendenciasQuery();

const showTesteModal = ref(false);
const showEmitirModal = ref(false);
const showDetalhesDrawer = ref(false);
const detalhesDocumentoId = ref<number | null>(null);
const showPendenciasPopover = ref(false);
const activeStatusFilter = ref<string | null>(null);
const showResolucaoDrawer = ref(false);

function handleAbrirResolucao() {
  showPendenciasPopover.value = false;
  showResolucaoDrawer.value = true;
}

const handleAbrirDetalhes = (id: number) => {
  detalhesDocumentoId.value = id;
  showDetalhesDrawer.value = true;
};

const totalPendencias = computed(() => {
  if (!pendencias.value) return 0;
  const emitente = pendencias.value.emitente_completo ? 0 : pendencias.value.emitente_pendencias.length;
  return (
    emitente +
    (pendencias.value.produtos_sem_ncm?.length ?? 0) +
    (pendencias.value.servicos_sem_lc116?.length ?? 0) +
    (pendencias.value.pagamentos_sem_sefaz?.length ?? 0)
  );
});

const healthPercent = computed(() => {
  if (!pendencias.value) return 0;
  let resolved = 0;
  if (pendencias.value.emitente_completo) resolved++;
  if ((pendencias.value.produtos_sem_ncm?.length ?? 0) === 0) resolved++;
  if ((pendencias.value.servicos_sem_lc116?.length ?? 0) === 0) resolved++;
  if ((pendencias.value.pagamentos_sem_sefaz?.length ?? 0) === 0) resolved++;
  return Math.round((resolved / 4) * 100);
});

const healthBarColor = computed(() => {
  if (healthPercent.value === 100) return 'bg-emerald-500';
  if (healthPercent.value >= 75) return 'bg-emerald-400';
  if (healthPercent.value >= 50) return 'bg-amber-400';
  return 'bg-red-500';
});

const healthTextColor = computed(() => {
  if (healthPercent.value === 100) return 'text-emerald-600';
  if (healthPercent.value >= 50) return 'text-amber-600';
  return 'text-red-600';
});
</script>

<template>
  <div class="flex flex-col gap-6 flex-1 min-h-0">

    <!-- Page Header (padrão do sistema) -->
    <div class="flex flex-col flex-wrap sm:flex-row sm:justify-between sm:items-end gap-4">
      <PageReview
        title="NF-e"
        description="Gerencie suas Notas Fiscais Eletrônicas"
      />

      <div class="flex items-center gap-2">
        <!-- Saúde Fiscal — card clicável -->
        <div class="relative">
          <button
            type="button"
            class="flex items-center gap-3 px-4 py-2 rounded-xl border border-zinc-200 bg-white hover:border-zinc-300 hover:shadow-sm transition-all cursor-pointer"
            @click="showPendenciasPopover = !showPendenciasPopover"
          >
            <Activity :size="16" :class="healthTextColor" />
            <div class="flex flex-col items-start">
              <span class="text-xs font-semibold text-zinc-700 leading-none">Saúde Fiscal</span>
              <div class="flex items-center gap-2 mt-1">
                <div class="w-16 h-1.5 rounded-full bg-zinc-100 overflow-hidden">
                  <div
                    :class="['h-full rounded-full transition-all duration-700', healthBarColor]"
                    :style="{ width: healthPercent + '%' }"
                  />
                </div>
                <span :class="['text-[10px] font-bold tabular-nums', healthTextColor]">{{ healthPercent }}%</span>
              </div>
            </div>
            <span
              v-if="totalPendencias > 0"
              class="inline-flex items-center justify-center min-w-5 h-5 px-1.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-700"
            >
              {{ totalPendencias }}
            </span>
          </button>

          <!-- Popover -->
          <Transition name="popover">
            <div
              v-if="showPendenciasPopover"
              class="absolute right-0 top-full mt-2 z-50 w-85 max-h-120 overflow-y-auto rounded-2xl shadow-xl border border-zinc-200 bg-white"
            >
              <FiscalPendenciasPanel @abrir-resolucao="handleAbrirResolucao" />
            </div>
          </Transition>

          <!-- Backdrop para fechar popover -->
          <div
            v-if="showPendenciasPopover"
            class="fixed inset-0 z-40"
            @click="showPendenciasPopover = false"
          />
        </div>

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

    <!-- Stats Cards -->
    <FiscalStats
      :resumo="resumo"
      :is-loading="isResumoLoading"
      :active-status="activeStatusFilter"
      @filter-status="activeStatusFilter = $event"
    />

    <!-- Tabela full-width -->
    <FiscalDocumentosTable
      tipo-filtro="NFE"
      :is-homologacao="isHomologacao"
      :status-filter-externo="activeStatusFilter"
      @abrir-detalhes="handleAbrirDetalhes"
    />

    <!-- Modais -->
    <FiscalEmitirTesteModal
      :is-open="showTesteModal"
      @close="showTesteModal = false"
    />
    <FiscalEmitirNFeModal
      :is-open="showEmitirModal"
      @close="showEmitirModal = false"
      @abrir-detalhes-documento="handleAbrirDetalhes"
    />

    <!-- Drawer de Detalhes -->
    <FiscalDocumentoDetailsDrawer
      v-model:is-open="showDetalhesDrawer"
      :documento-id="detalhesDocumentoId"
    />

    <!-- Drawer de Resolução de Pendências -->
    <FiscalResolucaoProdutosDrawer
      v-model:is-open="showResolucaoDrawer"
    />
  </div>
</template>

<style scoped>
.popover-enter-active,
.popover-leave-active {
  transition: all 0.15s ease;
}
.popover-enter-from,
.popover-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.98);
}
</style>
