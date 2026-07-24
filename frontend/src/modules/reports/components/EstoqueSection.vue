<script setup lang="ts">
import { computed, toRef } from 'vue';
import { Boxes, Download, TriangleAlert, PackageX } from 'lucide-vue-next';

import { formatCurrency, formatCentsToInput } from '@/shared/utils/finance';
import { saveCsv } from '@/shared/utils/csv';
import { useToast } from '@/shared/composables/useToast';
import { useEstoqueQuery } from '../composables/useEstoqueQuery';

const props = defineProps<{ inicio: string; fim: string }>();

const { data } = useEstoqueQuery(toRef(props, 'inicio'), toRef(props, 'fim'));
const toast = useToast();

const abc = computed(() => data.value?.curva_abc ?? []);
const abaixo = computed(() => data.value?.abaixo_minimo ?? []);
const parados = computed(() => data.value?.parados ?? []);

// Selo de classe ABC.
const CLASSE_COR: Record<string, string> = {
  A: 'bg-emerald-50 text-emerald-700',
  B: 'bg-amber-50 text-amber-700',
  C: 'bg-slate-100 text-slate-500',
};

function pct(v: number): string {
  return `${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`;
}

async function exportarAbc() {
  const d = data.value;
  if (!d) return;
  const linhas = d.curva_abc.map((i) => [
    i.classe,
    i.nome,
    i.sku ?? '',
    String(i.quantidade),
    formatCentsToInput(i.faturamento),
    String(i.participacao_pct),
    String(i.acumulado_pct),
  ]);
  const caminho = await saveCsv(
    `curva_abc_${d.inicio}_a_${d.fim}.csv`,
    ['Classe', 'Produto', 'SKU', 'Qtd vendida', 'Faturamento (R$)', '% Part.', '% Acum.'],
    linhas,
  );
  if (caminho) toast.success(`Curva ABC salva em: ${caminho}`);
}
</script>

<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h3 class="text-sm font-bold text-slate-700 flex items-center gap-2">
        <Boxes :size="15" class="text-brand-primary" /> Estoque e Curva ABC
      </h3>
      <button
        v-if="abc.length"
        type="button"
        class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:border-brand-primary hover:text-brand-primary transition-colors cursor-pointer"
        @click="exportarAbc"
      >
        <Download :size="14" /> Exportar ABC
      </button>
    </div>

    <!-- KPIs -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div class="rounded-lg border border-slate-100 bg-slate-50/60 p-3">
        <span class="text-[10px] uppercase text-slate-400 font-semibold tracking-wide">Valor em estoque (custo)</span>
        <p class="text-base font-bold text-slate-700 leading-tight tabular-nums">{{ formatCurrency(data?.valor_custo_total ?? 0) }}</p>
        <span class="text-[11px] text-slate-400">a preço de venda: {{ formatCurrency(data?.valor_venda_total ?? 0) }}</span>
      </div>
      <div class="rounded-lg border border-slate-100 bg-slate-50/60 p-3">
        <span class="text-[10px] uppercase text-slate-400 font-semibold tracking-wide">SKUs ativos</span>
        <p class="text-base font-bold text-slate-700 leading-tight tabular-nums">{{ data?.skus_ativos ?? 0 }}</p>
      </div>
      <div class="rounded-lg border border-amber-100 bg-amber-50/60 p-3">
        <span class="text-[10px] uppercase text-amber-500 font-semibold tracking-wide">Abaixo do mínimo</span>
        <p class="text-base font-bold text-amber-700 leading-tight tabular-nums">{{ data?.itens_abaixo_minimo ?? 0 }}</p>
      </div>
      <div class="rounded-lg border border-slate-100 bg-slate-50/60 p-3">
        <span class="text-[10px] uppercase text-slate-400 font-semibold tracking-wide">Parados no período</span>
        <p class="text-base font-bold text-slate-700 leading-tight tabular-nums">{{ data?.itens_parados ?? 0 }}</p>
      </div>
    </div>

    <!-- Curva ABC -->
    <div v-if="abc.length" class="overflow-x-auto">
      <table class="w-full text-sm min-w-150">
        <thead>
          <tr class="text-[11px] uppercase tracking-wide text-slate-400 border-b border-slate-200">
            <th class="py-2 pr-2 font-semibold text-center w-12">Classe</th>
            <th class="py-2 px-3 font-semibold text-left">Produto</th>
            <th class="py-2 px-2 font-semibold text-right">Qtd</th>
            <th class="py-2 px-3 font-semibold text-right">Faturamento</th>
            <th class="py-2 px-2 font-semibold text-right">% Part.</th>
            <th class="py-2 pl-2 font-semibold text-right">% Acum.</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="i in abc" :key="i.produto_id" class="border-b border-slate-100 last:border-0">
            <td class="py-2 pr-2 text-center">
              <span class="inline-block w-6 rounded-full text-[11px] font-bold py-0.5" :class="CLASSE_COR[i.classe]">{{ i.classe }}</span>
            </td>
            <td class="py-2 px-3 text-slate-700 font-medium">
              {{ i.nome }}
              <span v-if="i.sku" class="text-[11px] text-slate-400">· {{ i.sku }}</span>
            </td>
            <td class="py-2 px-2 text-right text-slate-500 tabular-nums">{{ i.quantidade }}</td>
            <td class="py-2 px-3 text-right text-slate-600 tabular-nums">{{ formatCurrency(i.faturamento) }}</td>
            <td class="py-2 px-2 text-right text-slate-400 tabular-nums">{{ pct(i.participacao_pct) }}</td>
            <td class="py-2 pl-2 text-right text-slate-400 tabular-nums">{{ pct(i.acumulado_pct) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="py-6 text-center text-xs text-slate-400">
      Nenhuma venda de produto cadastrado no período para montar a Curva ABC.
    </div>

    <!-- Reposição e Parados -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div class="rounded-lg border border-slate-100 p-3">
        <h4 class="text-xs font-bold text-slate-600 flex items-center gap-1.5 mb-2">
          <TriangleAlert :size="13" class="text-amber-500" /> Reposição (abaixo do mínimo)
        </h4>
        <ul v-if="abaixo.length" class="space-y-1 max-h-56 overflow-y-auto">
          <li v-for="p in abaixo" :key="p.produto_id" class="flex items-center justify-between text-xs">
            <span class="text-slate-600 truncate pr-2">{{ p.nome }}</span>
            <span class="tabular-nums shrink-0">
              <span class="font-semibold text-amber-600">{{ p.quantidade }}</span>
              <span class="text-slate-400"> / mín {{ p.quantidade_minima ?? '—' }}</span>
            </span>
          </li>
        </ul>
        <p v-else class="text-xs text-slate-400 py-2">Nenhum produto abaixo do mínimo. 👍</p>
      </div>

      <div class="rounded-lg border border-slate-100 p-3">
        <h4 class="text-xs font-bold text-slate-600 flex items-center gap-1.5 mb-2">
          <PackageX :size="13" class="text-slate-400" /> Parados (sem venda no período)
        </h4>
        <ul v-if="parados.length" class="space-y-1 max-h-56 overflow-y-auto">
          <li v-for="p in parados" :key="p.produto_id" class="flex items-center justify-between text-xs">
            <span class="text-slate-600 truncate pr-2">{{ p.nome }}</span>
            <span class="tabular-nums shrink-0">
              <span class="text-slate-500">{{ p.quantidade }} un</span>
              <span class="text-slate-400"> · {{ formatCurrency(p.valor_custo) }}</span>
            </span>
          </li>
        </ul>
        <p v-else class="text-xs text-slate-400 py-2">Todos os produtos com estoque venderam no período.</p>
      </div>
    </div>
  </div>
</template>
