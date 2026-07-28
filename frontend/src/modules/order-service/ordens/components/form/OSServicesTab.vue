<script setup lang="ts">
import { Plus, Trash2, Package, Wrench, ShoppingBag, Pencil } from 'lucide-vue-next';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { formatCurrency } from '@/shared/utils/finance';
import type { OsItemCreateSchemaDataType, OsItemReadSchemaDataType } from '../../schemas/relationship/osItem.schema';
import { useCapacidades } from '@/modules/order-service/shared/segmento/useCapacidades';

type OsItem = OsItemCreateSchemaDataType | OsItemReadSchemaDataType;

const { temAprovacaoItens, temGarantiaItens } = useCapacidades();

const STATUS_BADGE: Record<string, { label: string; cls: string }> = {
  APROVADO: { label: 'Aprovado', cls: 'bg-emerald-50 text-emerald-600' },
  PENDENTE: { label: 'Pendente', cls: 'bg-amber-50 text-amber-600' },
  REPROVADO: { label: 'Reprovado', cls: 'bg-red-50 text-red-600' },
};

function statusBadge(item: OsItem) {
  return STATUS_BADGE[item.status_aprovacao ?? 'APROVADO'] ?? STATUS_BADGE.APROVADO;
}

function garantiaLabel(item: OsItem): string {
  const partes: string[] = [];
  if (item.garantia_dias) partes.push(`${item.garantia_dias} dias`);
  if (item.garantia_km) partes.push(`${item.garantia_km.toLocaleString('pt-BR')} km`);
  return partes.join(' / ');
}

interface Props {
  itens: OsItem[];
  isLocked?: boolean;
}

withDefaults(defineProps<Props>(), {
  isLocked: false,
});

const emit = defineEmits<{
  addItem: [];
  editItem: [index: number];
  removeItem: [index: number];
}>();

function getItemIcon(item: OsItem) {
  return item.tipo === 'SERVICO' ? Wrench : ShoppingBag;
}

function getItemIconClass(item: OsItem) {
  return item.tipo === 'SERVICO'
    ? 'bg-brand-primary-light text-brand-primary'
    : 'bg-brand-primary-light text-brand-primary';
}

function getItemTotal(item: OsItem): number {
  if ('valor_total' in item && item.valor_total !== undefined) return item.valor_total;
  return item.quantidade * item.valor_unitario;
}
</script>

<template>
  <div class="space-y-4 animate-fadeIn">
    <div class="flex items-center justify-between border-b border-slate-200 pb-3">
      <div class="flex items-center gap-3">
        <div class="bg-brand-primary-light p-2 rounded-lg text-brand-primary">
          <Package :size="20" />
        </div>
        <div>
          <h5 class="text-sm font-bold text-slate-700">Itens da OS</h5>
          <p class="text-xs text-slate-500">Serviços e Peças adicionados</p>
        </div>
      </div>

      <BaseButton v-if="!isLocked" variant="primary" size="sm" @click="emit('addItem')">
        <Plus :size="16" class="mr-2" />
        ADICIONAR ITEM
      </BaseButton>
    </div>

    <fieldset :disabled="isLocked" class="contents">
      <div
        v-if="itens.length === 0"
        class="flex flex-col items-center justify-center py-12 text-slate-400 border-2 border-dashed border-slate-200 rounded-xl bg-slate-50/50"
      >
        <div class="w-14 h-14 bg-slate-100 rounded-full flex items-center justify-center mb-3">
          <Package :size="28" stroke-width="1.5" class="text-slate-300" />
        </div>
        <p class="text-sm font-semibold text-slate-500">Nenhum item adicionado</p>
        <p class="text-xs text-slate-400 mt-1">Clique em "Adicionar Item" para incluir serviços ou peças.</p>
      </div>

      <div v-else class="space-y-2">
        <div
          v-for="(item, index) in itens"
          :key="'id' in item && item.id ? item.id : `new-${index}`"
          class="flex items-center justify-between p-3 bg-white border border-slate-200 rounded-lg hover:border-brand-primary/20 transition-colors group"
        >
          <div class="flex items-center gap-3 overflow-hidden">
            <div class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0" :class="getItemIconClass(item)">
              <component :is="getItemIcon(item)" :size="18" />
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-2 min-w-0">
                <p class="text-sm font-bold text-slate-700 truncate">{{ item.nome }}</p>
                <span
                  v-if="temAprovacaoItens"
                  class="text-[10px] font-bold px-1.5 py-0.5 rounded-full shrink-0"
                  :class="statusBadge(item).cls"
                >
                  {{ statusBadge(item).label }}
                </span>
              </div>
              <p class="text-xs text-slate-500 truncate">
                {{ item.unidade_medida }}
                <span v-if="temGarantiaItens && garantiaLabel(item)"> · Garantia {{ garantiaLabel(item) }}</span>
              </p>
            </div>
          </div>

          <div class="flex items-center gap-6 shrink-0">
            <div class="text-right hidden sm:block">
              <p class="text-xs text-slate-400 font-medium uppercase">Qtd</p>
              <p class="text-sm font-bold text-slate-600">{{ item.quantidade }}</p>
            </div>
            <div class="text-right hidden sm:block">
              <p class="text-xs text-slate-400 font-medium uppercase">Unitário</p>
              <p class="text-sm font-bold text-slate-600">{{ formatCurrency(item.valor_unitario) }}</p>
            </div>
            <div class="text-right w-24">
              <p class="text-xs text-slate-400 font-medium uppercase">Total</p>
              <p class="text-sm font-black text-slate-800">{{ formatCurrency(getItemTotal(item)) }}</p>
            </div>

            <div v-if="!isLocked" class="flex items-center gap-1 pl-2 border-l border-slate-100">
              <BaseButton variant="ghost" size="sm" class="p-1.5 text-slate-400 hover:text-brand-primary hover:bg-brand-primary-light" @click="emit('editItem', index)">
                <Pencil :size="14" />
              </BaseButton>
              <BaseButton variant="ghost" size="sm" class="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50" @click="emit('removeItem', index)">
                <Trash2 :size="14" />
              </BaseButton>
            </div>
          </div>
        </div>
      </div>

    </fieldset>
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
