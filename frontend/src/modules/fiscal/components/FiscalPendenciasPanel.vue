<script setup lang="ts">
import { ref, computed } from 'vue';
import {
  Building2,
  Package,
  Wrench,
  CreditCard,
  ChevronDown,
  ChevronRight,
  CheckCircle,
  AlertTriangle,
} from 'lucide-vue-next';

import { useFiscalPendenciasQuery } from '../composables/useFiscalPendenciasQuery';

const { data: pendencias, isLoading } = useFiscalPendenciasQuery();

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

const totalPendencias = computed(() => {
  if (!pendencias.value) return 0;
  let total = 0;
  if (!pendencias.value.emitente_completo) total += pendencias.value.emitente_pendencias.length;
  total += pendencias.value.produtos_sem_ncm.length;
  total += pendencias.value.servicos_sem_lc116.length;
  total += pendencias.value.pagamentos_sem_sefaz.length;
  return total;
});
</script>

<template>
  <div class="bg-white border border-zinc-200 rounded-2xl md:rounded-3xl shadow-sm flex flex-col h-full">
    <!-- Header -->
    <div class="p-4 md:p-6 border-b border-zinc-100">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-bold text-zinc-800">Pendências</h3>
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
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex-1 p-6">
      <div class="space-y-4 animate-pulse">
        <div v-for="i in 4" :key="i" class="h-10 bg-zinc-100 rounded-lg" />
      </div>
    </div>

    <!-- Sections -->
    <div v-else class="flex-1 overflow-y-auto divide-y divide-zinc-100">
      <!-- Emitente -->
      <div>
        <button
          class="w-full flex items-center gap-3 px-4 py-3 md:px-6 hover:bg-zinc-50 transition-colors text-left"
          @click="toggle('emitente')"
        >
          <Building2 :size="16" class="text-zinc-400 shrink-0" />
          <span class="flex-1 text-sm font-medium text-zinc-700">Emitente</span>
          <CheckCircle
            v-if="pendencias?.emitente_completo"
            :size="14"
            class="text-green-500 shrink-0"
          />
          <AlertTriangle
            v-else
            :size="14"
            class="text-amber-500 shrink-0"
          />
          <component
            :is="isExpandido('emitente') ? ChevronDown : ChevronRight"
            :size="14"
            class="text-zinc-400 shrink-0"
          />
        </button>
        <div v-if="isExpandido('emitente')" class="px-4 pb-3 md:px-6">
          <p
            v-if="pendencias?.emitente_completo"
            class="text-xs text-green-600 pl-7"
          >
            Dados do emitente completos.
          </p>
          <ul v-else class="space-y-1 pl-7">
            <li
              v-for="p in pendencias?.emitente_pendencias"
              :key="p"
              class="text-xs text-zinc-500 flex items-start gap-1.5"
            >
              <span class="w-1 h-1 rounded-full bg-amber-400 mt-1.5 shrink-0" />
              {{ p }}
            </li>
          </ul>
        </div>
      </div>

      <!-- Produtos sem NCM -->
      <div>
        <button
          class="w-full flex items-center gap-3 px-4 py-3 md:px-6 hover:bg-zinc-50 transition-colors text-left"
          @click="toggle('produtos')"
        >
          <Package :size="16" class="text-zinc-400 shrink-0" />
          <span class="flex-1 text-sm font-medium text-zinc-700">Produtos sem NCM</span>
          <span
            :class="[
              'text-xs font-semibold px-1.5 py-0.5 rounded-full',
              (pendencias?.produtos_sem_ncm?.length ?? 0) > 0
                ? 'bg-amber-100 text-amber-700'
                : 'bg-green-100 text-green-700',
            ]"
          >
            {{ pendencias?.produtos_sem_ncm?.length ?? 0 }}
          </span>
          <component
            :is="isExpandido('produtos') ? ChevronDown : ChevronRight"
            :size="14"
            class="text-zinc-400 shrink-0"
          />
        </button>
        <div v-if="isExpandido('produtos')" class="px-4 pb-3 md:px-6">
          <p
            v-if="!pendencias?.produtos_sem_ncm?.length"
            class="text-xs text-green-600 pl-7"
          >
            Todos os produtos possuem NCM.
          </p>
          <ul v-else class="space-y-1 pl-7 max-h-40 overflow-y-auto">
            <li
              v-for="item in pendencias!.produtos_sem_ncm"
              :key="item.id"
              class="text-xs text-zinc-500 flex items-start gap-1.5"
            >
              <span class="w-1 h-1 rounded-full bg-amber-400 mt-1.5 shrink-0" />
              {{ item.nome }}
            </li>
          </ul>
        </div>
      </div>

      <!-- Serviços sem LC116 -->
      <div>
        <button
          class="w-full flex items-center gap-3 px-4 py-3 md:px-6 hover:bg-zinc-50 transition-colors text-left"
          @click="toggle('servicos')"
        >
          <Wrench :size="16" class="text-zinc-400 shrink-0" />
          <span class="flex-1 text-sm font-medium text-zinc-700">Serviços sem LC116</span>
          <span
            :class="[
              'text-xs font-semibold px-1.5 py-0.5 rounded-full',
              (pendencias?.servicos_sem_lc116?.length ?? 0) > 0
                ? 'bg-amber-100 text-amber-700'
                : 'bg-green-100 text-green-700',
            ]"
          >
            {{ pendencias?.servicos_sem_lc116?.length ?? 0 }}
          </span>
          <component
            :is="isExpandido('servicos') ? ChevronDown : ChevronRight"
            :size="14"
            class="text-zinc-400 shrink-0"
          />
        </button>
        <div v-if="isExpandido('servicos')" class="px-4 pb-3 md:px-6">
          <p
            v-if="!pendencias?.servicos_sem_lc116?.length"
            class="text-xs text-green-600 pl-7"
          >
            Todos os serviços possuem código LC116.
          </p>
          <ul v-else class="space-y-1 pl-7 max-h-40 overflow-y-auto">
            <li
              v-for="item in pendencias!.servicos_sem_lc116"
              :key="item.id"
              class="text-xs text-zinc-500 flex items-start gap-1.5"
            >
              <span class="w-1 h-1 rounded-full bg-amber-400 mt-1.5 shrink-0" />
              {{ item.nome }}
            </li>
          </ul>
        </div>
      </div>

      <!-- Pagamentos sem código SEFAZ -->
      <div>
        <button
          class="w-full flex items-center gap-3 px-4 py-3 md:px-6 hover:bg-zinc-50 transition-colors text-left"
          @click="toggle('pagamentos')"
        >
          <CreditCard :size="16" class="text-zinc-400 shrink-0" />
          <span class="flex-1 text-sm font-medium text-zinc-700">Pagamentos sem SEFAZ</span>
          <span
            :class="[
              'text-xs font-semibold px-1.5 py-0.5 rounded-full',
              (pendencias?.pagamentos_sem_sefaz?.length ?? 0) > 0
                ? 'bg-amber-100 text-amber-700'
                : 'bg-green-100 text-green-700',
            ]"
          >
            {{ pendencias?.pagamentos_sem_sefaz?.length ?? 0 }}
          </span>
          <component
            :is="isExpandido('pagamentos') ? ChevronDown : ChevronRight"
            :size="14"
            class="text-zinc-400 shrink-0"
          />
        </button>
        <div v-if="isExpandido('pagamentos')" class="px-4 pb-3 md:px-6">
          <p
            v-if="!pendencias?.pagamentos_sem_sefaz?.length"
            class="text-xs text-green-600 pl-7"
          >
            Todas as formas de pagamento possuem código SEFAZ.
          </p>
          <ul v-else class="space-y-1 pl-7 max-h-40 overflow-y-auto">
            <li
              v-for="item in pendencias!.pagamentos_sem_sefaz"
              :key="item.id"
              class="text-xs text-zinc-500 flex items-start gap-1.5"
            >
              <span class="w-1 h-1 rounded-full bg-amber-400 mt-1.5 shrink-0" />
              {{ item.nome }}
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>
