<script setup lang="ts">
import { useOrdemServico } from '@/shared/composables/useOrdemServico';
/**
 * @component ComissaoSection
 * @description Override de comissão POR FUNCIONÁRIO. Todos os campos vazios =
 *   herda do cargo (cascata funcionário -> cargo, resolvida no backend).
 *   Percentuais em BASIS POINTS (500 = 5,00%); meta em centavos.
 */

import { computed } from 'vue';
import { Percent } from 'lucide-vue-next';
import LucideIcon from '@/shared/components/icons/LucideIcon.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseMoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';

import { useEmployeeForm } from '../../composables/useEmployeeForm';

interface Props {
  submitCount: number;
  disabled?: boolean;
}

defineProps<Props>();

const {
  comissao_venda_percentual,
  comissao_servico_percentual,
  meta_mensal,
  comissao_modo,
} = useEmployeeForm();

const { usaOrdemServico } = useOrdemServico();

// Conversão só na exibição: o form guarda basis points e centavos.
function bpParaStr(bp: number | null | undefined): string {
  return bp != null ? String(bp / 100) : '';
}
function strParaBp(v: string): number | null {
  const n = parseFloat(String(v).replace(',', '.'));
  return isNaN(n) ? null : Math.round(n * 100);
}
const comissaoVendaPct = computed<string>({
  get: () => bpParaStr(comissao_venda_percentual.value),
  set: (v) => { comissao_venda_percentual.value = strParaBp(v); },
});
const comissaoServicoPct = computed<string>({
  get: () => bpParaStr(comissao_servico_percentual.value),
  set: (v) => { comissao_servico_percentual.value = strParaBp(v); },
});
const metaReais = computed<number>({
  get: () => (meta_mensal.value != null ? meta_mensal.value / 100 : 0),
  set: (v) => { meta_mensal.value = v ? Math.round(Number(v) * 100) : null; },
});

// Modo: null = herda do cargo (opção "Herdar"); 'direto' e 'meta' sobrescrevem.
const modoAtual = computed<'herda' | 'direto' | 'meta'>(() => {
  if (comissao_modo.value === 'direto') return 'direto';
  if (comissao_modo.value === 'meta') return 'meta';
  return 'herda';
});
function setModo(modo: 'herda' | 'direto' | 'meta') {
  comissao_modo.value = modo === 'herda' ? null : modo;
}

const MODOS: { id: 'herda' | 'direto' | 'meta'; titulo: string; ajuda: string }[] = [
  { id: 'herda', titulo: 'Herdar do cargo', ajuda: 'Usa a regra do cargo' },
  { id: 'direto', titulo: 'Direto', ajuda: 'Paga em toda venda/serviço' },
  { id: 'meta', titulo: 'Só ao bater a meta', ajuda: 'Trava até atingir a meta' },
];
</script>

<template>
  <section>
    <!-- Section Header -->
    <div class="flex items-center gap-3 mb-2">
      <div
        class="w-10 h-10 bg-brand-primary-light rounded-xl flex items-center justify-center text-brand-primary"
      >
        <LucideIcon :icon="Percent" />
      </div>
      <div>
        <h3 class="text-lg font-semibold text-zinc-800">Comissão</h3>
        <p class="text-xs text-zinc-400">Sobrescreve o cargo. Deixe vazio para herdar.</p>
      </div>
    </div>

    <div class="grid grid-cols-12 gap-4 mt-4">
      <div class="col-span-6 md:col-span-3">
        <label class="mb-1 block text-xs font-medium text-zinc-600">% sobre vendas</label>
        <div class="flex items-center gap-1.5">
          <BaseInput v-model="comissaoVendaPct" type="number" placeholder="herda" :disabled="disabled" />
          <span class="text-sm font-medium text-zinc-400">%</span>
        </div>
      </div>
      <!-- Loja sem OS nao tem servico para comissionar: metade do formulario
           seria sobre algo que nao existe ali. O campo continua na tabela; some
           so da tela. -->
      <div v-if="usaOrdemServico" class="col-span-6 md:col-span-3">
        <label class="mb-1 block text-xs font-medium text-zinc-600">% sobre serviços</label>
        <div class="flex items-center gap-1.5">
          <BaseInput v-model="comissaoServicoPct" type="number" placeholder="herda" :disabled="disabled" />
          <span class="text-sm font-medium text-zinc-400">%</span>
        </div>
      </div>
      <div class="col-span-12 md:col-span-6">
        <label class="mb-1 block text-xs font-medium text-zinc-600">Meta mensal</label>
        <BaseMoneyInput v-model="metaReais" :disabled="disabled" />
      </div>

      <!-- Modo -->
      <div class="col-span-12">
        <label class="mb-1.5 block text-xs font-medium text-zinc-600">Quando pagar a comissão</label>
        <div class="grid grid-cols-3 gap-2">
          <button
            v-for="m in MODOS"
            :key="m.id"
            type="button"
            :disabled="disabled"
            class="rounded-xl border px-3 py-2.5 text-left transition disabled:opacity-60"
            :class="modoAtual === m.id
              ? 'border-brand-primary bg-brand-primary-light ring-1 ring-brand-primary'
              : 'border-zinc-200 bg-white hover:border-zinc-300'"
            @click="setModo(m.id)"
          >
            <span class="block text-xs font-semibold text-zinc-800">{{ m.titulo }}</span>
            <span class="mt-0.5 block text-[11px] leading-tight text-zinc-500">{{ m.ajuda }}</span>
          </button>
        </div>
        <p v-if="modoAtual === 'meta' && !meta_mensal" class="mt-1.5 text-[11px] leading-tight text-amber-600">
          Sem meta definida aqui, o gatilho usa a meta herdada do cargo (se houver).
        </p>
      </div>
    </div>
  </section>
</template>
