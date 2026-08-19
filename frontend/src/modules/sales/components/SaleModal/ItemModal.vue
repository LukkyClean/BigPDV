<script setup lang="ts">
import { X, Info, Tag, Lock, AlertTriangle } from 'lucide-vue-next';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import MoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import UnitValueInput from './UnitValueInput.vue';
import AvisoEstoqueNegativoModal from './AvisoEstoqueNegativoModal.vue';
import GerenteAprovacaoModal from '@/shared/components/commons/GerenteAprovacaoModal/GerenteAprovacaoModal.vue';

import { useItemModal } from '../../composables/flows/useItemModal';
import { useItemSaleForm } from '../../composables/form/useItemSaleForm';

import { formatCurrency } from '@/shared/utils/finance';
import { recursoDisponivel } from '@/shared/config/planos';
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useConfiguracoesStore } from '@/shared/stores/configuracoes.store';

const props = defineProps<{
  saleId: number | null;
  isOrcamento?: boolean;
}>();

const { closeItemModal, itemModalIsOpen, isCreateMode, selectedItem, descricaoInicial } = useItemModal();
const { requerPinAlterarPreco } = storeToRefs(useConfiguracoesStore());

const canEditPrice = computed(() =>
  isCreateMode.value ||
  selectedItem.value?.tipo_produto === 'AVULSO' ||
  requerPinAlterarPreco.value
);

const onSucess = () => closeItemModal();

const {
  descricao,
  valorUnitario,
  quantidade,
  desconto,
  custo,
  subtotal,
  total,
  errors,
  isSubmitting,
  submit,
  resetForm,
  increaseQuantity,
  decreaseQuantity,
  avisoEstoqueOpen,
  confirmarSalvarComEstoqueNegativo,
  gerentePreco,
} = useItemSaleForm(
  props.saleId,
  selectedItem,
  onSucess,
  props.isOrcamento,
  requerPinAlterarPreco,
  descricaoInicial,
);

// Custo interno só se aplica ao avulso: produto cadastrado tem o custo vindo do
// livro de estoque, congelado na baixa.
const isAvulso = computed(() => isCreateMode.value || selectedItem.value?.tipo_produto === 'AVULSO');
const nfeDisponivel = recursoDisponivel('nfe');

const sobraItem = computed(() => {
  if (custo.value <= 0) return null;
  return (valorUnitario.value - custo.value) * quantidade.value;
});

const displaySubtotal = computed(() => {
  return formatCurrency(subtotal.value * 100);
});

const displayDesconto = computed(() => {
  return formatCurrency(desconto.value * 100);
});

const displayTotal = computed(() => {
  return formatCurrency(total.value * 100);
});

function handleCloseModal() {
  resetForm();
  closeItemModal();
}
</script>

<template>
  <AvisoEstoqueNegativoModal
    :is-open="avisoEstoqueOpen"
    :nome-produto="selectedItem?.nome ?? ''"
    :estoque-atual="selectedItem?.estoque_disponivel ?? 0"
    :quantidade-desejada="quantidade"
    @confirmar="confirmarSalvarComEstoqueNegativo"
    @cancelar="avisoEstoqueOpen = false"
  />
  <GerenteAprovacaoModal
    :is-open="gerentePreco.isOpen.value"
    :is-loading="gerentePreco.isLoading.value"
    @confirmar="gerentePreco.confirmar"
    @cancelar="gerentePreco.cancelar"
  />
  <BaseModal :is-open="itemModalIsOpen" title="Produto Avulso" size="lg">
    <template #header>
      <div class="flex items-center justify-between px-6 py-4 border-b border-zinc-200">
        <div class="flex items-center gap-3">
          <h2 class="text-xl font-bold text-zinc-800">
            {{ isCreateMode ? 'Adicionar Produto Avulso' : 'Editar Produto' }}
          </h2>
        </div>

        <button
          type="button"
          class="p-2 text-zinc-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
          @click="handleCloseModal"
        >
          <X :size="20" />
        </button>
      </div>
    </template>

    <div class="w-full flex flex-col">
      <div class="p-4 w-full bg-brand-primary/20 rounded-xl">
        <div class="flex items-center justify-center gap-5">
          <Info :size="35" class="text-brand-primary" />
          <div class="flex flex-col gap-1">
            <h1 class="font-bold text-sm text-brand-primary">
              {{
                isCreateMode
                  ? 'Aqui você pode adicionar um produto avulso à venda'
                  : 'Aqui você pode editar as informações do produto selecionado'
              }}
            </h1>
            <p class="font-medium text-xs text-zinc-500">
              {{
                isCreateMode
                  ? 'Esses produtos não estão cadastrados no estoque e são ideais para itens únicos ou personalizados.'
                  : ' Lembre-se de que essas alterações não afetarão outros produtos ou vendas.'
              }}
            </p>
          </div>
        </div>
      </div>

      <div v-if="isAvulso && nfeDisponivel" class="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-xl">
        <div class="flex items-start gap-2.5">
          <AlertTriangle :size="16" class="text-amber-500 mt-0.5 shrink-0" />
          <div>
            <p class="text-sm font-semibold text-amber-700">Emissão fiscal indisponível</p>
            <p class="text-xs text-amber-600 mt-0.5">
              Itens avulsos impedem a emissão de nota fiscal. Para emitir NF-e nesta venda,
              cadastre o produto no catálogo e adicione-o pela busca.
            </p>
          </div>
        </div>
      </div>

      <form class="mt-10">
        <div class="grid grid-cols-8 gap-5">
          <div class="col-span-8">
            <BaseInput
              v-model="descricao"
              label="Nome do produto"
              :required="isCreateMode ? true : false"
              :disabled="!isCreateMode"
              placeholder="Insira a descrição do produto"
              :error="errors.descricao"
            />
          </div>
          <div class="col-span-5">
            <MoneyInput
              v-model="valorUnitario"
              :disabled="!canEditPrice"
              :required="isCreateMode ? true : false"
              label="Preço unitário"
              :error="errors.valor_unitario"
            />
          </div>
          <div class="col-span-3 h-full flex flex-col gap-1">
            <label class="text-xs font-medium text-zinc-700"
              >Quantidade <span v-if="isCreateMode" class="text-red-500">*</span>
            </label>
            <UnitValueInput
              v-model="quantidade"
              class="rounded-md"
              @decrease="decreaseQuantity"
              @increase="increaseQuantity"
            />
          </div>
          <div class="col-span-5">
            <MoneyInput
              v-model.number="desconto"
              type="number"
              label="Desconto"
              :max="subtotal"
              :error="errors.desconto"
            />
          </div>
        </div>

        <!--
          Custo interno. Item avulso não passa pelo estoque, então sem declarar
          aqui ele entra no relatório como receita sem custo e infla o lucro.
          NÃO aparece em nenhuma via impressa.
        -->
        <div v-if="isAvulso" class="mt-5 rounded-xl border border-zinc-200 bg-zinc-50/60 p-3">
          <div class="flex items-center gap-1.5 mb-2">
            <Lock :size="13" class="text-zinc-400" />
            <span class="text-xs font-semibold text-zinc-500 uppercase tracking-wide">
              Custo para a loja
            </span>
            <span class="text-[10px] text-zinc-400">(opcional)</span>
          </div>
          <div class="grid grid-cols-8 gap-5 items-end">
            <div class="col-span-5">
              <MoneyInput v-model="custo" label="" />
            </div>
            <p v-if="sobraItem !== null" class="col-span-3 text-xs text-zinc-500 pb-2">
              Sobra
              <strong :class="sobraItem >= 0 ? 'text-emerald-600' : 'text-red-600'">
                {{ formatCurrency(Math.round(sobraItem * 100)) }}
              </strong>
            </p>
          </div>
          <p class="mt-1.5 text-[11px] text-zinc-400 leading-snug">
            Quanto você pagou por este item. Fica só no relatório —
            <strong class="text-zinc-500">o cliente nunca vê este valor</strong>.
          </p>
        </div>
      </form>

      <div
        class="p-4 mt-20 w-full bg-brand-primary/10 border border-mid-gray/20 shadow-md rounded-xl"
      >
        <div class="flex items-center">
          <div
            class="w-15 h-15 bg-white rounded-full flex items-center justify-center text-brand-primary"
          >
            <Tag :size="30" />
          </div>

          <div class="w-full flex justify-around">
            <div>
              <h2 class="font-semibold text-[10px] text-mid-gray uppercase">Quantidade</h2>
              <p class="font-bold text-xl sm:text-md text-zinc-700">{{ `${quantidade} un.` }}</p>
            </div>
            <div>
              <h2 class="font-semibold text-[10px] text-mid-gray uppercase">Subtotal</h2>
              <p class="font-bold text-xl sm:text-md text-zinc-700">{{ displaySubtotal }}</p>
            </div>
            <div>
              <h2 class="font-semibold text-[10px] text-mid-gray uppercase">Desconto</h2>
              <p class="font-bold text-xl sm:text-md text-zinc-700">{{ displayDesconto }}</p>
            </div>
            <div>
              <h2 class="font-semibold text-[10px] text-brand-primary/70 uppercase">
                Total do Item
              </h2>
              <p class="font-bold text-xl sm:text-md text-brand-primary">{{ displayTotal }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-end gap-3">
        <BaseButton variant="secondary" size="md" @click="handleCloseModal">Cancelar</BaseButton>
        <BaseButton variant="primary" size="md" type="submit" :loading="isSubmitting" @click="submit">{{
          isCreateMode ? 'Adicionar' : 'Salvar Alterações'
        }}</BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
