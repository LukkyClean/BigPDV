<script setup lang="ts">
import { ref, computed } from 'vue';

import OSReopenOptionsModal from './OSReopenOptionsModal.vue';
import OSItemFormModal from './OSItemFormModal.vue';
import OSObjetoSelectModal from './OSObjetoSelectModal.vue';
import OSClientHistoryModal from './OSClientHistoryModal.vue';
import OSPrintTemplate from '../OSPrintTemplate.vue';
import OSPrintCupom from '../OSPrintCupom.vue';
import PrintFormatSelectModal from '@/shared/components/print/PrintFormatSelectModal.vue';
import OSFinalizarModal, { type DadosFinalizacaoOS } from '../OSFinalizarModal.vue';
import OSPagamentoModal from '../OSPagamentoModal.vue';
import { useOSFormView } from '../../context/useOSFormView.context';
import { useReadyOrderServiceMutation } from '../../composables/request/useOrderServiceUpdate.mutate';

const view = useOSFormView();
const finalizarEntregaMutation = useReadyOrderServiceMutation();

// Valor já registrado como pago na OS — usado para perguntar "o cliente já pagou?"
// na reabertura completa. Só pergunta quando há dinheiro em jogo.
const valorJaPago = computed(() => {
  const os = view.currentOSData.value;
  if (!os) return 0;
  const pagamentos = (os.pagamentos ?? []).reduce((s, p) => s + p.valor, 0);
  return (os.credito_anterior ?? 0) + pagamentos + (os.valor_entrada ?? 0);
});

// ─── Estado do fluxo de finalização (dois modais) ─────────────────────────────
const isPagamentoOpen = ref(false);
const dadosFinalizacao = ref<DadosFinalizacaoOS | null>(null);

function handleAdvance(data: DadosFinalizacaoOS) {
  dadosFinalizacao.value = data;

  // Sem reparo / Condenado: finaliza direto sem tela de pagamento
  const isEntrega = data.situacao_equipamento === 'SEM_REPARO' || data.situacao_equipamento === 'CONDENADO';
  if (isEntrega) {
    const osNumber = view.osNumber.value;
    if (!osNumber) return;
    finalizarEntregaMutation.mutate(
      {
        osNumber,
        readyOs: {
          situacao_equipamento: data.situacao_equipamento,
          garantia: data.garantia,
          solucao: data.solucao,
          observacoes: data.observacoes ?? '',
          desconto: data.desconto,
          taxa_entrega: view.currentOSData.value?.taxa_entrega ?? 0,
          acrescimo: 0,
          valor_entrada: data.zerarAdiantamento ? 0 : undefined,
          pagamentos: [],
        },
      },
      {
        onSuccess: () => {
          view.printType.value = 'SAIDA';
          handleFinalized({ shouldPrint: true });
        },
      },
    );
    return;
  }

  isPagamentoOpen.value = true;
}

function handlePagamentoVoltar() {
  isPagamentoOpen.value = false;
}

function handlePagamentoClose() {
  isPagamentoOpen.value = false;
  dadosFinalizacao.value = null;
  view.closeFinalizarModal();
}

async function handleFinalized(payload: { shouldPrint: boolean }) {
  isPagamentoOpen.value = false;
  dadosFinalizacao.value = null;
  view.closeFinalizarModal();
  // Recarrega a OS com os dados do fechamento (situação, solução, pagamentos)
  // antes de imprimir; senão o cupom automático sai defasado (a via manual da
  // lista já busca a OS fresca). Só recarrega quando de fato vai imprimir.
  if (payload.shouldPrint) await view.refreshCurrentOSData();
  view.onFinalized(payload);
}
</script>

<template>
  <OSClientHistoryModal
    :is-open="view.isHistoricoModalOpen.value"
    :cliente-id="view.currentCliente.value?.id ?? null"
    @close="view.closeHistoricoModal"
    @reutilizar-objeto="view.reutilizarObjeto"
  />

  <OSReopenOptionsModal
    :is-open="view.isReopenOptionsOpen.value"
    :tem-pagamento="valorJaPago > 0"
    :valor-pago="valorJaPago"
    @cancel="view.handleReopenCancel"
    @text-only="view.handleReopenTextOnly"
    @full="view.handleReopenFull"
  />

  <PrintFormatSelectModal
    :is-open="view.isPrintSelectModalOpen.value"
    subtitle="Selecione o formato desejado para imprimir esta OS."
    @close="view.closePrintSelectModal"
    @select="view.handlePrintFormatSelected"
  />

  <OSPrintTemplate
    v-if="view.currentOSData.value && view.printFormat.value === 'A4'"
    :ordem-servico="view.currentOSData.value"
    :type="view.printType.value"
  />

  <OSPrintCupom
    v-if="view.currentOSData.value && view.printFormat.value === 'CUPOM'"
    :order-service="view.currentOSData.value"
    :type="view.printType.value"
  />

  <!-- Modal 1: Detalhes da finalização -->
  <OSFinalizarModal
    :is-open="view.isFinalizarModalOpen.value"
    :os-numero="view.osNumber.value"
    :ordem-servico="view.currentOSData.value"
    @close="view.closeFinalizarModal"
    @advance="handleAdvance"
  />

  <!-- Modal 2: Pagamento (overlay sobre Modal 1) -->
  <OSPagamentoModal
    :is-open="isPagamentoOpen"
    :os-numero="view.osNumber.value"
    :ordem-servico="view.currentOSData.value"
    :dados-os="dadosFinalizacao"
    :desconto-os="dadosFinalizacao?.desconto ?? 0"
    :credito-ao-reabrir="view.currentOSData.value?.credito_anterior ?? view.creditoAoReabrir.value"
    @close="handlePagamentoClose"
    @voltar="handlePagamentoVoltar"
    @finalized="handleFinalized"
  />

  <OSItemFormModal
    :is-open="view.isItemModalOpen.value"
    :item="view.editingItem.value"
    @close="view.closeItemModal"
    @save="view.handleSaveItem"
  />

  <OSObjetoSelectModal
    :is-open="view.isObjetoSelectModalOpen.value"
    :objetos="view.objetosHistorico.value"
    @close="view.closeObjetoModal"
    @select="view.handleObjetoSelected"
  />
</template>
