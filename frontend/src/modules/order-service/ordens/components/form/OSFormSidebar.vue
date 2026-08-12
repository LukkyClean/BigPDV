<script setup lang="ts">
import OSClientCard from './OSClientCard.vue';
import OSSummaryCard from './OSSummaryCard.vue';
import { useOSFormView } from '../../context/useOSFormView.context';

const view = useOSFormView();
</script>

<template>
  <fieldset :disabled="view.isStructureLocked.value" class="contents lg:block space-y-4">
    <OSSummaryCard
      :subtotal="view.displaySubtotal.value"
      :valor-entrega="view.displayValorEntrega.value"
      :valor-desconto="view.displayValorDesconto.value"
      :valor-total="view.displayValorTotal.value"
      :valor-entrada="view.displayValorEntrada.value"
      :forma-pagamento-entrada-id="view.displayFormaPagamentoEntradaId.value"
      :valor-acrescimo="view.displayValorAcrescimo.value"
      :is-locked="view.isStructureLocked.value"
      :is-finalizada="view.isFinalizada.value"
      :pagamentos="view.currentOSData.value?.pagamentos ?? []"
      :credito-ao-reabrir="view.currentOSData.value?.credito_anterior ?? view.creditoAoReabrir.value"
      :saldo-credito-cliente="view.isCreateMode.value ? view.saldoCreditoCliente.value : 0"
      :status="view.currentOSData.value?.status"
      :situacao-equipamento="view.currentOSData.value?.situacao_equipamento"
      :os-number="view.osNumber.value"
      :data-criacao="view.currentOSData.value?.data_criacao"
      :data-finalizacao="view.currentOSData.value?.data_finalizacao"
      @update:valor-entrada="view.handleValorEntradaUpdate"
      @update:valor-entrega="view.handleValorEntregaUpdate"
      @update:forma-pagamento-entrada-id="view.handleFormaPagamentoEntradaUpdate"
      @usar-credito="view.handleUsarCredito"
    />

    <OSClientCard
      :cliente="view.currentCliente.value"
      :is-edit-mode="view.isEditMode.value"
      :is-locked="view.isStructureLocked.value"
      @change-cliente="view.handleChangeCliente"
      @update-cliente="view.handleUpdateCliente"
      @open-historico="view.openHistoricoModal"
    />
  </fieldset>
</template>
