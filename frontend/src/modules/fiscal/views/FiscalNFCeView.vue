<script setup lang="ts">
/**
 * @component FiscalNFCeView
 * @description Central de gestão da NFC-e (modelo 65).
 *
 * Espelha a `FiscalNFeView` e reusa os mesmos componentes com o filtro fixo em
 * NFCE. O que difere é o que a NFC-e tem de próprio: o prazo de cancelamento
 * de 30 minutos, curto o bastante para precisar estar na tela, e a segunda via
 * do cupom (no drawer de detalhes).
 *
 * Não há emissão a partir daqui de propósito: a NFC-e nasce no caixa, junto da
 * venda. Um botão "emitir" nesta tela sugeriria um cupom sem venda por trás.
 */

import { ref, computed } from 'vue';
import { Activity, Clock, Receipt, FolderArchive } from 'lucide-vue-next';

import PageReview from '@/shared/components/layout/PageReview/PageReview.vue';

import FiscalStats from '../components/listagem/FiscalStats.vue';
import FiscalDocumentosTable from '../components/listagem/FiscalDocumentosTable.vue';
import FiscalPendenciasPanel from '../components/shared/FiscalPendenciasPanel.vue';
import FiscalExportarXmlModal from '../components/listagem/FiscalExportarXmlModal.vue';
import FiscalDocumentoDetailsDrawer from '../components/detalhes/FiscalDocumentoDetailsDrawer.vue';
import FiscalResolucaoProdutosDrawer from '../components/shared/FiscalResolucaoProdutosDrawer.vue';
import { useFiscalResumoQuery } from '../composables/useFiscalResumoQuery';
import { useFiscalPendenciasQuery } from '../composables/useFiscalPendenciasQuery';
import { useFiscalConfiguracaoQuery } from '../composables/useFiscalConfiguracaoQuery';
import type { DocumentoFiscalStatus } from '../types/fiscal.types';

const { data: resumo, isLoading: isResumoLoading } = useFiscalResumoQuery('NFCE');
const { data: pendencias } = useFiscalPendenciasQuery();
const { data: configuracao } = useFiscalConfiguracaoQuery();

const showDetalhesDrawer = ref(false);
const detalhesDocumentoId = ref<number | null>(null);
const showPendenciasPopover = ref(false);
const showExportarXmlModal = ref(false);
const activeStatusFilter = ref<DocumentoFiscalStatus | null>(null);
const showResolucaoDrawer = ref(false);

const isHomologacao = computed(() => configuracao.value?.ambiente === 2);

function handleAbrirResolucao() {
  showPendenciasPopover.value = false;
  showResolucaoDrawer.value = true;
}

function handleAbrirDetalhes(id: number) {
  detalhesDocumentoId.value = id;
  showDetalhesDrawer.value = true;
}

const totalPendencias = computed(() => {
  if (!pendencias.value) return 0;
  const emitente = pendencias.value.emitente_completo
    ? 0
    : pendencias.value.emitente_pendencias.length;
  return (
    emitente
    + (pendencias.value.produtos_sem_ncm?.length ?? 0)
    + (pendencias.value.servicos_sem_lc116?.length ?? 0)
    + (pendencias.value.pagamentos_sem_sefaz?.length ?? 0)
  );
});

const healthPercent = computed(() => {
  if (!pendencias.value) return 0;
  let resolvidos = 0;
  if (pendencias.value.emitente_completo) resolvidos++;
  if ((pendencias.value.produtos_sem_ncm?.length ?? 0) === 0) resolvidos++;
  if ((pendencias.value.servicos_sem_lc116?.length ?? 0) === 0) resolvidos++;
  if ((pendencias.value.pagamentos_sem_sefaz?.length ?? 0) === 0) resolvidos++;
  return Math.round((resolvidos / 4) * 100);
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

    <!-- Cabeçalho -->
    <div class="flex flex-col flex-wrap sm:flex-row sm:justify-between sm:items-end gap-4">
      <PageReview
        title="NFC-e"
        description="Cupons fiscais emitidos no caixa"
      />

      <div class="flex items-center gap-2">
        <!-- Saúde fiscal -->
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
                <span :class="['text-[10px] font-bold tabular-nums', healthTextColor]">
                  {{ healthPercent }}%
                </span>
              </div>
            </div>
            <span
              v-if="totalPendencias > 0"
              class="inline-flex items-center justify-center min-w-5 h-5 px-1.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-700"
            >
              {{ totalPendencias }}
            </span>
          </button>

          <Transition name="popover">
            <div
              v-if="showPendenciasPopover"
              class="absolute right-0 top-full mt-2 z-50 w-85 max-h-120 overflow-y-auto rounded-2xl shadow-xl border border-zinc-200 bg-white"
            >
              <FiscalPendenciasPanel @abrir-resolucao="handleAbrirResolucao" />
            </div>
          </Transition>

          <div
            v-if="showPendenciasPopover"
            class="fixed inset-0 z-40"
            @click="showPendenciasPopover = false"
          />
        </div>
        <BaseButton
          type="button"
          variant="ghost"
          class="text-sm"
          data-exportar-xml
          @click="showExportarXmlModal = true"
        >
          <FolderArchive :size="16" class="mr-1.5" />
          XMLs do período
        </BaseButton>
      </div>
    </div>

    <!-- Onde a NFC-e nasce, e o prazo que ela tem.
         O de 30 minutos é curto o bastante para o lojista precisar vê-lo ANTES
         de procurar o botão de cancelar — depois disso a via é a nota de
         devolução, que é outro trabalho. -->
    <div class="flex flex-col sm:flex-row gap-3">
      <div class="flex items-start gap-2.5 rounded-xl border border-zinc-200 bg-white px-4 py-3 flex-1">
        <Receipt :size="15" class="text-zinc-400 mt-0.5 shrink-0" />
        <p class="text-[11px] text-zinc-500 leading-snug">
          A NFC-e é emitida no <strong class="text-zinc-700">fechamento da venda</strong>,
          no PDV. Esta tela acompanha, reimprime e cancela os cupons já emitidos.
        </p>
      </div>
      <div class="flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50/60 px-4 py-3 flex-1">
        <Clock :size="15" class="text-amber-500 mt-0.5 shrink-0" />
        <p class="text-[11px] text-amber-800 leading-snug">
          O cancelamento só é aceito pela SEFAZ em até
          <strong>30 minutos</strong> da autorização. Passado o prazo, a correção
          exige uma NF-e de devolução.
        </p>
      </div>
    </div>

    <!-- Contadores -->
    <FiscalStats
      :resumo="resumo"
      :is-loading="isResumoLoading"
      :active-status="activeStatusFilter"
      @filter-status="activeStatusFilter = $event"
    />

    <!-- Documentos -->
    <FiscalDocumentosTable
      tipo-filtro="NFCE"
      :is-homologacao="isHomologacao"
      :status-filter-externo="activeStatusFilter"
      @abrir-detalhes="handleAbrirDetalhes"
    />

    <!-- Detalhes: histórico, reenvio, cancelamento e a 2a via do cupom -->
    <FiscalDocumentoDetailsDrawer
      v-model:is-open="showDetalhesDrawer"
      :documento-id="detalhesDocumentoId"
      @reemitir="(id) => { detalhesDocumentoId = id; }"
      @abrir-resolucao-produtos="handleAbrirResolucao"
    />

    <FiscalResolucaoProdutosDrawer v-model:is-open="showResolucaoDrawer" />

    <FiscalExportarXmlModal
      :is-open="showExportarXmlModal"
      tipo-inicial="NFCE"
      @close="showExportarXmlModal = false"
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
