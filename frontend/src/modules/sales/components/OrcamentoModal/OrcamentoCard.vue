<script setup lang="ts">
import { computed } from 'vue';

import { TicketPercent, Truck, UserRound, CalendarDays, Settings } from 'lucide-vue-next';

import { useOrcamentoDetailsForm } from '../../composables/flows/useOrcamentoDetailsForm';

import BaseInfoCard from '@/shared/components/layout/StatsCard/BaseInfoCard.vue';
import MoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';
import BaseTextarea from '@/shared/components/ui/BaseInput/BaseTextarea.vue';

import { OrcamentoRead } from '../../schemas/orcamento.schema';
import { formatDataHora } from '@/shared/utils/date.utils';

const props = defineProps<{
  orcamento: OrcamentoRead | undefined;
  readonly: boolean;
}>();

const orcamentoRef = computed(() => props.orcamento);
const { form, isSaving, saveNow } = useOrcamentoDetailsForm(orcamentoRef);

const orcamentoDisplay = computed(() => {
  if (!props.orcamento) return '...';
  return `ORC #${String(props.orcamento.id).padStart(6, '0')}`;
});

// Mesmo caso do SaleCard: hora UTC crua virava texto na tela.
const createdAt = computed(() =>
  props.orcamento?.criado_em ? formatDataHora(props.orcamento.criado_em).replace(',', ' as') : null,
);
</script>
<template>
  <BaseInfoCard :icon="Settings" title="Dados do orçamento">
    <div class="px-4 py-3 flex flex-col gap-3">
      <!-- Número do Orçamento + Status -->
      <div class="flex items-center gap-2">
        <h2 class="font-poppins font-bold text-sm text-zinc-800 underline underline-offset-2">
          {{ orcamentoDisplay }}
        </h2>
        <span
          :class="[
            'px-2.5 py-0.5 text-[10px] font-semibold rounded-full border',
            orcamento?.convertido ? 'text-green-700 bg-green-50' : 'text-blue-700 bg-blue-50',
          ]"
        >
          {{ orcamento?.convertido ? 'Convertido' : 'Ativo' }}
        </span>
      </div>

      <!-- Funcionário Responsável -->
      <div class="flex flex-col gap-1">
        <h2 class="font-poppins font-bold text-xs text-zinc-600 uppercase">Funcionário Responsável</h2>
        <div class="flex items-center gap-2">
          <UserRound :size="18" class="text-zinc-500 shrink-0" />
          <div class="flex flex-col">
            <span class="font-poppins text-sm text-zinc-800">{{ orcamento?.funcionario?.nome ?? '—' }}</span>
            <span
              v-if="orcamento?.funcionario?.cargo?.nome"
              class="font-poppins text-[10px] font-bold text-blue-600 uppercase tracking-wide"
            >
              {{ orcamento.funcionario.cargo.nome }}
            </span>
          </div>
        </div>
      </div>

      <!-- Criado em -->
      <div class="flex flex-col gap-1">
        <h2 class="font-poppins font-bold text-xs text-zinc-600 uppercase">Criado em</h2>
        <div class="flex items-center gap-2">
          <CalendarDays :size="18" class="text-zinc-500 shrink-0" />
          <p class="font-poppins text-sm">
            {{ createdAt }}
          </p>
        </div>
      </div>

      <!-- Entrega -->
      <div class="flex flex-col gap-1">
        <h2 class="font-poppins font-bold text-xs text-zinc-600 uppercase">Entrega</h2>
        <div class="flex gap-2 items-center" data-sale-entrega>
          <Truck :size="18" class="text-zinc-500 shrink-0" />
          <MoneyInput v-model.number="form.entrega" :disabled="isSaving || readonly" @blur="saveNow" @enter="saveNow" class="w-auto" />
        </div>
      </div>

      <!-- Desconto -->
      <div class="flex flex-col gap-1">
        <h2 class="font-poppins font-bold text-xs text-zinc-600 uppercase">Desconto</h2>
        <div class="flex gap-2 items-center" data-sale-desconto>
          <TicketPercent :size="18" class="text-zinc-500 shrink-0" />
          <MoneyInput v-model.number="form.desconto" :disabled="isSaving || readonly" @blur="saveNow" @enter="saveNow" class="w-auto" />
        </div>
      </div>

      <!-- Observação -->
      <div class="flex flex-col gap-1">
        <h2 class="font-poppins font-bold text-xs text-zinc-600 uppercase">Observação</h2>
        <BaseTextarea v-model="form.observacao" :disabled="isSaving || readonly" placeholder="Adicione uma observação sobre esse orçamento" class="w-full" />
      </div>
    </div>
  </BaseInfoCard>
</template>
