<script setup lang="ts">
import { computed } from 'vue';
import { UserRound, CalendarDays, XCircle } from 'lucide-vue-next';
import BaseTextarea from '@/shared/components/ui/BaseInput/BaseTextarea.vue';
import type { SaleRead, SaleUpdate } from '../../schemas/sale.schema';
import { formatDataHora } from '@/shared/utils/date.utils';

const props = defineProps<{
  sale: SaleRead | undefined;
  readonly: boolean;
  form: SaleUpdate;
  isSaving: boolean;
  onSave: () => void;
}>();

// `criado_em` é UTC no backend. O `.split('T')[1]` anterior mostrava a hora UTC
// crua (com microssegundos) — agora sai a hora local, formatada.
const createdAt = computed(() =>
  props.sale?.criado_em ? formatDataHora(props.sale.criado_em).replace(',', ' às') : null,
);
</script>

<template>
  <div class="rounded-xl border border-zinc-200 bg-white p-3 flex flex-col gap-3">

    <!-- Funcionário + Data lado a lado -->
    <div class="grid grid-cols-2 gap-2">
      <div class="flex flex-col gap-0.5">
        <span class="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide flex items-center gap-1">
          <UserRound :size="10" /> Funcionário
        </span>
        <span class="text-xs font-medium text-zinc-700 truncate">{{ sale?.funcionario?.nome ?? '—' }}</span>
        <span v-if="sale?.funcionario?.cargo?.nome" class="text-[10px] text-blue-500 font-semibold truncate">
          {{ sale.funcionario.cargo.nome }}
        </span>
      </div>
      <div class="flex flex-col gap-0.5">
        <span class="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide flex items-center gap-1">
          <CalendarDays :size="10" /> Criada em
        </span>
        <span class="text-xs font-medium text-zinc-700">{{ createdAt ?? '—' }}</span>
      </div>
    </div>

    <div class="border-t border-zinc-100" />

    <!-- Observação -->
    <div class="flex flex-col gap-1">
      <span class="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide">Observação</span>
      <BaseTextarea
        v-model="form.observacao"
        :disabled="isSaving || readonly"
        placeholder="Adicione uma observação..."
        :rows="3"
        class="w-full text-sm"
        @blur="onSave"
      />
    </div>

    <!-- Observação Interna -->
    <div class="flex flex-col gap-1">
      <span class="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide">Obs. Interna</span>
      <BaseTextarea
        v-model="form.observacao_interna"
        :disabled="isSaving || readonly"
        placeholder="Nota interna..."
        :rows="3"
        class="w-full text-sm"
        @blur="onSave"
      />
    </div>

    <!-- Motivo do Cancelamento (apenas para vendas canceladas) -->
    <template v-if="sale?.status === 'CANCELADA' && sale?.motivo_cancelamento">
      <div class="border-t border-zinc-100" />
      <div class="flex flex-col gap-1.5">
        <span class="text-[10px] font-semibold text-red-400 uppercase tracking-wide flex items-center gap-1">
          <XCircle :size="10" /> Motivo do Cancelamento
        </span>
        <p class="text-xs text-zinc-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2 leading-relaxed">
          {{ sale.motivo_cancelamento }}
        </p>
      </div>
    </template>
  </div>
</template>
