<script setup lang="ts">
import { computed, toRef } from 'vue';
import { Wrench, Clock, CheckCircle2, Inbox } from 'lucide-vue-next';

import { formatCurrency } from '@/shared/utils/finance';
import { useOSPerformanceQuery } from '../composables/useOSPerformanceQuery';

const props = defineProps<{ inicio: string; fim: string }>();

const { data } = useOSPerformanceQuery(toRef(props, 'inicio'), toRef(props, 'fim'));

const tecnicos = computed(() => data.value?.por_tecnico ?? []);
const porStatus = computed(() => data.value?.por_status ?? []);
const reparo = computed(() => data.value?.reparo);

/** Horas → texto legível (dias quando ≥ 24h). */
function fmtTempo(horas: number | null | undefined): string {
  if (horas == null) return '—';
  if (horas >= 24) return `${(horas / 24).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} d`;
  return `${horas.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} h`;
}

/** ENUM de status → rótulo amigável. */
function statusLabel(s: string): string {
  return s
    .toLowerCase()
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}
</script>

<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-4">
    <h3 class="text-sm font-bold text-slate-700 flex items-center gap-2">
      <Wrench :size="15" class="text-brand-primary" /> Desempenho de OS
    </h3>

    <!-- KPIs -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div class="rounded-lg border border-slate-100 bg-slate-50/60 p-3">
        <span class="text-[10px] uppercase text-slate-400 font-semibold tracking-wide flex items-center gap-1">
          <Inbox :size="11" /> Abertas / Finalizadas
        </span>
        <p class="text-base font-bold text-slate-700 leading-tight tabular-nums">
          {{ data?.abertas ?? 0 }} <span class="text-slate-300">/</span> {{ data?.finalizadas ?? 0 }}
        </p>
      </div>
      <div class="rounded-lg border border-slate-100 bg-slate-50/60 p-3">
        <span class="text-[10px] uppercase text-slate-400 font-semibold tracking-wide flex items-center gap-1">
          <Clock :size="11" /> Tempo médio
        </span>
        <p class="text-base font-bold text-slate-700 leading-tight tabular-nums">{{ fmtTempo(data?.tempo_medio_horas) }}</p>
      </div>
      <div class="rounded-lg border border-emerald-100 bg-emerald-50/60 p-3">
        <span class="text-[10px] uppercase text-emerald-500 font-semibold tracking-wide flex items-center gap-1">
          <CheckCircle2 :size="11" /> Taxa de reparo
        </span>
        <p class="text-base font-bold text-emerald-700 leading-tight tabular-nums">
          {{ (reparo?.taxa_reparo_pct ?? 0).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) }}%
        </p>
      </div>
      <div class="rounded-lg border border-slate-100 bg-slate-50/60 p-3">
        <span class="text-[10px] uppercase text-slate-400 font-semibold tracking-wide">Faturamento de OS</span>
        <p class="text-base font-bold text-slate-700 leading-tight tabular-nums">{{ formatCurrency(data?.faturamento_total ?? 0) }}</p>
      </div>
    </div>

    <!-- Desfecho + backlog -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div class="rounded-lg border border-slate-100 p-3">
        <h4 class="text-xs font-bold text-slate-600 mb-2">Desfecho das finalizadas</h4>
        <div class="flex flex-wrap gap-2 text-xs">
          <span class="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 font-semibold text-emerald-700">
            Reparado: {{ reparo?.reparado ?? 0 }}
          </span>
          <span class="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 font-semibold text-amber-700">
            Sem reparo: {{ reparo?.sem_reparo ?? 0 }}
          </span>
          <span class="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 font-semibold text-red-600">
            Condenado: {{ reparo?.condenado ?? 0 }}
          </span>
          <span v-if="reparo?.nao_informado" class="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 font-semibold text-slate-500">
            Sem registro: {{ reparo.nao_informado }}
          </span>
        </div>
      </div>

      <div class="rounded-lg border border-slate-100 p-3">
        <h4 class="text-xs font-bold text-slate-600 mb-2">Backlog por status (atual)</h4>
        <ul v-if="porStatus.length" class="space-y-1 max-h-40 overflow-y-auto">
          <li v-for="s in porStatus" :key="s.status" class="flex items-center justify-between text-xs">
            <span class="text-slate-600">{{ statusLabel(s.status) }}</span>
            <span class="font-semibold text-slate-700 tabular-nums">{{ s.quantidade }}</span>
          </li>
        </ul>
        <p v-else class="text-xs text-slate-400 py-2">Nenhuma OS no backlog.</p>
      </div>
    </div>

    <!-- Por técnico -->
    <div v-if="tecnicos.length" class="overflow-x-auto">
      <table class="w-full text-sm min-w-120">
        <thead>
          <tr class="text-[11px] uppercase tracking-wide text-slate-400 border-b border-slate-200">
            <th class="py-2 pr-3 font-semibold text-left">Técnico</th>
            <th class="py-2 px-3 font-semibold text-right">Finalizadas</th>
            <th class="py-2 px-3 font-semibold text-right">Tempo médio</th>
            <th class="py-2 pl-3 font-semibold text-right">Faturamento</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in tecnicos" :key="t.funcionario_id" class="border-b border-slate-100 last:border-0">
            <td class="py-2 pr-3 text-slate-700 font-medium">{{ t.nome }}</td>
            <td class="py-2 px-3 text-right text-slate-600 tabular-nums">{{ t.finalizadas }}</td>
            <td class="py-2 px-3 text-right text-slate-500 tabular-nums">{{ fmtTempo(t.tempo_medio_horas) }}</td>
            <td class="py-2 pl-3 text-right font-semibold text-brand-primary tabular-nums">{{ formatCurrency(t.faturamento) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="py-4 text-center text-xs text-slate-400">
      Nenhuma OS finalizada com técnico atribuído no período.
    </div>
  </div>
</template>
