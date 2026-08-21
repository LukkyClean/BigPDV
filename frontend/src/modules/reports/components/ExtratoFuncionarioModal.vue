<script setup lang="ts">
/**
 * @fileoverview O extrato de serviços de uma pessoa, na tela e no papel.
 *
 * Aberto pelo ícone de cada linha do Ranking. Só o Master chega aqui — o
 * backend responde 403 para os demais, e a seção inteira vive dentro do
 * `v-if="isMaster"` da tela de relatórios.
 */
import { computed, nextTick, ref, toRef } from 'vue';
import { Printer, FileText } from 'lucide-vue-next';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import { formatCurrency } from '@/shared/utils/finance';
import { imprimirComPagina } from '@/shared/utils/print.utils';

import { useExtratoFuncionarioQuery } from '../composables/useExtratoFuncionarioQuery';
import ExtratoFuncionarioPrint from './ExtratoFuncionarioPrint.vue';

const props = defineProps<{
  isOpen: boolean;
  funcionarioId: number | null;
  inicio: string;
  fim: string;
}>();

const emit = defineEmits<{ (e: 'close'): void }>();

const { data, isLoading, isError } = useExtratoFuncionarioQuery(
  toRef(props, 'funcionarioId'),
  toRef(props, 'inicio'),
  toRef(props, 'fim'),
);

const temItens = computed(() => (data.value?.itens.length ?? 0) > 0);

/** "12/08" — o ano já está no cabeçalho do período. */
function diaMes(iso: string): string {
  const [, m, d] = iso.split('-');
  return `${d}/${m}`;
}

function fmtQtd(q: number): string {
  return Number.isInteger(q) ? String(q) : q.toLocaleString('pt-BR', { maximumFractionDigits: 3 });
}

/**
 * Impressão A4 — o mesmo fluxo da folha de comissão, incluindo o fallback.
 *
 * O `afterprint` é quem devolve a tela ao normal, mas ele não dispara em todo
 * cenário (diálogo cancelado de certas formas, impressora virtual). O timeout de
 * 60s existe para a folha não ficar montada para sempre quando isso acontece.
 */
const mostrarFolha = ref(false);
async function imprimir() {
  if (!data.value) return;
  mostrarFolha.value = true;
  await nextTick();
  let fallback: ReturnType<typeof setTimeout>;
  const limpar = () => {
    mostrarFolha.value = false;
    window.removeEventListener('afterprint', limpar);
    clearTimeout(fallback);
  };
  window.addEventListener('afterprint', limpar);
  fallback = setTimeout(limpar, 60000);
  imprimirComPagina('A4');
}
</script>

<template>
  <BaseModal
    :is-open="props.isOpen"
    :title="data?.funcionario_nome ? `Extrato — ${data.funcionario_nome}` : 'Extrato de serviços'"
    subtitle="Serviços executados nas OS finalizadas do período"
    size="2xl"
    @close="emit('close')"
  >
    <ExtratoFuncionarioPrint
      v-if="mostrarFolha && data"
      :funcionario="data.funcionario_nome"
      :itens="data.itens"
      :qtd-os="data.qtd_os"
      :qtd-servicos="data.qtd_servicos"
      :valor-total="data.valor_total"
      :inicio="data.inicio"
      :fim="data.fim"
    />

    <div v-if="isError" class="p-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl">
      Não foi possível carregar o extrato. Tente novamente.
    </div>

    <div v-else-if="isLoading" class="py-10 text-center text-sm text-slate-400">Carregando…</div>

    <template v-else-if="data">
      <div class="flex flex-wrap items-center gap-4 pb-3 mb-3 border-b border-slate-200">
        <div>
          <p class="text-[10px] font-bold uppercase tracking-widest text-slate-400">Serviços</p>
          <p class="text-xl font-bold text-slate-800 tabular-nums">{{ data.qtd_servicos }}</p>
        </div>
        <div>
          <p class="text-[10px] font-bold uppercase tracking-widest text-slate-400">Ordens de serviço</p>
          <p class="text-xl font-bold text-slate-800 tabular-nums">{{ data.qtd_os }}</p>
        </div>
        <div>
          <p class="text-[10px] font-bold uppercase tracking-widest text-slate-400">Total</p>
          <p class="text-xl font-bold text-emerald-700 tabular-nums">{{ formatCurrency(data.valor_total) }}</p>
        </div>

        <button
          type="button"
          :disabled="!temItens"
          class="ml-auto inline-flex items-center gap-1.5 h-9 px-3 rounded-lg bg-brand-primary text-white text-xs font-semibold hover:bg-brand-primary/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          @click="imprimir"
        >
          <Printer :size="14" /> Imprimir extrato
        </button>
      </div>

      <div v-if="!temItens" class="py-10 text-center">
        <FileText :size="28" class="mx-auto text-slate-300" />
        <p class="mt-2 text-sm text-slate-500">Nenhum serviço finalizado neste período.</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-[11px] uppercase tracking-wide text-slate-400 border-b border-slate-200">
              <th class="py-2 pr-3 text-left font-medium">Data</th>
              <th class="py-2 px-3 text-left font-medium">OS</th>
              <th class="py-2 px-3 text-left font-medium">Objeto / Cliente</th>
              <th class="py-2 px-3 text-left font-medium">Serviço</th>
              <th class="py-2 px-3 text-right font-medium">Qtd</th>
              <th class="py-2 pl-3 text-right font-medium">Valor</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(i, idx) in data.itens"
              :key="`${i.numero_os}-${idx}`"
              class="border-b border-slate-100 last:border-0"
            >
              <td class="py-2 pr-3 text-slate-500 tabular-nums">{{ diaMes(i.data_finalizacao) }}</td>
              <td class="py-2 px-3 text-slate-700 font-medium">{{ i.numero_os }}</td>
              <td class="py-2 px-3 text-slate-500">
                <span v-if="i.objeto">{{ i.objeto }}</span>
                <span v-if="i.objeto && i.cliente"> · </span>
                <span v-if="i.cliente">{{ i.cliente }}</span>
                <span v-if="!i.objeto && !i.cliente">—</span>
              </td>
              <td class="py-2 px-3 text-slate-700">{{ i.servico }}</td>
              <td class="py-2 px-3 text-right text-slate-500 tabular-nums">{{ fmtQtd(i.quantidade) }}</td>
              <td class="py-2 pl-3 text-right font-semibold text-slate-800 tabular-nums">
                {{ formatCurrency(i.valor_total) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </BaseModal>
</template>
