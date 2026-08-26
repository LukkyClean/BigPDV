<script setup lang="ts">
import { ref, computed } from 'vue';
import { refDebounced } from '@vueuse/core';
import { ShoppingCart, FileCheck, AlertTriangle } from 'lucide-vue-next';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseSearchInput from '@/shared/components/ui/BaseSearchInput/BaseSearchInput.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';

import { useSalesListQuery } from '@/modules/sales/composables/queries/useSalesListQuery';
import { useFiscalEmitirNfeMutation } from '../composables/useFiscalEmitirNfeMutation';
import { formatCurrency } from '@/shared/utils/finance';

import type { SaleSimpleRead } from '@/modules/sales/schemas/sale.schema';

interface Props {
  isOpen: boolean;
}

defineProps<Props>();

const emit = defineEmits<{
  close: [];
}>();

// --- Busca de vendas ---
const searchTerm = ref('');
const debouncedSearch = refDebounced(searchTerm, 400);

const filters = computed(() =>
  debouncedSearch.value
    ? { search: debouncedSearch.value, status: 'FINALIZADA' as const }
    : { status: 'FINALIZADA' as const },
);

const { data: salesData, isLoading } = useSalesListQuery(filters);

const vendas = computed(() => salesData.value?.vendas ?? []);

// --- Venda selecionada ---
const vendaSelecionada = ref<SaleSimpleRead | null>(null);

function selecionarVenda(venda: SaleSimpleRead) {
  vendaSelecionada.value = venda;
}

// --- Emissão ---
const emitirMutation = useFiscalEmitirNfeMutation();

function handleEmitir() {
  if (!vendaSelecionada.value) return;

  emitirMutation.mutate(
    { venda_id: vendaSelecionada.value.id },
    {
      onSuccess: () => {
        fecharModal();
      },
    },
  );
}

// --- Helpers ---
function fecharModal() {
  searchTerm.value = '';
  vendaSelecionada.value = null;
  emit('close');
}

function getNomeCliente(venda: SaleSimpleRead): string {
  if (!venda.cliente) return 'Sem cliente';
  if (venda.cliente.tipo === 'PF') return venda.cliente.nome || 'Sem nome';
  return venda.cliente.razao_social || 'Sem razão social';
}

function getDocumentoCliente(venda: SaleSimpleRead): string {
  if (!venda.cliente) return '';
  if (venda.cliente.tipo === 'PF') return venda.cliente.cpf || '';
  return venda.cliente.cnpj || '';
}

function formatarData(iso: string): string {
  return new Date(iso).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}
</script>

<template>
  <BaseModal
    :is-open="isOpen"
    title="Emitir NF-e"
    subtitle="Selecione uma venda finalizada para emissão da nota fiscal."
    size="md"
    @close="fecharModal"
  >
    <!-- Etapa 1: buscar e selecionar venda -->
    <template v-if="!vendaSelecionada">
      <BaseSearchInput
        v-model="searchTerm"
        placeholder="Buscar por número da venda ou nome do cliente"
      />

      <div class="mt-3 max-h-80 overflow-y-auto divide-y divide-zinc-100 -mx-1 px-1">
        <!-- Skeleton -->
        <template v-if="isLoading">
          <div v-for="n in 4" :key="n" class="flex items-center gap-3 px-2 py-3 animate-pulse">
            <div class="w-9 h-9 rounded-full bg-zinc-200 shrink-0" />
            <div class="flex-1 space-y-1.5">
              <div class="h-3 w-1/2 bg-zinc-200 rounded" />
              <div class="h-2.5 w-1/3 bg-zinc-100 rounded" />
            </div>
          </div>
        </template>

        <!-- Lista de vendas -->
        <template v-else-if="vendas.length > 0">
          <button
            v-for="venda in vendas"
            :key="venda.id"
            type="button"
            class="w-full flex items-center gap-3 px-2 py-3 rounded-xl text-left transition-colors hover:bg-zinc-50 cursor-pointer"
            @click="selecionarVenda(venda)"
          >
            <div
              class="w-9 h-9 rounded-full bg-brand-primary/10 flex items-center justify-center shrink-0"
            >
              <ShoppingCart :size="16" class="text-brand-primary" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-semibold text-zinc-900">
                Venda #{{ venda.numero_venda ?? venda.id }}
                <span class="font-normal text-zinc-500 ml-1">
                  · {{ formatCurrency(venda.total) }}
                </span>
              </p>
              <p class="text-[11px] text-zinc-400 truncate">
                {{ getNomeCliente(venda) }}
                <template v-if="getDocumentoCliente(venda)">
                  · {{ getDocumentoCliente(venda) }}
                </template>
                · {{ formatarData(venda.criado_em) }}
              </p>
            </div>
          </button>
        </template>

        <!-- Estado vazio -->
        <div v-else class="py-10 text-center text-zinc-400">
          <p class="text-sm font-medium">
            {{ searchTerm ? 'Nenhuma venda encontrada' : 'Vendas finalizadas aparecerão aqui' }}
          </p>
          <p class="text-xs mt-1">
            {{ searchTerm ? 'Tente outro termo de busca.' : 'Busque por número ou nome do cliente.' }}
          </p>
        </div>
      </div>
    </template>

    <!-- Etapa 2: confirmação -->
    <template v-else>
      <div class="space-y-4">
        <!-- Resumo da venda -->
        <div class="bg-zinc-50 rounded-xl p-4 space-y-2">
          <div class="flex items-center gap-2 mb-3">
            <FileCheck :size="18" class="text-brand-primary" />
            <span class="text-sm font-semibold text-zinc-700">
              Venda #{{ vendaSelecionada.numero_venda ?? vendaSelecionada.id }}
            </span>
          </div>

          <div class="grid grid-cols-2 gap-2 text-sm">
            <div>
              <p class="text-zinc-400 text-xs">Cliente</p>
              <p class="text-zinc-700 font-medium">{{ getNomeCliente(vendaSelecionada) }}</p>
            </div>
            <div>
              <p class="text-zinc-400 text-xs">Documento</p>
              <p class="text-zinc-700 font-medium">{{ getDocumentoCliente(vendaSelecionada) || '-' }}</p>
            </div>
            <div>
              <p class="text-zinc-400 text-xs">Valor Total</p>
              <p class="text-zinc-700 font-medium">{{ formatCurrency(vendaSelecionada.total) }}</p>
            </div>
            <div>
              <p class="text-zinc-400 text-xs">Data</p>
              <p class="text-zinc-700 font-medium">{{ formatarData(vendaSelecionada.criado_em) }}</p>
            </div>
          </div>
        </div>

        <!-- Aviso -->
        <div class="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <AlertTriangle :size="16" class="text-amber-500 shrink-0 mt-0.5" />
          <p class="text-xs text-amber-700">
            A NF-e será emitida para esta venda. Certifique-se de que os dados fiscais dos
            produtos e do cliente estão corretos antes de prosseguir.
          </p>
        </div>
      </div>
    </template>

    <template #footer>
      <div class="flex gap-2">
        <template v-if="vendaSelecionada">
          <BaseButton
            variant="secondary"
            class="flex-1"
            @click="vendaSelecionada = null"
          >
            Voltar
          </BaseButton>
          <BaseButton
            variant="primary"
            class="flex-1"
            :is-loading="emitirMutation.isPending.value"
            @click="handleEmitir"
          >
            Emitir NF-e
          </BaseButton>
        </template>
        <BaseButton v-else variant="secondary" class="w-full" @click="fecharModal">
          Cancelar
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
