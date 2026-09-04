<script setup lang="ts">
import { computed } from 'vue';
import { Pencil, Eye, CheckCircle, XCircle, RotateCcw, Printer, FileText } from 'lucide-vue-next';

import BaseTableContainer from '@/shared/components/commons/BaseTableContainer/BaseTableContainer.vue';
import BaseSearchInput from '@/shared/components/ui/BaseSearchInput/BaseSearchInput.vue';
import BaseFilter from '@/shared/components/ui/BaseFilter/BaseFilter.vue';
import PendenciasFiscaisModal from '@/shared/components/commons/PendenciasFiscaisModal.vue';
import { formatCurrency } from '@/shared/utils/finance';
import { tempoDecorrido as esperandoDesde } from '@/shared/utils/date.utils';
import { recursoDisponivel } from '@/shared/config/planos';
import { useEmitirFiscal } from '@/shared/composables/useEmitirFiscal';

import { useSaleTable } from '../composables/flows/useSaleTable';
import { useSaleModal } from '../composables/flows/useSaleModal';

import { SALE_FILTERS, STATUS_COLORS, SALE_FILTER_CONFIG, SALE_FILTER_CONFIG_COM_CAIXA } from '../constants';
import { storeToRefs } from 'pinia';
import { useConfiguracoesStore } from '@/shared/stores/configuracoes.store';

const { searchTerm, activeFilter, goToPage, sales, isLoading } = useSaleTable();
const { openSaleViewModal, openSaleEditModal } = useSaleModal();

// Loja que não ligou a fila não tem o que filtrar nem o que sinalizar —
// oferecer seria um botão que nunca traz nada e um selo que nunca aparece.
const { usarFilaDoCaixa } = storeToRefs(useConfiguracoesStore());
const filtrosDisponiveis = computed(() =>
  usarFilaDoCaixa.value ? SALE_FILTER_CONFIG_COM_CAIXA : SALE_FILTER_CONFIG,
);
const nfeDisponivel = recursoDisponivel('nfe');
const { pendencias, pendenciasModalOpen, isVerificando, emitirVenda } = useEmitirFiscal();

const emit = defineEmits<{
  (e: 'cancel', saleId: number): void;
  (e: 'finish', saleId: number): void;
  (e: 'reopen', saleId: number): void;
  (e: 'print', saleId: number, status: string): void;
}>();
</script>

<template>
  <BaseTableContainer
    :is-loading="isLoading"
    :is-empty="sales?.vendas.length === 0"
    :current-page="sales?.page"
    :total-pages="sales?.total_pages"
    :total-items="sales?.total"
    item-label="Venda"
    item-label-plural="Vendas"
    empty-title="Nenhuma venda encontrada"
    empty-description='Clique em "Nova Venda" para criar uma venda'
    @update:current-page="goToPage"
  >
    <template #toolbar>
      <BaseSearchInput v-model="searchTerm" placeholder="Buscar por número, cliente..." class="min-w-64 flex-1" />
      <BaseFilter v-model="activeFilter" :filter-config="filtrosDisponiveis" button-label="Filtros" />
    </template>

    <div class="overflow-x-auto">
      <table class="w-full text-left min-w-160">
        <thead>
          <tr
            class="bg-zinc-50/50 text-[10px] uppercase tracking-wider text-zinc-500 font-bold border-b border-zinc-100"
          >
            <th class="px-4 md:px-6 py-3 md:py-4">Nº Venda</th>
            <th class="px-4 md:px-6 py-3 md:py-4">Cliente</th>
            <th class="px-4 md:px-6 py-3 md:py-4">Status</th>
            <th class="px-4 md:px-6 py-3 md:py-4">Data da Venda</th>
            <th class="px-4 md:px-6 py-3 md:py-4">Valor</th>
            <th class="px-4 md:px-6 py-3 md:py-4 text-right min-w-40">Ações Rápidas</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-zinc-100">
          <tr
            v-for="sale in sales?.vendas"
            :key="sale.id"
            class="hover:bg-zinc-50/50 transition-colors group cursor-pointer"
            @click="sale.status !== 'ATIVA' ? openSaleViewModal(sale.id) : openSaleEditModal(sale.id)"
          >
            <td class="px-4 md:px-6 py-3 md:py-4">
              <div
                v-if="sale.numero_venda"
                class="w-10 h-10 bg-brand-primary/10 rounded-xl flex flex-col items-center justify-center text-brand-primary"
              >
                <span class="text-[7px] opacity-70 font-medium leading-none">VENDA</span>
                <span class="text-sm font-bold leading-none mt-0.5">{{ sale.numero_venda }}</span>
              </div>
              <div
                v-else
                class="w-10 h-10 bg-zinc-100 rounded-xl flex flex-col items-center justify-center text-zinc-400"
              >
                <span class="text-[7px] opacity-70 font-medium leading-none">RASCUNHO</span>
                <span class="text-[10px] font-bold leading-none mt-0.5">---</span>
              </div>
            </td>

            <td class="px-4 md:px-6 py-3 md:py-4">
              <div class="flex flex-col">
                <span class="text-sm font-semibold text-zinc-900 group-hover:text-brand-primary transition-colors">
                  <span v-if="!!sale.cliente">{{ sale.cliente?.tipo === "PF" ? sale.cliente?.nome : sale.cliente?.razao_social }}</span>
                  <span v-else class="text-red-400">Venda sem cliente</span>
                </span>
                <span class="text-[10px] text-zinc-400 mt-0.5">{{ sale.cliente?.tipo === "PF" ? sale.cliente?.cpf : sale.cliente?.cnpj }}</span>
              </div>
            </td>

            <td class="px-4 md:px-6 py-3 md:py-4">
              <span
                :class="[
                  'px-2 md:px-3 py-1 rounded-full text-[10px] md:text-[11px] font-bold whitespace-nowrap',
                  STATUS_COLORS[sale.status]?.bg,
                  STATUS_COLORS[sale.status]?.text,
                ]"
              >
                {{ SALE_FILTERS[sale.status]?.label }}
              </span>
              <!--
                Selo da fila, ao lado do status e não no lugar dele: a venda
                continua ATIVA, e trocar o rótulo faria parecer um quarto status
                que não existe no banco. O tempo de espera é o que faz o caixa
                escolher qual pegar primeiro.
              -->
              <span
                v-if="usarFilaDoCaixa && sale.enviada_ao_caixa_em"
                class="ml-1.5 inline-flex items-center gap-1 px-2 py-1 rounded-full text-[10px] md:text-[11px] font-bold whitespace-nowrap bg-emerald-50 text-emerald-700"
                :title="`Entregue ao caixa ${esperandoDesde(sale.enviada_ao_caixa_em)}`"
              >
                No caixa · {{ esperandoDesde(sale.enviada_ao_caixa_em) }}
              </span>
            </td>

            <td class="px-4 md:px-6 py-3 md:py-4 text-xs md:text-sm font-medium text-zinc-600 group-hover:text-brand-primary transition-colors">
              <span v-if="sale.status === 'FINALIZADA'">{{ sale.atualizado_em }}</span>
              <span v-else class="text-zinc-300">—</span>
            </td>

            <td class="px-4 md:px-6 py-3 md:py-4 text-xs md:text-sm font-medium text-zinc-600 group-hover:text-brand-primary transition-colors">
              <span v-if="sale.total > 0">{{ formatCurrency(sale.total) }}</span>
              <span v-else class="text-zinc-300">—</span>
            </td>

            <!-- Quick Actions -->
            <td class="px-4 md:px-6 py-3 md:py-4">
              <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <!-- ATIVA actions -->
                <template v-if="sale.status === 'ATIVA'">
                  <button
                    type="button"
                    class="inline-flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 transition hover:bg-blue-50 hover:text-brand-primary"
                    title="Editar"
                    @click.stop="openSaleEditModal(sale.id)"
                  >
                    <Pencil class="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    class="inline-flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700"
                    title="Imprimir"
                    @click.stop="emit('print', sale.id, sale.status)"
                  >
                    <Printer class="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    class="inline-flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 transition hover:bg-green-50 hover:text-green-600"
                    title="Finalizar"
                    @click.stop="emit('finish', sale.id)"
                  >
                    <CheckCircle class="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    class="inline-flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 transition hover:bg-red-50 hover:text-red-600"
                    title="Cancelar"
                    @click.stop="emit('cancel', sale.id)"
                  >
                    <XCircle class="h-4 w-4" />
                  </button>
                </template>

                <!-- FINALIZADA actions -->
                <template v-else-if="sale.status === 'FINALIZADA'">
                  <button
                    type="button"
                    class="inline-flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 transition hover:bg-blue-50 hover:text-brand-primary"
                    title="Visualizar"
                    @click.stop="openSaleViewModal(sale.id)"
                  >
                    <Eye class="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    class="inline-flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700"
                    title="Imprimir"
                    @click.stop="emit('print', sale.id, sale.status)"
                  >
                    <Printer class="h-4 w-4" />
                  </button>
                  <button
                    v-if="nfeDisponivel"
                    type="button"
                    class="inline-flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 transition hover:bg-emerald-50 hover:text-emerald-600"
                    title="Emitir Nota Fiscal"
                    :disabled="isVerificando"
                    @click.stop="emitirVenda(sale.id)"
                  >
                    <FileText class="h-4 w-4" />
                  </button>
                </template>

                <!-- CANCELADA actions -->
                <template v-else-if="sale.status === 'CANCELADA'">
                  <button
                    type="button"
                    class="inline-flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 transition hover:bg-blue-50 hover:text-brand-primary"
                    title="Visualizar"
                    @click.stop="openSaleViewModal(sale.id)"
                  >
                    <Eye class="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    class="inline-flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 transition hover:bg-amber-50 hover:text-amber-600"
                    title="Reabrir"
                    @click.stop="emit('reopen', sale.id)"
                  >
                    <RotateCcw class="h-4 w-4" />
                  </button>
                </template>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </BaseTableContainer>

  <PendenciasFiscaisModal
    :is-open="pendenciasModalOpen"
    :pendencias="pendencias"
    titulo="Pendências Fiscais — Venda"
    @close="pendenciasModalOpen = false"
  />
</template>
