<script setup lang="ts">
import type { Component } from 'vue';
import { computed } from 'vue';

/**
 * Card de indicador — o bloco de número que abre as telas do sistema.
 *
 * Duas capacidades foram acrescentadas quando a Gestão Financeira passou a
 * usá-lo, e as duas faltavam num componente cujo trabalho é mostrar VALOR:
 *
 * 1. `tabular-nums` no número. Sem isso os dígitos têm larguras diferentes e
 *    uma coluna de valores dança a cada atualização. O resto do sistema já
 *    fazia isso à mão onde havia dinheiro (caixa, pagamento de OS); aqui era o
 *    único lugar que não fazia.
 *
 * 2. `tone`, para o card que precisa GRITAR. Uma conta vencida não é um número
 *    a mais: é o número que o dono tem de ver primeiro. O padrão é `neutro`, e
 *    é idêntico ao que o card sempre foi — nenhuma das telas que já o usavam
 *    muda de aparência.
 */

type Tom = 'neutro' | 'perigo' | 'alerta' | 'sucesso';

interface Props {
  icon: Component;
  label: string;
  value: string;
  /**
   * Estado que a cor deve comunicar. Use com parcimônia: se tudo é vermelho,
   * nada é. `perigo` é para o que já deu errado (vencido), `alerta` para o que
   * vai dar (vence hoje), `sucesso` para o que fechou bem.
   */
  tone?: Tom;
}

const props = withDefaults(defineProps<Props>(), { tone: 'neutro' });

const TONS: Record<Tom, { card: string; icone: string; rotulo: string; valor: string }> = {
  neutro: {
    card: 'bg-white border-zinc-200 hover:border-brand-secondary hover:shadow-brand-primary/10',
    icone: 'bg-zinc-50 border-zinc-100 group-hover:bg-brand-primary/5 group-hover:border-brand-primary/20',
    rotulo: 'text-zinc-500',
    valor: 'text-zinc-900',
  },
  perigo: {
    card: 'bg-rose-50 border-rose-200 hover:border-rose-300 hover:shadow-rose-500/10',
    icone: 'bg-rose-100 border-rose-200',
    rotulo: 'text-rose-600',
    valor: 'text-rose-700',
  },
  alerta: {
    card: 'bg-amber-50 border-amber-200 hover:border-amber-300 hover:shadow-amber-500/10',
    icone: 'bg-amber-100 border-amber-200',
    rotulo: 'text-amber-700',
    valor: 'text-amber-800',
  },
  sucesso: {
    card: 'bg-emerald-50 border-emerald-200 hover:border-emerald-300 hover:shadow-emerald-500/10',
    icone: 'bg-emerald-100 border-emerald-200',
    rotulo: 'text-emerald-700',
    valor: 'text-emerald-800',
  },
};

const tom = computed(() => TONS[props.tone]);
</script>

<template>
  <div
    class="p-5 md:p-6 rounded-2xl md:rounded-3xl border shadow-sm hover:shadow-md transition-all duration-300 hover:-translate-y-0.5 group"
    :class="tom.card"
  >
    <!-- Header: Icon + Change Badge -->
    <div class="flex items-center justify-between mb-4">
      <div
        class="w-10 h-10 md:w-12 md:h-12 rounded-xl md:rounded-2xl flex items-center justify-center border transition-colors"
        :class="tom.icone"
      >
        <component :is="icon" :size="20" class="md:w-6 md:h-6" :class="tom.valor" />
      </div>
      <slot name="badge" />
    </div>

    <!-- Label -->
    <p
      class="text-[10px] md:text-xs font-semibold mb-1 uppercase tracking-wider"
      :class="tom.rotulo"
    >
      {{ label }}
    </p>

    <!-- Value -->
    <p class="text-xl md:text-2xl font-black tracking-tight tabular-nums" :class="tom.valor">
      {{ value }}
    </p>
  </div>
</template>
