<script setup lang="ts">
import { computed, ref, nextTick, toRef } from 'vue';
import { HandCoins, Download, Printer, Lock } from 'lucide-vue-next';

import { formatCurrency, formatCentsToInput } from '@/shared/utils/finance';
import { saveCsv } from '@/shared/utils/csv';
import { imprimirComPagina } from '@/shared/utils/print.utils';
import { useToast } from '@/shared/composables/useToast';
import { useComissaoQuery } from '../composables/useComissaoQuery';
import ComissaoFolhaPrint from './ComissaoFolhaPrint.vue';

const props = defineProps<{ inicio: string; fim: string }>();

const { data } = useComissaoQuery(toRef(props, 'inicio'), toRef(props, 'fim'));
const itens = computed(() => data.value?.itens ?? []);
const totalPagar = computed(() => data.value?.total_comissao ?? 0);
const toast = useToast();

/** Basis points → texto de %. Ex.: 500 → "5%", 550 → "5,5%". */
function pct(bp: number | null): string {
  if (bp == null) return '—';
  return `${(bp / 100).toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%`;
}

function metaTexto(p: number | null): string {
  return p == null ? '—' : `${p.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`;
}

// Impressão A4 (PDF) — usa o mesmo sistema das impressões de OS (window.print).
const mostrarFolha = ref(false);
async function imprimirFolha() {
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

async function exportar() {
  const d = data.value;
  if (!d) return;
  const linhas = d.itens.map((i) => [
    i.nome,
    formatCentsToInput(i.faturamento_vendas),
    i.percentual_venda != null ? String(i.percentual_venda / 100) : '',
    formatCentsToInput(i.faturamento_os),
    i.percentual_servico != null ? String(i.percentual_servico / 100) : '',
    formatCentsToInput(i.comissao_total),
  ]);
  const caminho = await saveCsv(
    `comissao_${d.inicio}_a_${d.fim}.csv`,
    ['Funcionário', 'Vendas (R$)', '% Venda', 'Serviços (R$)', '% Serviço', 'Comissão (R$)'],
    linhas,
  );
  if (caminho) toast.success(`Folha de comissão salva em: ${caminho}`);
}
</script>

<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
    <div class="flex flex-wrap items-center justify-between gap-3 mb-3">
      <h3 class="text-sm font-bold text-slate-700 flex items-center gap-2">
        <HandCoins :size="15" class="text-brand-primary" /> Comissão por funcionário
      </h3>
      <div class="flex items-center gap-4">
        <div class="text-right">
          <span class="text-[10px] uppercase text-slate-400 font-semibold tracking-wide">Total a pagar</span>
          <p class="text-lg font-bold text-brand-primary leading-none tabular-nums">{{ formatCurrency(totalPagar) }}</p>
        </div>
        <button
          v-if="itens.length"
          type="button"
          class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg bg-brand-primary text-white text-xs font-semibold hover:bg-brand-primary/90 transition-colors cursor-pointer"
          @click="imprimirFolha"
        >
          <Printer :size="14" /> Imprimir folha
        </button>
        <button
          v-if="itens.length"
          type="button"
          class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:border-brand-primary hover:text-brand-primary transition-colors cursor-pointer"
          @click="exportar"
        >
          <Download :size="14" /> Exportar CSV
        </button>
      </div>
    </div>

    <!-- Folha imprimível (A4) — só renderiza durante a impressão -->
    <ComissaoFolhaPrint
      v-if="mostrarFolha && data"
      :itens="itens"
      :total-pagar="totalPagar"
      :inicio="inicio"
      :fim="fim"
    />

    <div v-if="itens.length" class="overflow-x-auto">
      <table class="w-full text-sm min-w-150">
        <thead>
          <tr class="text-[11px] uppercase tracking-wide text-slate-400 border-b border-slate-200">
            <th class="py-2 pr-3 font-semibold text-left">Funcionário</th>
            <th class="py-2 px-3 font-semibold text-right">Vendas</th>
            <th class="py-2 px-2 font-semibold text-right">% V</th>
            <th class="py-2 px-3 font-semibold text-right">Serviços</th>
            <th class="py-2 px-2 font-semibold text-right">% S</th>
            <th class="py-2 px-3 font-semibold text-right">Meta</th>
            <th class="py-2 pl-3 font-semibold text-right">Comissão</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="i in itens"
            :key="i.funcionario_id"
            class="border-b border-slate-100 last:border-0"
          >
            <td class="py-2 pr-3 text-slate-700 font-medium">{{ i.nome }}</td>
            <td class="py-2 px-3 text-right text-slate-500 tabular-nums">{{ formatCurrency(i.faturamento_vendas) }}</td>
            <td class="py-2 px-2 text-right text-slate-400 tabular-nums">{{ pct(i.percentual_venda) }}</td>
            <td class="py-2 px-3 text-right text-slate-500 tabular-nums">{{ formatCurrency(i.faturamento_os) }}</td>
            <td class="py-2 px-2 text-right text-slate-400 tabular-nums">{{ pct(i.percentual_servico) }}</td>
            <td class="py-2 px-3 text-right tabular-nums">
              <span
                v-if="!i.comissao_liberada"
                class="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-600"
                title="Modo por meta: comissão travada até bater a meta"
              >
                <Lock :size="10" /> {{ metaTexto(i.meta_atingida_percentual) }}
              </span>
              <span v-else class="text-slate-400">{{ metaTexto(i.meta_atingida_percentual) }}</span>
            </td>
            <td
              class="py-2 pl-3 text-right font-bold tabular-nums"
              :class="i.comissao_liberada ? 'text-brand-primary' : 'text-slate-300'"
            >
              {{ formatCurrency(i.comissao_total) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="py-8 text-center text-xs text-slate-400">
      Nenhuma comissão no período. Configure a % nos <strong>cargos</strong> e atribua vendas/OS aos funcionários.
    </div>
  </div>
</template>
