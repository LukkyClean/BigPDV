<script setup lang="ts">
import { ref, computed, type ComputedRef } from 'vue';
import { useRouter } from 'vue-router';
import {
  Building2,
  Package,
  Wrench,
  CreditCard,
  ChevronDown,
  ChevronRight,
  CheckCircle,
  AlertOctagon,
  ExternalLink,
  ShieldCheck,
  Sparkles,
} from 'lucide-vue-next';

import { useFiscalPendenciasQuery } from '../../composables/useFiscalPendenciasQuery';

const router = useRouter();
const { data: pendencias, isLoading } = useFiscalPendenciasQuery();

const emit = defineEmits<{
  (e: 'abrir-resolucao'): void;
}>();

const expandidos = ref<Set<string>>(new Set(['emitente']));

function toggle(secao: string) {
  if (expandidos.value.has(secao)) {
    expandidos.value.delete(secao);
  } else {
    expandidos.value.add(secao);
  }
}

function isExpandido(secao: string) {
  return expandidos.value.has(secao);
}

// --- Contadores ---
const emitenteCount = computed(() => {
  if (!pendencias.value || pendencias.value.emitente_completo) return 0;
  return pendencias.value.emitente_pendencias.length;
});

const produtosCount = computed(() => pendencias.value?.produtos_sem_ncm?.length ?? 0);
const servicosCount = computed(() => pendencias.value?.servicos_sem_lc116?.length ?? 0);
const pagamentosCount = computed(() => pendencias.value?.pagamentos_sem_sefaz?.length ?? 0);

const totalPendencias = computed(() =>
  emitenteCount.value + produtosCount.value + servicosCount.value + pagamentosCount.value,
);

// --- Barra de Saúde (Recomendação 3) ---
const totalChecks = computed(() => {
  if (!pendencias.value) return 1;
  // Total = 1 (emitente) + qtd_produtos + qtd_servicos + qtd_pagamentos
  // Para simplificar, usamos as 4 seções como base
  return 4;
});

const resolvedChecks = computed(() => {
  if (!pendencias.value) return 0;
  let resolved = 0;
  if (pendencias.value.emitente_completo) resolved++;
  if (produtosCount.value === 0) resolved++;
  if (servicosCount.value === 0) resolved++;
  if (pagamentosCount.value === 0) resolved++;
  return resolved;
});

const healthPercent = computed(() =>
  Math.round((resolvedChecks.value / totalChecks.value) * 100),
);

const healthColor = computed(() => {
  if (healthPercent.value === 100) return 'bg-emerald-500';
  if (healthPercent.value >= 75) return 'bg-emerald-400';
  if (healthPercent.value >= 50) return 'bg-amber-400';
  return 'bg-red-500';
});

const healthTextColor = computed(() => {
  if (healthPercent.value === 100) return 'text-emerald-600';
  if (healthPercent.value >= 50) return 'text-amber-600';
  return 'text-red-600';
});

// --- Deep Linking (Recomendação 1) ---
function navegarEmpresa() {
  router.push({ name: 'enterprise' });
}

function navegarServico(_servicoId: number) {
  router.push({ name: 'services' });
}

function navegarPagamentos() {
  // Formas de pagamento geralmente ficam nas configurações ou na área do emitente
  router.push({ name: 'enterprise' });
}

// --- Seções configuradas (Recomendação 5 — gravidade) ---
interface Secao {
  key: string;
  label: string;
  icon: any;
  gravidade: 'critica' | 'alerta';
  gravidadeLabel: string;
  count: ComputedRef<number>;
  isOk: ComputedRef<boolean>;
}

const secoes = computed<Secao[]>(() => [
  {
    key: 'emitente',
    label: 'Dados do Emitente',
    icon: Building2,
    gravidade: 'critica',
    gravidadeLabel: 'Blocante',
    count: emitenteCount,
    isOk: computed(() => pendencias.value?.emitente_completo ?? false),
  },
  {
    key: 'produtos',
    label: 'Produto com Cadastro Incompleto',
    icon: Package,
    gravidade: 'alerta',
    gravidadeLabel: 'Atenção',
    count: produtosCount,
    isOk: computed(() => produtosCount.value === 0),
  },
  {
    key: 'servicos',
    label: 'Serviço com Cadastro Incompleto',
    icon: Wrench,
    gravidade: 'alerta',
    gravidadeLabel: 'Atenção',
    count: servicosCount,
    isOk: computed(() => servicosCount.value === 0),
  },
  {
    key: 'pagamentos',
    label: 'Pagamentos sem SEFAZ',
    icon: CreditCard,
    gravidade: 'alerta',
    gravidadeLabel: 'Atenção',
    count: pagamentosCount,
    isOk: computed(() => pagamentosCount.value === 0),
  },
]);
</script>

<template>
  <div class="bg-white border border-zinc-200 rounded-2xl md:rounded-3xl shadow-sm flex flex-col h-full">
    <!-- Header -->
    <div class="p-4 md:p-6 border-b border-zinc-100">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-bold text-zinc-800">Saúde Fiscal</h3>
        <span
          v-if="!isLoading"
          :class="[
            'text-xs font-semibold px-2 py-0.5 rounded-full',
            totalPendencias > 0
              ? 'bg-amber-100 text-amber-700'
              : 'bg-green-100 text-green-700',
          ]"
        >
          {{ totalPendencias > 0 ? `${totalPendencias} pendência${totalPendencias > 1 ? 's' : ''}` : 'Tudo certo' }}
        </span>
      </div>
      <p class="text-xs text-zinc-400 mt-1">Itens que impedem a emissão fiscal.</p>

      <!-- Barra de progresso (Recomendação 3) -->
      <div v-if="!isLoading" class="mt-3">
        <div class="flex items-center justify-between mb-1">
          <span class="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Configuração</span>
          <span :class="['text-xs font-bold tabular-nums', healthTextColor]">{{ healthPercent }}%</span>
        </div>
        <div class="h-2 w-full rounded-full bg-zinc-100 overflow-hidden">
          <div
            :class="['h-full rounded-full transition-all duration-700 ease-out', healthColor]"
            :style="{ width: healthPercent + '%' }"
          />
        </div>
        <p class="text-[10px] text-zinc-400 mt-1">
          {{ resolvedChecks }} de {{ totalChecks }} categorias resolvidas
        </p>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex-1 p-6">
      <div class="space-y-4 animate-pulse">
        <div v-for="i in 4" :key="i" class="h-10 bg-zinc-100 rounded-lg" />
      </div>
    </div>

    <!-- Empty State Comemorativo (Recomendação 4) -->
    <div
      v-else-if="totalPendencias === 0"
      class="flex-1 flex flex-col items-center justify-center px-6 py-10 text-center"
    >
      <div class="relative mb-4">
        <div class="w-16 h-16 rounded-2xl bg-emerald-50 flex items-center justify-center">
          <ShieldCheck class="w-8 h-8 text-emerald-500" />
        </div>
        <div class="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-amber-50 flex items-center justify-center">
          <Sparkles class="w-3.5 h-3.5 text-amber-500" />
        </div>
      </div>
      <h4 class="text-sm font-bold text-zinc-800">Tudo pronto!</h4>
      <p class="text-xs text-zinc-400 mt-1 max-w-[200px] leading-relaxed">
        Seu sistema está com a saúde fiscal em dia. Todas as categorias foram configuradas corretamente.
      </p>
    </div>

    <!-- Seções com pendências -->
    <div v-else class="flex-1 overflow-y-auto divide-y divide-zinc-100">
      <div v-for="secao in secoes" :key="secao.key">
        <button
          class="w-full flex items-center gap-3 px-4 py-3 md:px-6 hover:bg-zinc-50 transition-colors text-left"
          @click="toggle(secao.key)"
        >
          <component :is="secao.icon" :size="16" class="text-zinc-400 shrink-0" />
          <span class="flex-1 text-sm font-medium text-zinc-700">{{ secao.label }}</span>

          <!-- Badge de gravidade (Recomendação 5) -->
          <template v-if="!secao.isOk.value">
            <span
              :class="[
                'text-[10px] font-bold px-1.5 py-0.5 rounded-full uppercase tracking-wide',
                secao.gravidade === 'critica'
                  ? 'bg-red-100 text-red-600'
                  : 'bg-amber-100 text-amber-600',
              ]"
            >
              {{ secao.gravidadeLabel }}
            </span>
            <span
              :class="[
                'text-xs font-semibold px-1.5 py-0.5 rounded-full min-w-[24px] text-center',
                secao.gravidade === 'critica'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-amber-100 text-amber-700',
              ]"
            >
              {{ secao.count.value }}
            </span>
          </template>
          <CheckCircle v-else :size="14" class="text-green-500 shrink-0" />

          <component
            :is="isExpandido(secao.key) ? ChevronDown : ChevronRight"
            :size="14"
            class="text-zinc-400 shrink-0"
          />
        </button>

        <!-- Conteúdo expandido -->
        <div v-if="isExpandido(secao.key)" class="px-4 pb-3 md:px-6">
          <!-- OK -->
          <p v-if="secao.isOk.value" class="text-xs text-green-600 pl-7 flex items-center gap-1.5">
            <CheckCircle :size="12" />
            {{
              secao.key === 'emitente' ? 'Dados do emitente completos.' :
              secao.key === 'produtos' ? 'Cadastros de produtos estão completos.' :
              secao.key === 'servicos' ? 'Cadastros de serviços estão completos.' :
              'Todas as formas de pagamento possuem código SEFAZ.'
            }}
          </p>

          <!-- Emitente pendências -->
          <template v-else-if="secao.key === 'emitente'">
            <!-- Banner crítico (Recomendação 5) -->
            <div class="mb-2 ml-7 flex items-start gap-2 rounded-lg bg-red-50 border border-red-100 p-2.5">
              <AlertOctagon :size="14" class="text-red-500 mt-0.5 shrink-0" />
              <p class="text-[11px] text-red-700 leading-relaxed">
                <strong>Crítico:</strong> Sem estes dados, nenhuma nota fiscal poderá ser emitida.
              </p>
            </div>
            <ul class="space-y-1.5 pl-7">
              <li
                v-for="p in pendencias?.emitente_pendencias"
                :key="p"
                class="text-xs text-zinc-600 flex items-center gap-1.5"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-red-400 shrink-0" />
                {{ p }}
              </li>
            </ul>
            <!-- Link para resolver (Recomendação 1) -->
            <button
              @click="navegarEmpresa"
              class="mt-2.5 ml-7 inline-flex items-center gap-1.5 text-xs font-semibold text-brand-primary hover:underline cursor-pointer"
            >
              <ExternalLink :size="12" />
              Ir para Dados da Empresa
            </button>
          </template>

          <!-- Produtos sem NCM -->
          <template v-else-if="secao.key === 'produtos'">
            <ul class="space-y-1 pl-7 max-h-40 overflow-y-auto">
              <li
                v-for="item in pendencias?.produtos_sem_ncm ?? []"
                :key="item.id"
                class="text-xs text-zinc-600 flex items-center justify-between gap-2 group/item py-0.5"
              >
                <span class="flex items-center gap-1.5 min-w-0">
                  <span class="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                  <span class="truncate">{{ item.nome }}</span>
                </span>
              </li>
            </ul>
            <button
              @click.stop="emit('abrir-resolucao')"
              class="mt-2.5 ml-7 inline-flex items-center gap-1.5 text-xs font-semibold text-brand-primary hover:underline cursor-pointer"
            >
              <ExternalLink :size="12" />
              Resolver aqui
            </button>
          </template>

          <!-- Serviços sem LC116 -->
          <template v-else-if="secao.key === 'servicos'">
            <ul class="space-y-1 pl-7 max-h-40 overflow-y-auto">
              <li
                v-for="item in pendencias?.servicos_sem_lc116 ?? []"
                :key="item.id"
                class="text-xs text-zinc-600 flex items-center justify-between gap-2 group/item py-0.5"
              >
                <span class="flex items-center gap-1.5 min-w-0">
                  <span class="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                  <span class="truncate">{{ item.nome }}</span>
                </span>
                <button
                  @click.stop="navegarServico(item.id)"
                  class="opacity-0 group-hover/item:opacity-100 shrink-0 text-brand-primary hover:underline flex items-center gap-0.5 transition-opacity"
                >
                  <ExternalLink :size="10" />
                  <span class="text-[10px] font-semibold">Editar</span>
                </button>
              </li>
            </ul>
          </template>

          <!-- Pagamentos sem SEFAZ -->
          <template v-else-if="secao.key === 'pagamentos'">
            <ul class="space-y-1 pl-7 max-h-40 overflow-y-auto">
              <li
                v-for="item in pendencias?.pagamentos_sem_sefaz ?? []"
                :key="item.id"
                class="text-xs text-zinc-600 flex items-center gap-1.5 py-0.5"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                <span class="truncate">{{ item.nome }}</span>
              </li>
            </ul>
            <button
              @click="navegarPagamentos"
              class="mt-2.5 ml-7 inline-flex items-center gap-1.5 text-xs font-semibold text-brand-primary hover:underline cursor-pointer"
            >
              <ExternalLink :size="12" />
              Ir para Configurações
            </button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
