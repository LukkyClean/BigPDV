<script setup lang="ts">
import { computed } from 'vue';
import { ListPlus, BadgeDollarSign, Truck, TicketPercent, AlertTriangle } from 'lucide-vue-next';
import { formatCurrency } from '@/shared/utils/finance';
import MoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';
import type { SaleUpdate } from '../../schemas/sale.schema';
import { focarBuscaDeProduto } from '../../focarBusca.util';

const props = defineProps<{
  subtotal?: number;
  discount?: number;
  delivery?: number;
  total?: number;
  form?: SaleUpdate;
  isSaving?: boolean;
  readonly?: boolean;
  descontoDesabilitado?: boolean;
  valorMinimoVenda?: number;
  onSave?: () => void;
}>();

/**
 * Enter em Desconto ou Entrega grava e devolve o foco à busca de produto.
 *
 * Estes dois campos são exceção no ritmo do balcão: chega-se neles por atalho
 * (`Ctrl+D` e `Ctrl+E`), mexe-se uma vez e volta-se a vender. Deixar o cursor
 * parado ali depois do Enter tem o mesmo perigo da quantidade — a próxima
 * bipada digitaria o código de barras inteiro dentro do campo de desconto.
 *
 * O `blur` continua só gravando: sair com o mouse não é dizer "terminei".
 */
function salvarEVoltarParaBusca() {
  props.onSave?.();
  focarBuscaDeProduto();
}

const belowMinimum = computed(() => {
  const min = props.valorMinimoVenda ?? 0;
  return min > 0 && (props.total ?? 0) < min;
});

const hasDiscount = computed(() => {
  if (props.form && props.form.desconto !== undefined) {
    return props.form.desconto > 0;
  }
  return (props.discount ?? 0) > 0;
});

const hasDelivery = computed(() => {
  if (props.form && props.form.entrega !== undefined) {
    return props.form.entrega > 0;
  }
  return (props.delivery ?? 0) > 0;
});
</script>

<template>
  <section class="w-full flex items-center bg-brand-primary/10 border border-brand-primary/20 rounded-lg px-4 py-3 gap-2">
    <!-- Subtotal -->
    <div class="flex-1 flex items-center gap-2 min-w-0">
      <ListPlus :size="15" class="text-brand-action shrink-0" />
      <div class="min-w-0">
        <p class="text-[10px] font-semibold text-zinc-500 uppercase">Subtotal</p>
        <div class="h-9.5 flex items-center">
          <span class="font-bold text-base text-zinc-700 whitespace-nowrap">{{ formatCurrency(subtotal ?? 0) }}</span>
        </div>
      </div>
    </div>

    <div class="w-px h-8 bg-brand-primary/20 shrink-0" />

    <!-- Desconto -->
    <div class="flex-1 flex items-center gap-2 min-w-0">
      <TicketPercent
        :size="15"
        :class="[
          'shrink-0 transition-all duration-300',
          hasDiscount ? 'text-emerald-500 scale-110' : 'text-brand-action'
        ]"
      />
      <div class="min-w-0 flex-1">
        <p
          :class="[
            'text-[10px] font-semibold uppercase transition-colors duration-300',
            hasDiscount ? 'text-emerald-600 font-bold' : 'text-zinc-500'
          ]"
        >
          Desconto
        </p>
        <MoneyInput
          v-if="form && !readonly"
          v-model.number="form.desconto"
          :disabled="isSaving || descontoDesabilitado"
          :variant="hasDiscount ? 'success' : 'default'"
          class="w-full max-w-28 bg-white/80"
          data-sale-desconto
          @blur="onSave"
          @enter="salvarEVoltarParaBusca"
        />
        <div v-else class="h-9.5 flex items-center">
          <span
            :class="[
              'font-bold text-base transition-colors duration-300',
              hasDiscount ? 'text-emerald-600' : 'text-zinc-700'
            ]"
          >
            {{ formatCurrency(discount ?? 0) }}
          </span>
        </div>
      </div>
    </div>

    <div class="w-px h-8 bg-brand-primary/20 shrink-0" />

    <!-- Entrega -->
    <div class="flex-1 flex items-center gap-2 min-w-0">
      <Truck
        :size="15"
        :class="[
          'shrink-0 transition-all duration-300',
          hasDelivery ? 'text-amber-500 scale-110' : 'text-brand-action'
        ]"
      />
      <div class="min-w-0 flex-1">
        <p
          :class="[
            'text-[10px] font-semibold uppercase transition-colors duration-300',
            hasDelivery ? 'text-amber-600 font-bold' : 'text-zinc-500'
          ]"
        >
          Entrega
        </p>
        <MoneyInput
          v-if="form && !readonly"
          v-model.number="form.entrega"
          :disabled="isSaving"
          :variant="hasDelivery ? 'warning' : 'default'"
          class="w-full max-w-28 bg-white/80"
          data-sale-entrega
          @blur="onSave"
          @enter="salvarEVoltarParaBusca"
        />
        <div v-else class="h-9.5 flex items-center">
          <span
            :class="[
              'font-bold text-base transition-colors duration-300',
              hasDelivery ? 'text-amber-600' : 'text-zinc-700'
            ]"
          >
            {{ formatCurrency(delivery ?? 0) }}
          </span>
        </div>
      </div>
    </div>

    <div class="w-px h-8 bg-brand-primary/20 shrink-0" />

    <!-- Total -->
    <div class="flex flex-col items-end gap-1 shrink-0">
      <div class="flex items-center gap-3 bg-brand-primary rounded-lg px-5 py-2.5 text-white shadow-lg shadow-brand-primary/20 transform hover:scale-[1.02] transition-transform">
        <BadgeDollarSign :size="24" class="text-white opacity-80 shrink-0" />
        <div>
          <p class="text-[10px] font-bold text-blue-100 uppercase tracking-widest">Total Final</p>
          <span class="font-black text-2xl whitespace-nowrap tracking-tight">{{ formatCurrency(total ?? 0) }}</span>
        </div>
      </div>
      <div v-if="belowMinimum" class="flex items-center gap-1 text-red-600 bg-red-50 border border-red-200 rounded-md px-2 py-0.5">
        <AlertTriangle :size="11" class="shrink-0" />
        <span class="text-[10px] font-semibold whitespace-nowrap">Mínimo: {{ formatCurrency(valorMinimoVenda ?? 0) }}</span>
      </div>
    </div>
  </section>
</template>
