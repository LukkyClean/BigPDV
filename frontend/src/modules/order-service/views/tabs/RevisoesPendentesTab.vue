<script setup lang="ts">
import { ref, computed } from 'vue';
import {
  CalendarClock, Gauge, Car, Loader2, AlertTriangle,
  Search, History, Plus, MessageCircle,
} from 'lucide-vue-next';

import BaseStatsCard from '@/shared/components/layout/StatsCard/BaseStatsCard.vue';
import { useRevisoesPendentes } from '../../revisoes/composables/useRevisao.queries';
import type { RevisaoPendente } from '../../revisoes/services/revisao.service';
import OSKmHistoryModal from '../../revisoes/components/OSKmHistoryModal.vue';
import { useOSCreateFlow } from '../../ordens/composables/useOSCreateFlow';
import { getCustomerById } from '@/modules/customers/services/customerGet.service';
import { useToast } from '@/shared/composables/useToast';

const { data: revisoes, isLoading } = useRevisoesPendentes(ref(true));
const { handleClienteSelected } = useOSCreateFlow();
const toast = useToast();

// ─── Filtro + busca ─────────────────────────────────────────────────────────
type Filtro = 'todas' | 'data' | 'km';
const filtro = ref<Filtro>('todas');
const busca = ref('');

const filtroOptions: { id: Filtro; label: string }[] = [
  { id: 'todas', label: 'Todas' },
  { id: 'data', label: 'Por data' },
  { id: 'km', label: 'Por KM' },
];

// ─── KPIs ───────────────────────────────────────────────────────────────────
const kpis = computed(() => {
  const lista = revisoes.value ?? [];
  return {
    total: lista.length,
    porData: lista.filter((r) => r.motivo === 'data').length,
    porKm: lista.filter((r) => r.motivo === 'km').length,
  };
});

// ─── Urgência (dias vencidos / km acima do alvo) ────────────────────────────
function diasVencido(r: RevisaoPendente): number {
  if (!r.proxima_revisao_data) return 0;
  const alvo = new Date(r.proxima_revisao_data);
  const hoje = new Date();
  return Math.max(0, Math.floor((hoje.getTime() - alvo.getTime()) / 86_400_000));
}

function kmExcedente(r: RevisaoPendente): number {
  if (r.km_atual == null || r.proxima_revisao_km == null) return 0;
  return Math.max(0, r.km_atual - r.proxima_revisao_km);
}

function urgenciaTexto(r: RevisaoPendente): string {
  if (r.motivo === 'data') {
    const d = diasVencido(r);
    return d <= 0 ? 'Vence hoje' : `Vencida há ${d} ${d === 1 ? 'dia' : 'dias'}`;
  }
  const km = kmExcedente(r);
  return km > 0 ? `${km.toLocaleString('pt-BR')} km acima do alvo` : 'Atingiu o KM alvo';
}

// ─── Lista filtrada e ordenada (mais crítica primeiro) ──────────────────────
const listaFiltrada = computed<RevisaoPendente[]>(() => {
  let lista = [...(revisoes.value ?? [])];

  if (filtro.value !== 'todas') {
    lista = lista.filter((r) => r.motivo === filtro.value);
  }

  const q = busca.value.trim().toLowerCase();
  if (q) {
    lista = lista.filter((r) =>
      `${r.marca} ${r.modelo} ${r.numero_serie} ${r.cliente_nome ?? ''}`
        .toLowerCase()
        .includes(q),
    );
  }

  // Vencidas por data (mais dias) primeiro; depois por KM (mais km acima).
  return lista.sort((a, b) => {
    if (a.motivo !== b.motivo) return a.motivo === 'data' ? -1 : 1;
    return a.motivo === 'data'
      ? diasVencido(b) - diasVencido(a)
      : kmExcedente(b) - kmExcedente(a);
  });
});

// ─── Formatação ─────────────────────────────────────────────────────────────
function formatarData(d: string | null): string {
  return d ? new Date(d).toLocaleDateString('pt-BR') : '—';
}

function formatarKm(km: number | null): string {
  return km != null ? `${km.toLocaleString('pt-BR')} km` : '—';
}

function veiculoLabel(r: RevisaoPendente): string {
  return `${r.marca} ${r.modelo} (${r.numero_serie})`;
}

// ─── Contato (WhatsApp) ─────────────────────────────────────────────────────
function whatsappHref(telefone: string | null): string | null {
  if (!telefone) return null;
  const digitos = telefone.replace(/\D/g, '');
  if (digitos.length < 10) return null;
  const comDDI = digitos.startsWith('55') ? digitos : `55${digitos}`;
  return `https://wa.me/${comDDI}`;
}

// ─── Ações ──────────────────────────────────────────────────────────────────
const isKmModalOpen = ref(false);
const selectedObjetoId = ref<number | null>(null);
const selectedLabel = ref('');

function abrirHistorico(r: RevisaoPendente) {
  selectedObjetoId.value = r.objeto_id;
  selectedLabel.value = veiculoLabel(r);
  isKmModalOpen.value = true;
}

const criandoOSId = ref<number | null>(null);

async function abrirNovaOS(r: RevisaoPendente) {
  // Um veículo não pode ter duas OS em aberto ao mesmo tempo.
  if (r.tem_os_aberta) {
    toast.error('Este veículo já tem uma OS em aberto. Finalize-a antes de abrir outra.');
    return;
  }
  criandoOSId.value = r.objeto_id;
  try {
    const cliente = await getCustomerById(r.cliente_id);
    await handleClienteSelected(cliente);
  } catch {
    toast.error('Não foi possível abrir a Nova OS para este cliente.');
  } finally {
    criandoOSId.value = null;
  }
}
</script>

<template>
  <div class="space-y-6 animate-fadeIn">
    <!-- ─── KPIs ─── -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 md:gap-6">
      <BaseStatsCard :icon="AlertTriangle" label="Total Vencidas" :value="String(kpis.total)" />
      <BaseStatsCard :icon="CalendarClock" label="Vencidas por Data" :value="String(kpis.porData)" />
      <BaseStatsCard :icon="Gauge" label="Vencidas por KM" :value="String(kpis.porKm)" />
    </div>

    <!-- ─── Toolbar: filtros + busca ─── -->
    <div class="flex flex-col sm:flex-row sm:items-center gap-3">
      <div class="flex items-center gap-1 bg-slate-100 p-1 rounded-xl w-fit">
        <button
          v-for="opt in filtroOptions"
          :key="opt.id"
          type="button"
          class="px-3 py-1.5 text-xs font-bold rounded-lg transition-colors"
          :class="filtro === opt.id
            ? 'bg-white text-brand-primary shadow-sm'
            : 'text-slate-500 hover:text-slate-700'"
          @click="filtro = opt.id"
        >
          {{ opt.label }}
        </button>
      </div>

      <div class="relative sm:ml-auto sm:w-72">
        <Search :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          v-model="busca"
          type="text"
          placeholder="Buscar por veículo, placa ou cliente..."
          class="w-full pl-9 pr-3 py-2 text-sm bg-white border border-slate-200 rounded-xl outline-none focus:border-brand-primary/40 focus:ring-2 focus:ring-brand-primary/10 transition"
        />
      </div>
    </div>

    <!-- ─── Loading ─── -->
    <div v-if="isLoading" class="flex items-center justify-center py-16 text-slate-400">
      <Loader2 :size="22" class="animate-spin" />
    </div>

    <!-- ─── Vazio ─── -->
    <div
      v-else-if="listaFiltrada.length === 0"
      class="flex flex-col items-center justify-center py-16 text-slate-400 border-2 border-dashed border-slate-200 rounded-xl bg-slate-50/50"
    >
      <div class="w-14 h-14 bg-slate-100 rounded-full flex items-center justify-center mb-3">
        <CalendarClock :size="28" stroke-width="1.5" class="text-slate-300" />
      </div>
      <p class="text-sm font-semibold text-slate-500">
        {{ busca || filtro !== 'todas' ? 'Nenhum resultado para este filtro' : 'Nenhuma revisão pendente' }}
      </p>
      <p class="text-xs text-slate-400 mt-1">
        {{ busca || filtro !== 'todas'
          ? 'Ajuste a busca ou o filtro acima.'
          : 'Os veículos com revisão agendada aparecerão aqui quando vencerem.' }}
      </p>
    </div>

    <!-- ─── Lista ─── -->
    <div v-else class="space-y-2.5">
      <div
        v-for="r in listaFiltrada"
        :key="r.objeto_id"
        class="flex flex-col lg:flex-row lg:items-center gap-4 p-4 bg-white border border-slate-200 rounded-xl border-l-4 hover:shadow-md hover:shadow-brand-primary/5 transition-all"
        :class="r.motivo === 'data' ? 'border-l-red-400' : 'border-l-amber-400'"
      >
        <!-- Veículo + cliente -->
        <div class="flex items-center gap-3 min-w-0 lg:flex-1">
          <div class="w-11 h-11 rounded-xl flex items-center justify-center shrink-0 bg-brand-primary-light text-brand-primary">
            <Car :size="20" />
          </div>
          <div class="min-w-0">
            <p class="text-sm font-bold text-slate-700 truncate">
              {{ r.marca }} {{ r.modelo }}
              <span class="text-slate-400 font-semibold">· {{ r.numero_serie }}</span>
            </p>
            <p class="text-xs text-slate-500 truncate mt-0.5">
              {{ r.cliente_nome || 'Cliente não informado' }}
              <span v-if="r.cliente_telefone" class="text-slate-400">· {{ r.cliente_telefone }}</span>
            </p>
          </div>
        </div>

        <!-- Urgência -->
        <div class="shrink-0">
          <span
            class="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full"
            :class="r.motivo === 'data' ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-600'"
          >
            <component :is="r.motivo === 'data' ? CalendarClock : Gauge" :size="12" />
            {{ urgenciaTexto(r) }}
          </span>
        </div>

        <!-- Alvo / atual -->
        <div class="flex items-center gap-6 shrink-0 lg:border-l lg:border-slate-100 lg:pl-6">
          <div class="text-right">
            <p class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Data alvo</p>
            <p class="text-sm font-bold text-slate-600">{{ formatarData(r.proxima_revisao_data) }}</p>
          </div>
          <div class="text-right">
            <p class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">KM alvo / atual</p>
            <p class="text-sm font-bold text-slate-600">
              {{ formatarKm(r.proxima_revisao_km) }} <span class="text-slate-300">/</span> {{ formatarKm(r.km_atual) }}
            </p>
          </div>
        </div>

        <!-- Ações — contato é o principal (callback); Nova OS é atalho secundário -->
        <div class="flex items-center gap-2 shrink-0 lg:ml-auto">
          <!-- WhatsApp: ação em destaque -->
          <a
            v-if="whatsappHref(r.cliente_telefone)"
            :href="whatsappHref(r.cliente_telefone) || undefined"
            target="_blank"
            rel="noopener"
            class="inline-flex items-center gap-1.5 h-9 px-3.5 rounded-lg bg-emerald-500 text-white text-xs font-bold hover:bg-emerald-600 shadow-sm shadow-emerald-500/20 transition-colors"
          >
            <MessageCircle :size="16" />
            WhatsApp
          </a>
          <span v-else class="text-[11px] text-slate-400 px-1">sem telefone</span>

          <!-- Histórico de KM -->
          <button
            type="button"
            title="Histórico de KM"
            class="w-9 h-9 flex items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 hover:text-brand-primary transition-colors"
            @click="abrirHistorico(r)"
          >
            <History :size="17" />
          </button>

          <!-- Nova OS: atalho secundário; bloqueado se já há OS em aberto -->
          <button
            type="button"
            :disabled="criandoOSId === r.objeto_id"
            :title="r.tem_os_aberta ? 'Este veículo já tem uma OS em aberto' : 'Abrir nova OS (cliente e veículo já preenchidos)'"
            class="inline-flex items-center gap-1 h-9 px-3 rounded-lg border text-xs font-bold transition-colors disabled:opacity-60"
            :class="r.tem_os_aberta
              ? 'border-amber-200 bg-amber-50 text-amber-600 hover:bg-amber-100'
              : 'border-slate-200 text-slate-600 hover:border-brand-primary hover:text-brand-primary'"
            @click="abrirNovaOS(r)"
          >
            <Loader2 v-if="criandoOSId === r.objeto_id" :size="15" class="animate-spin" />
            <Plus v-else :size="15" />
            Nova OS
          </button>
        </div>
      </div>
    </div>

    <OSKmHistoryModal
      :is-open="isKmModalOpen"
      :objeto-id="selectedObjetoId"
      :veiculo-label="selectedLabel"
      @close="isKmModalOpen = false"
    />
  </div>
</template>

<style scoped>
.animate-fadeIn {
  animation: fadeIn 0.3s ease-in-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
