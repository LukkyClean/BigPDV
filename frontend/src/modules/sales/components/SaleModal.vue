<script setup lang="ts">
import { computed, nextTick, ref, toRef, watch } from 'vue';
import { X, Printer, ShoppingCart, PackagePlus, Trash2 } from 'lucide-vue-next';
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';

import ProductSearch from './SaleModal/ProductSearch.vue';
import CustomerCard from './SaleModal/CustomerCard.vue';
import SaleCard from './SaleModal/SaleCard.vue';
import SaleItemsTable from './SaleModal/SaleItemsTable.vue';
import SaleSummary from './SaleModal/SaleSummary.vue';
import ItemModal from './SaleModal/ItemModal.vue';
import FinishSaleModal from './SaleModal/FinishSaleModal.vue';
import AddProductModal from './SaleModal/AddProductModal.vue';
import CancelSaleModal from './SaleModal/CancelSaleModal.vue';
import GerenteAprovacaoModal from '@/shared/components/commons/GerenteAprovacaoModal/GerenteAprovacaoModal.vue';

import { SALE_FILTERS, STATUS_COLORS } from '../constants';

import { useFinishSaleModal } from '../composables/flows/useFinishSaleModal';
import { useSaleModal } from '../composables/flows/useSaleModal';
import { useItemModal } from '../composables/flows/useItemModal';
import { useConfirmSaleAction } from '../composables/flows/useConfirmSaleAction';
import { useDeleteSaleMutation } from '../composables/mutates/useDeleteSaleMutation';
import { useUpdateSaleMutation } from '../composables/mutates/useUpdateSaleMutation';
import { useCustomerSearchModal } from '../composables/flows/useCustomerSearchModal';
import { useSaleShortcuts } from '../composables/useSaleShortcuts';
import { useSalePrintFlow } from '../composables/flows/useSalePrintFlow';
import { useSaleDetailsForm } from '../composables/flows/useSaleDetailsForm';
import { useAddProductModal } from '../composables/flows/useAddProductModal';
import type { SaleRead } from '../schemas/sale.schema';
import { storeToRefs } from 'pinia';
import { useConfiguracoesStore } from '@/shared/stores/configuracoes.store';
import { useBalcaoStore } from '@/shared/stores/balcao.store';

import PrintFormatSelectModal from '@/shared/components/print/PrintFormatSelectModal.vue';
import SalePrintTemplate from './print/SalePrintTemplate.vue';
import SalePrintCupom from './print/SalePrintCupom.vue';

const { saleModalIsOpen, closeSaleModal, sale, selectedSaleId, isEditMode, isViewMode } = useSaleModal();
const addProductModal = useAddProductModal();
const {
  form: saleForm,
  isSaving: isSaleFormSaving,
  saveNow: saveSaleForm,
  gerenteDesconto,
} = useSaleDetailsForm(sale);
const { openFinishModal, closeFinishModal, finishModalIsOpen, showPaymentDetails } = useFinishSaleModal();
const { itemModalIsOpen, openCreateItemModal, closeItemModal } = useItemModal();
const { openConfirmModal, closeConfirmModal: closeConfirm, confirmModalPending } = useConfirmSaleAction();
const deleteMutation = useDeleteSaleMutation();
const updateSaleMutation = useUpdateSaleMutation();
const cancelSaleModalIsOpen = ref(false);
const { openCustomerModalForChange, iniciarVendaSemCliente } = useCustomerSearchModal();
const { valorMinimoVenda, exigirClienteIdentificado } = storeToRefs(useConfiguracoesStore());
const { modoBalcao } = storeToRefs(useBalcaoStore());

const {
  saleForPrint,
  printType,
  printFormat,
  isPrintSelectModalOpen,
  printSaleData,
  imprimirAposFinalizar,
  handlePrintFormatSelected,
  closePrintSelectModal,
  resolvePaymentMethodName,
} = useSalePrintFlow();

/**
 * Põe o cursor na busca de produto — e confere que ele ficou lá.
 *
 * A venda abre dentro de um `<Transition>` e a busca só existe em modo edição,
 * então houve mais de um jeito de o `nextTick` chegar antes do elemento estar
 * focável. Quando isso acontecia, a venda abria sem cursor em lugar nenhum e o
 * operador era obrigado a clicar na barra com o mouse — no primeiro passo do
 * fluxo que deveria ser todo de teclado.
 *
 * A segunda tentativa no quadro seguinte é barata e cobre a corrida.
 */
function focarBuscaDeProduto() {
  const tentar = () => {
    const input = document.querySelector<HTMLInputElement>('[data-search-products] input');
    if (!input) return false;
    input.focus();
    return document.activeElement === input;
  };

  nextTick(() => {
    if (tentar()) return;
    requestAnimationFrame(() => void tentar());
  });
}

watch(saleModalIsOpen, (isOpen) => {
  if (isOpen) focarBuscaDeProduto();
}, { immediate: true });

/**
 * O que acontece depois que a venda fecha.
 *
 * Fora do Modo Balcão: volta para a lista, como sempre.
 *
 * No Modo Balcão a próxima venda já abre — no balcão as vendas são encadeadas e
 * mandar o operador clicar em "Nova venda" a cada cliente é atrito puro.
 *
 * A ORDEM IMPORTA: fecha primeiro, abre depois. Se a criação da próxima falhar
 * (caixa fechado no meio do turno, por exemplo), o operador cai na lista com o
 * aviso do servidor, em vez de ficar preso numa tela mostrando a venda que ele
 * acabou de finalizar.
 *
 * Emenda só depois da impressão, porque é o `afterPrint` que roda quando o
 * cupom saiu — trocar a venda da tela antes disso mexeria no que está sendo
 * impresso.
 */
function handleFinalized(finishedSale: SaleRead) {
  imprimirAposFinalizar(finishedSale, () => {
    closeSaleModal();
    if (modoBalcao.value && !exigirClienteIdentificado.value) {
      iniciarVendaSemCliente();
    }
  });
}

function handleChangeCliente() {
  if (!sale.value) return;
  const saleId = sale.value.id;

  openCustomerModalForChange((clienteId) => {
    updateSaleMutation.mutate({
      saleId,
      payload: { cliente_id: clienteId },
    });
  });
}

function handleCancel() {
  if (!sale.value) return;

  const saleId = sale.value.id;

  openConfirmModal({
    title: 'Descartar Venda?',
    message: 'Tem certeza que deseja descartar este rascunho? Esta ação não pode ser desfeita.',
    variant: 'danger',
    label: 'DESCARTAR',
    action: () => {
      confirmModalPending.value = true;
      deleteMutation.mutate(
        { saleId },
        {
          onSuccess: () => {
            closeConfirm();
            closeSaleModal();
          },
          onSettled: () => { confirmModalPending.value = false; },
        },
      );
    },
  });
}

function handleCancelFinalized() {
  cancelSaleModalIsOpen.value = true;
}

function handlePrint() {
  if (!sale.value) return;
  printSaleData(sale.value, 'VENDA');
}

useSaleShortcuts({
  saleModalIsOpen,
  isEditMode,
  finishModalIsOpen,
  paymentDetailsIsOpen: showPaymentDetails,
  itemModalIsOpen,
  addProductModalIsOpen: toRef(addProductModal, 'isAddProductModalOpen'),
  onCreateSale: () => {},
  onOpenFinishModal: openFinishModal,
  onOpenItemModal: openCreateItemModal,
  onOpenAddProductModal: () => addProductModal.openAddProductModal(),
  onCloseAddProductModal: addProductModal.closeAddProductModal,
  onFocusPaymentGrid: () => {
    nextTick(() => {
      const btn = document.querySelector<HTMLButtonElement>('[data-payment-grid] button');
      btn?.focus();
    });
  },
  onCancelSale: handleCancel,
  onCloseSaleModal: closeSaleModal,
  onCloseFinishModal: closeFinishModal,
  onClosePaymentDetails: () => { showPaymentDetails.value = false; },
  onCloseItemModal: closeItemModal,
  onFocusSearch: focarBuscaDeProduto,
  onFocusSaleInputs: (field) => {
    nextTick(() => {
      document.querySelector<HTMLInputElement>(`[data-sale-${field}] input`)?.focus();
    });
  },
});

const saleDisplay = computed(() => {
  if (!sale.value) return '...';
  if (sale.value.numero_venda) return `Venda #${String(sale.value.numero_venda).padStart(6, '0')}`;
  return `#${String(sale.value.id).padStart(6, '0')}`;
});
</script>

<template>
  <BaseModal
    :is-open="saleModalIsOpen"
    :title="saleDisplay"
    subtitle="Gerencie os detalhes desta venda, adicione produtos, finalize ou cancele a venda"
    size="full"
    overflow="hidden"
    @close="closeSaleModal"
  >
    <template #header>
      <div class="flex items-center justify-between px-6 py-4 border-b border-zinc-200">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 bg-brand-primary shadow-sm shadow-brand-primary/20">
            <ShoppingCart :size="18" class="text-white" />
          </div>
          <h2 class="text-xl font-bold text-zinc-800">
            Atendimento Atual
          </h2>
          <span
            :class="[
              'px-2 py-0.5 text-xs font-medium rounded-full',
              STATUS_COLORS[sale?.status!].text,
              STATUS_COLORS[sale?.status!].bg,
            ]"
          >
            {{ SALE_FILTERS[sale?.status!].label }}
          </span>
          <span
            v-if="sale?.produtos?.length"
            class="px-2 py-0.5 text-xs font-medium rounded-full bg-zinc-100 text-zinc-500"
          >
            {{ sale.produtos.length }} {{ sale.produtos.length === 1 ? 'item' : 'itens' }}
          </span>
        </div>

        <div class="flex items-center gap-1">
          <button
            v-if="isEditMode"
            type="button"
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors cursor-pointer mr-1"
            title="Descartar Venda (Ctrl+Backspace)"
            @click="handleCancel"
          >
            <Trash2 :size="16" />
            <span class="hidden sm:inline">Descartar Venda</span>
          </button>
          <button
            v-if="isViewMode && sale?.status === 'FINALIZADA'"
            type="button"
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors cursor-pointer mr-1"
            title="Cancelar Venda"
            @click="handleCancelFinalized"
          >
            <Trash2 :size="16" />
            <span class="hidden sm:inline">Cancelar Venda</span>
          </button>
          <button
            v-if="!isEditMode"
            type="button"
            class="p-2 text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 rounded-lg transition-colors cursor-pointer"
            title="Imprimir Comprovante"
            @click="handlePrint"
          >
            <Printer :size="18" />
          </button>
          <button
            type="button"
            class="p-2 text-zinc-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
            @click="closeSaleModal()"
          >
            <X :size="20" />
          </button>
        </div>
      </div>
    </template>

    <main class="w-full h-full flex flex-nowrap gap-4">
      <!-- Área de produtos -->
      <section class="flex-1 min-w-0 flex flex-col gap-3 h-full">
        <div v-if="isEditMode" class="flex items-center gap-2">
          <ProductSearch class="flex-1" :sale-id="selectedSaleId" :current-items="sale?.produtos" />
          <button
            type="button"
            class="flex items-center gap-2 h-9 px-4 rounded-lg bg-brand-primary/10 text-brand-primary border border-brand-primary/20 text-sm font-semibold hover:bg-brand-primary/20 hover:border-brand-primary/30 transition-all shrink-0 cursor-pointer"
            title="Quantidade e desconto (F3)"
            @click="addProductModal.openAddProductModal()"
          >
            <PackagePlus :size="16" />
            Adicionar Produto
            <kbd class="ml-0.5 inline-flex items-center rounded border border-brand-primary/30 bg-white/60 px-1 text-[10px] font-semibold">F3</kbd>
          </button>
        </div>
        <SaleItemsTable :sale="sale" :readonly="isViewMode" class="flex-1 min-h-0" />
        <SaleSummary
          :subtotal="sale?.subtotal"
          :discount="sale?.descontos"
          :delivery="sale?.entrega"
          :total="sale?.total"
          :form="saleForm"
          :is-saving="isSaleFormSaving"
          :readonly="isViewMode"
          :valor-minimo-venda="valorMinimoVenda"
          :on-save="saveSaleForm"
        />
      </section>

      <!-- Painel lateral -->
      <section class="w-80 shrink-0 flex flex-col h-full gap-3">
        <CustomerCard :customer="sale?.cliente" :readonly="isViewMode" @change-cliente="handleChangeCliente" />
        <div class="flex-1 min-h-0 overflow-y-auto no-scrollbar">
          <SaleCard :sale="sale" :readonly="isViewMode" :form="saleForm" :is-saving="isSaleFormSaving" :on-save="saveSaleForm" />
        </div>

        <div class="shrink-0 pt-4 flex flex-col gap-2">
          <template v-if="isEditMode">
            <BaseButton
              variant="primary"
              size="lg"
              class="w-full text-base font-bold py-4 shadow-lg shadow-brand-primary/20"
              :disabled="!sale?.produtos?.length"
              @click="openFinishModal"
            >
              <div class="flex flex-col items-center">
                <span>Finalizar Venda</span>
                <span class="text-[9px] opacity-70 font-normal">Ctrl+Enter</span>
              </div>
            </BaseButton>
          </template>
          <template v-else>
            <BaseButton variant="secondary" size="md" class="w-full" @click="closeSaleModal()">
              Fechar
            </BaseButton>
          </template>
        </div>
      </section>
    </main>
    <ItemModal :sale-id="selectedSaleId" />
    <AddProductModal
      :is-open="addProductModal.isAddProductModalOpen"
      :sale-id="selectedSaleId"
      :current-items="sale?.produtos"
      :termo-inicial="addProductModal.termoInicial"
      @close="addProductModal.closeAddProductModal"
    />
    <CancelSaleModal
      :is-open="cancelSaleModalIsOpen"
      :sale="sale ?? null"
      @close="cancelSaleModalIsOpen = false"
      @success="cancelSaleModalIsOpen = false; closeSaleModal()"
    />
    <FinishSaleModal :sale="sale" @finalized="handleFinalized" />
    <GerenteAprovacaoModal
      :is-open="gerenteDesconto.isOpen.value"
      :is-loading="gerenteDesconto.isLoading.value"
      @confirmar="gerenteDesconto.confirmar"
      @cancelar="gerenteDesconto.cancelar"
    />

    <!-- Print Infrastructure -->
    <PrintFormatSelectModal
      :is-open="isPrintSelectModalOpen"
      subtitle="Selecione o formato para impressão da venda."
      @close="closePrintSelectModal"
      @select="handlePrintFormatSelected"
    />

    <SalePrintTemplate
      v-if="saleForPrint && printFormat === 'A4'"
      :sale="saleForPrint"
      :type="(printType as 'VENDA')"
      :payment-method-resolver="resolvePaymentMethodName"
    />

    <SalePrintCupom
      v-if="saleForPrint && printFormat === 'CUPOM'"
      :sale="saleForPrint"
      :type="(printType as 'VENDA')"
      :payment-method-resolver="resolvePaymentMethodName"
    />
  </BaseModal>
</template>
