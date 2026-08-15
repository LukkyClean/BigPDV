<script setup lang="ts">
import { ref, computed } from 'vue';
import { Plus, AlertTriangle } from 'lucide-vue-next';
import GerenteAprovacaoModal from '@/shared/components/commons/GerenteAprovacaoModal/GerenteAprovacaoModal.vue';
import { useGerenteAprovacao } from '@/shared/composables/useGerenteAprovacao';
import { useToast } from '@/shared/composables/useToast';
import { useMagicKeys, whenever } from '@vueuse/core';

import PageReview from '@/shared/components/layout/PageReview/PageReview.vue';
import BaseTab2 from '@/shared/components/ui/BaseTab2/BaseTab2.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import ConfirmationTemplate from '@/shared/components/templates/ConfirmationTemplate.vue';
import PrintFormatSelectModal from '@/shared/components/print/PrintFormatSelectModal.vue';

import SalesStatus from './components/SalesStatus.vue';
import SaleTable from './components/SaleTable.vue';
import CaixaBar from './caixa/components/CaixaBar.vue';
import { useSessaoCaixaQuery } from './caixa/composables/queries/useSessaoCaixaQuery';
import SaleModal from './components/SaleModal.vue';
import SalePrintTemplate from './components/print/SalePrintTemplate.vue';
import SalePrintCupom from './components/print/SalePrintCupom.vue';

import OrcamentosStatus from './components/OrcamentosStatus.vue';
import OrcamentoTable from './components/OrcamentoTable.vue';
import OrcamentoModal from './components/OrcamentoModal.vue';

import { useCustomerSearchModal } from './composables/flows/useCustomerSearchModal';
import { useSaleModal } from './composables/flows/useSaleModal';
import { useFinishSaleModal } from './composables/flows/useFinishSaleModal';
import { useConfirmSaleAction } from './composables/flows/useConfirmSaleAction';
import { useDeleteSaleMutation } from './composables/mutates/useDeleteSaleMutation';
import { useReopenSaleMutation } from './composables/mutates/useReopenSaleMutation';
import { useSalePrintFlow } from './composables/flows/useSalePrintFlow';
import { useOrcamentoPrintFlow } from './composables/flows/useOrcamentoPrintFlow';
import { useOrcamentoModal } from './composables/flows/useOrcamentoModal';
import { useCreateOrcamentoMutation } from './composables/mutates/useCreateOrcamentoMutation';
import { useDeleteOrcamentoMutation } from './composables/mutates/useDeleteOrcamentoMutation';
import { useConverterOrcamentoMutation } from './composables/mutates/useConverterOrcamentoMutation';
import { useAuthStore } from '@/shared/stores/auth.store';
import { SALES_TAB_OPTIONS } from './constants';

const activeTab = ref<'vendas' | 'orcamentos'>('vendas');

const pageTitle = computed(() =>
  activeTab.value === 'vendas' ? 'Vendas' : 'Orçamentos',
);

const pageDescription = computed(() =>
  activeTab.value === 'vendas'
    ? 'Gerencie as vendas do seu estabelecimento.'
    : 'Gerencie os orçamentos do seu estabelecimento.',
);

const authStore = useAuthStore();

const { openCustomerModal, openCustomerModalForConversion } = useCustomerSearchModal();

// Trava do caixa na porta de entrada.
//
// A garantia de verdade esta no backend (create_sale e finish_sale); isto aqui e
// para o operador nao montar o carrinho inteiro e descobrir no checkout que o
// caixa esta fechado. O botao de abrir o caixa fica logo acima, na mesma tela.
//
// `vendaBloqueada` so e verdadeira com as DUAS chaves ligadas e sem turno
// aberto: loja que nao usa caixa nunca ve diferenca.
const { caixaAberto, caixaHabilitado, exigeCaixaAberto } = useSessaoCaixaQuery();
const vendaBloqueada = computed(
  () => caixaHabilitado.value && exigeCaixaAberto.value && !caixaAberto.value,
);
const { openSaleEditModal, saleModalIsOpen } = useSaleModal();
const { openFinishModal } = useFinishSaleModal();
const { openOrcamentoModal, closeOrcamentoModal, orcamentoModalIsOpen } = useOrcamentoModal();

const createOrcamentoMutation = useCreateOrcamentoMutation();
const deleteOrcamentoMutation = useDeleteOrcamentoMutation();
const converterMutation = useConverterOrcamentoMutation();

const {
  saleForPrint,
  printType,
  printFormat,
  isPrintSelectModalOpen,
  printSale,
  handlePrintFormatSelected,
  closePrintSelectModal,
  resolvePaymentMethodName,
} = useSalePrintFlow();

const {
  orcamentoForPrint,
  printFormat: orcPrintFormat,
  isPrintSelectModalOpen: isOrcPrintSelectOpen,
  printOrcamento,
  handlePrintFormatSelected: handleOrcPrintFormatSelected,
  closePrintSelectModal: closeOrcPrintSelectModal,
} = useOrcamentoPrintFlow();

const { F2 } = useMagicKeys();
whenever(F2, () => {
  if (saleModalIsOpen.value || orcamentoModalIsOpen.value) return;

  if (activeTab.value === 'vendas') {
    // O atalho tem que respeitar a mesma trava do botao, senao F2 fura a regra.
    if (vendaBloqueada.value) return;
    openCustomerModal();
  } else {
    handleNewOrcamento();
  }
});

const {
  confirmModalIsOpen,
  confirmModalState,
  confirmModalPending,
  openConfirmModal,
  closeConfirmModal,
  handleConfirm,
} = useConfirmSaleAction();

const discardMutation = useDeleteSaleMutation();
const reopenMutation = useReopenSaleMutation();
const gerenteReopen = useGerenteAprovacao();
const toast = useToast();

function handleFinishFromTable(saleId: number) {
  openSaleEditModal(saleId);
  setTimeout(() => openFinishModal(), 300);
}

function handleCancelFromTable(saleId: number) {
  openConfirmModal({
    title: 'Descartar Rascunho?',
    message: 'Tem certeza que deseja descartar este rascunho de venda? Esta ação não pode ser desfeita.',
    variant: 'danger',
    label: 'DESCARTAR',
    action: () => {
      confirmModalPending.value = true;
      discardMutation.mutate(
        { saleId },
        {
          onSuccess: () => closeConfirmModal(),
          onSettled: () => { confirmModalPending.value = false; },
        },
      );
    },
  });
}

async function executarReopen(saleId: number, codigoGerente?: string): Promise<void> {
  try {
    await reopenMutation.mutateAsync({ saleId, codigoGerente });
    closeConfirmModal();
  } catch (error: any) {
    const detail = error?.response?.data?.detail;
    if (detail === 'REQUER_APROVACAO_GERENTE') {
      closeConfirmModal();
      const pin = await gerenteReopen.pedirPin();
      if (pin) await executarReopen(saleId, pin);
    } else if (detail === 'PIN_GERENTE_INVALIDO') {
      toast.error('PIN do gerente inválido');
      const pin = await gerenteReopen.pedirPin();
      if (pin) await executarReopen(saleId, pin);
    }
  } finally {
    confirmModalPending.value = false;
  }
}

function handleReopenFromTable(saleId: number) {
  openConfirmModal({
    title: 'Reabrir Venda?',
    message: 'Deseja reabrir a Venda',
    highlightText: `Nº ${String(saleId).padStart(6, '0')}`,
    variant: 'primary',
    label: 'CONFIRMAR',
    action: () => {
      confirmModalPending.value = true;
      void executarReopen(saleId);
    },
  });
}

async function handlePrintFromTable(saleId: number, _status: string) {
  await printSale(saleId, 'VENDA');
}

async function handlePrintOrcamento(orcamentoId: number) {
  await printOrcamento(orcamentoId);
}

// --- Orçamento handlers ---

function handleNewOrcamento() {
  createOrcamentoMutation.mutate(
    { funcionario_id: authStore.userData?.funcionario_id as number },
    {
      onSuccess: (created) => {
        openOrcamentoModal(created.id);
      },
    },
  );
}

function handleDeleteOrcamentoFromTable(orcamentoId: number) {
  openConfirmModal({
    title: 'Excluir Orçamento?',
    message: 'Tem certeza que deseja excluir o Orçamento',
    highlightText: `Nº ${String(orcamentoId).padStart(6, '0')}`,
    variant: 'danger',
    label: 'EXCLUIR',
    action: () => {
      confirmModalPending.value = true;
      deleteOrcamentoMutation.mutate(
        { orcamentoId },
        {
          onSuccess: () => closeConfirmModal(),
          onSettled: () => { confirmModalPending.value = false; },
        },
      );
    },
  });
}

function handleConverterFromTable(orcamentoId: number) {
  openCustomerModalForConversion((clienteId) => {
    if (!clienteId) return;
    converterMutation.mutate(
      { orcamentoId, payload: { cliente_id: clienteId } },
      {
        onSuccess: (createdSale) => {
          activeTab.value = 'vendas';
          openSaleEditModal(createdSale.id);
        },
      },
    );
  });
}

function handleConverterFromModal(orcamentoId: number) {
  closeOrcamentoModal();
  handleConverterFromTable(orcamentoId);
}

function handleOpenSaleFromOrcamento(saleId: number) {
  closeOrcamentoModal();
  activeTab.value = 'vendas';
  setTimeout(() => openSaleEditModal(saleId), 300);
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
        <BaseTab2 :options="SALES_TAB_OPTIONS" v-model="activeTab" />
        <BaseButton
          v-if="activeTab === 'vendas'"
          variant="primary"
          size="md"
          type="button"
          class="flex gap-1"
          :disabled="vendaBloqueada"
          :title="vendaBloqueada ? 'Abra o caixa para começar a vender' : ''"
          @click="openCustomerModal"
        >
          <Plus :size="20" />
          Nova venda
        </BaseButton>
        <BaseButton
          v-else
          variant="primary"
          size="md"
          type="button"
          class="flex gap-1"
          :is-loading="createOrcamentoMutation.isPending.value"
          @click="handleNewOrcamento"
        >
          <Plus :size="20" />
          Novo orçamento
        </BaseButton>
      </div>
    </div>

    <!-- Tab: Vendas -->
    <template v-if="activeTab === 'vendas'">
      <!-- Barra do caixa. Não renderiza NADA quando a loja não usa controle de
           caixa (o padrão), e a query do turno nem chega a ser disparada — tela
           e rede idênticas para quem não ligou a chave. -->
      <CaixaBar />
      <SalesStatus />
      <SaleTable
        @cancel="handleCancelFromTable"
        @finish="handleFinishFromTable"
        @reopen="handleReopenFromTable"
        @print="handlePrintFromTable"
      />
    </template>

    <!-- Tab: Orçamentos -->
    <template v-else>
      <OrcamentosStatus />
      <OrcamentoTable
        @delete="handleDeleteOrcamentoFromTable"
        @converter="handleConverterFromTable"
        @print="handlePrintOrcamento"
      />
    </template>

    <!-- Shared: Confirmation Modal -->
    <BaseModal
      :is-open="confirmModalIsOpen"
      :title="confirmModalState.title"
      size="sm"
      overlay
      @close="closeConfirmModal"
    >
      <ConfirmationTemplate
        :icon="AlertTriangle"
        icon-bg-class="bg-brand-primary-light"
        icon-color-class="text-brand-primary"
      >
        <template #description>
          <p class="text-sm text-slate-500 leading-relaxed">
            {{ confirmModalState.message }}
            <span v-if="confirmModalState.highlightText" class="font-bold text-slate-800 block mt-1 text-base">
              {{ confirmModalState.highlightText }}
            </span>
          </p>
        </template>

        <template #footer>
          <div class="flex gap-3 w-full mt-6">
            <BaseButton
              variant="secondary"
              class="flex-1"
              :disabled="confirmModalPending"
              @click="closeConfirmModal"
            >
              VOLTAR
            </BaseButton>
            <BaseButton
              :variant="confirmModalState.variant"
              :is-loading="confirmModalPending"
              class="flex-1"
              @click="handleConfirm"
            >
              {{ confirmModalState.label }}
            </BaseButton>
          </div>
        </template>
      </ConfirmationTemplate>
    </BaseModal>

    <!-- Sale Modal -->
    <SaleModal />

    <GerenteAprovacaoModal
      :is-open="gerenteReopen.isOpen.value"
      :is-loading="gerenteReopen.isLoading.value"
      @confirmar="gerenteReopen.confirmar"
      @cancelar="gerenteReopen.cancelar"
    />

    <!-- Orçamento Modal -->
    <OrcamentoModal @converter="handleConverterFromModal" @open-sale="handleOpenSaleFromOrcamento" @print="handlePrintOrcamento" />

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
      :type="printType as 'VENDA'"
      :payment-method-resolver="resolvePaymentMethodName"
    />

    <SalePrintCupom
      v-if="saleForPrint && printFormat === 'CUPOM'"
      :sale="saleForPrint"
      :type="printType as 'VENDA'"
      :payment-method-resolver="resolvePaymentMethodName"
    />

    <!-- Orcamento Print Infrastructure -->
    <PrintFormatSelectModal
      :is-open="isOrcPrintSelectOpen"
      subtitle="Selecione o formato para impressão do orçamento."
      @close="closeOrcPrintSelectModal"
      @select="handleOrcPrintFormatSelected"
    />

    <SalePrintTemplate
      v-if="orcamentoForPrint && orcPrintFormat === 'A4'"
      :sale="orcamentoForPrint"
      type="ORCAMENTO"
    />

    <SalePrintCupom
      v-if="orcamentoForPrint && orcPrintFormat === 'CUPOM'"
      :sale="orcamentoForPrint"
      type="ORCAMENTO"
    />
  </div>
</template>
