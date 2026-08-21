<script setup lang="ts">
import { ref, computed } from 'vue';
import { Plus, AlertTriangle, Zap } from 'lucide-vue-next';
import { storeToRefs } from 'pinia';
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
import { useBalcaoStore } from '@/shared/stores/balcao.store';
import { useConfiguracoesStore } from '@/shared/stores/configuracoes.store';
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

const { openCustomerModal, openCustomerModalForConversion, iniciarVendaSemCliente } = useCustomerSearchModal();

// Modo Balcao: chave desta MAQUINA (localStorage), desligada por padrao.
const balcaoStore = useBalcaoStore();
const { modoBalcao } = storeToRefs(balcaoStore);
const { exigirClienteIdentificado, usarFilaDoCaixa } = storeToRefs(useConfiguracoesStore());

/**
 * O comeco da venda.
 *
 * Fora do Modo Balcao e com ele ligado numa loja que exige cliente, o caminho e
 * o de sempre: o modal de cliente primeiro. So a adega (balcao ligado E sem
 * exigencia de cliente) pula direto para o carrinho.
 *
 * A segunda condicao nao e detalhe: sem ela a venda nasceria sem cliente para
 * ser recusada la na finalizacao por `venda.py`, com o carrinho ja montado.
 */
function comecarVenda() {
  if (modoBalcao.value && !exigirClienteIdentificado.value) {
    iniciarVendaSemCliente();
    return;
  }
  openCustomerModal();
}

function handleNovaVenda() {
  if (!avisarCaixaFechado.value) {
    comecarVenda();
    return;
  }

  openConfirmModal({
    title: 'Caixa fechado',
    message:
      'Você pode montar esta venda, mas não vai conseguir finalizá-la enquanto o caixa estiver fechado.',
    highlightText: 'Abra o caixa antes de chamar o cliente.',
    variant: 'primary',
    // Maiúscula como as irmãs deste modal ('DESCARTAR'): o rótulo é o botão
    // que age, e a caixa alta é o que o distingue do 'VOLTAR' ao lado.
    label: 'MONTAR MESMO ASSIM',
    action: () => {
      closeConfirmModal();
      comecarVenda();
    },
  });
}

// O CAIXA NAO BARRA MAIS A ENTRADA -- so o dinheiro.
//
// Ate 21/08/2026 este bloco desabilitava "Nova venda" (e o F2) quando as duas
// chaves estavam ligadas e nao havia turno aberto. A trava saiu da criacao da
// venda no backend por decisao do dono: montar carrinho nao move dinheiro, e
// exigir turno para comecar impedia o atendente de montar a venda que o CAIXA
// vai receber -- alem de deixar a maquina RETAGUARDA sem saida, porque nela o
// botao de abrir caixa nem aparece.
//
// Quem avisa agora e a `CaixaBar`, logo acima: "voce pode montar vendas, mas
// nao finaliza-las". Aviso, e nao trava. A garantia continua no `finish_sale`.
//
// O turno volta a ser consultado aqui -- mas para AVISAR, nao para travar.
//
// Tirar a trava da criacao devolveu ao operador a liberdade de montar a venda
// sem turno, e junto tirou o unico ganho que aquela trava tinha: saber ANTES de
// montar o carrinho inteiro. Quem trabalha sozinho descobria a recusa no
// checkout, com o cliente na frente e os produtos ja digitados.
//
// O aviso e a forma de ter os dois: a venda continua podendo nascer, e ninguem
// perde tempo sem saber.
const { caixaAberto, caixaHabilitado, exigeCaixaAberto } = useSessaoCaixaQuery();

/**
 * Avisar so faz sentido para quem VAI ficar sem saida.
 *
 * Com a fila ligada, montar sem turno e o fluxo NORMAL do atendente: ele monta e
 * entrega ao caixa. Perguntar "tem certeza?" toda vez seria atrito no caminho
 * principal do dia dele -- e o rodape do SaleModal ja explica para onde a venda
 * vai. Sem a fila, montar leva a uma recusa no checkout: ai o aviso paga.
 */
const avisarCaixaFechado = computed(
  () =>
    caixaHabilitado.value &&
    exigeCaixaAberto.value &&
    !caixaAberto.value &&
    !usarFilaDoCaixa.value,
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
    // Sem trava aqui, pelo mesmo motivo do botao: quem barra e a finalizacao.
    handleNovaVenda();
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

        <!-- Modo Balcão: acelera o fluxo desta máquina. Fica ao lado de "Nova
             venda" porque é ali que ele muda o comportamento. Desligado, o
             módulo inteiro se comporta como sempre. -->
        <button
          v-if="activeTab === 'vendas'"
          type="button"
          :class="[
            'flex items-center gap-1.5 px-3 rounded-lg border text-sm font-semibold transition-all cursor-pointer',
            modoBalcao
              ? 'border-brand-primary bg-brand-primary/10 text-brand-primary'
              : 'border-zinc-200 bg-white text-zinc-400 hover:text-zinc-600 hover:border-zinc-300',
          ]"
          :title="modoBalcao
            ? 'Modo Balcão ligado — a venda começa no produto e emenda a próxima. Clique para desligar.'
            : 'Modo Balcão desligado — clique para vender no ritmo de balcão.'"
          @click="balcaoStore.alternar()"
        >
          <Zap :size="16" />
          Balcão
        </button>

        <BaseButton
          v-if="activeTab === 'vendas'"
          variant="primary"
          size="md"
          type="button"
          class="flex gap-1"
          @click="handleNovaVenda"
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
    <!-- O <SaleModal /> NAO se monta aqui: ele ja vive no MainLayout, que e pai
         desta rota. Montar nos dois punha DUAS instancias na tela ao mesmo tempo,
         e como o estado da venda e global (refs de modulo), o mesmo Esc era
         tratado duas vezes: a primeira fechava a modal de cima, a segunda via a
         flag ja em false e fechava o PDV inteiro. Achado em 20/08/2026. -->

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
