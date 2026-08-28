<script setup lang="ts">
/**
 * Tudo sobre uma conta a pagar, incluindo a trilha de auditoria.
 *
 * Gêmeo do detalhe de recebimento, e existe pela mesma razão: a lista mostra
 * cinco colunas e o documento guarda o dobro. Aqui a pergunta que ele responde
 * é a que o módulo inteiro veio resolver — "quem prorrogou este aluguel?".
 */
import { computed } from 'vue';
import { ArrowRight } from 'lucide-vue-next';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { formatCurrency } from '@/shared/utils/finance';
import { formatData, formatDataPura } from '@/shared/utils/date.utils';

import HistoricoFinanceiro from '../../shared/components/HistoricoFinanceiro.vue';
import { useHistoricoContaQuery } from '../../shared/composables/useFinanceiro';
import type { ContaPagar } from '../../shared/schemas/financeiro.schema';

const props = defineProps<{ conta: ContaPagar | null }>();
const emit = defineEmits<{ fechar: [] }>();

const contaId = computed(() => props.conta?.id ?? null);
const { data: historico, isLoading } = useHistoricoContaQuery(contaId);

const paga = computed(() => props.conta?.status === 'PAGA');

/** Diferença entre o previsto e o que saiu: juros de atraso ou desconto. */
const diferenca = computed(() => {
  const c = props.conta;
  if (!c || c.valor_pago == null) return 0;
  return c.valor_pago - c.valor;
});
</script>

<template>
  <BaseModal
    :is-open="!!conta"
    title="Detalhes da conta"
    size="sm"
    overlay
    @close="emit('fechar')"
  >
    <div v-if="conta" class="flex flex-col gap-5">
      <div>
        <p class="text-sm font-semibold text-gray-800">{{ conta.descricao }}</p>
        <p class="mt-0.5 text-xs text-gray-400">
          {{ conta.plano_conta_nome ?? 'Sem categoria' }}
          <template v-if="conta.fornecedor_nome"> · {{ conta.fornecedor_nome }}</template>
          <template v-if="conta.parcela_total">
            · parcela {{ conta.parcela_numero }} de {{ conta.parcela_total }}
          </template>
          <template v-else-if="conta.recorrente"> · repete todo mês</template>
        </p>
      </div>

      <dl class="flex flex-col gap-2 rounded-xl bg-gray-50 px-4 py-3 text-sm">
        <div class="flex justify-between gap-3">
          <dt class="text-gray-500">Previsto</dt>
          <dd class="font-medium text-gray-800 tabular-nums">{{ formatCurrency(conta.valor) }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-gray-500">Vencimento</dt>
          <dd class="text-gray-800">{{ formatDataPura(conta.vencimento) }}</dd>
        </div>

        <template v-if="paga">
          <div class="flex justify-between gap-3 border-t border-gray-200 pt-2">
            <dt class="text-gray-500">Pago</dt>
            <dd class="font-medium text-gray-800 tabular-nums">
              {{ formatCurrency(conta.valor_pago ?? 0) }}
            </dd>
          </div>
          <div v-if="diferenca !== 0" class="flex justify-between gap-3">
            <dt class="text-gray-500">{{ diferenca > 0 ? 'Acréscimo' : 'Desconto' }}</dt>
            <dd class="tabular-nums" :class="diferenca > 0 ? 'text-amber-700' : 'text-emerald-700'">
              {{ formatCurrency(Math.abs(diferenca)) }}
            </dd>
          </div>
        </template>
      </dl>

      <dl v-if="paga" class="flex flex-col gap-2 text-sm">
        <div class="flex justify-between gap-3">
          <dt class="text-gray-500">Pago em</dt>
          <dd class="text-gray-800">{{ formatData(conta.pago_em) }}</dd>
        </div>
        <div v-if="conta.conta_bancaria_nome" class="flex justify-between gap-3">
          <dt class="text-gray-500">Saiu de</dt>
          <dd class="text-gray-800">{{ conta.conta_bancaria_nome }}</dd>
        </div>
      </dl>

      <p v-else class="flex items-center gap-1.5 text-sm text-gray-500">
        <ArrowRight :size="14" class="text-gray-400" />
        {{ conta.status === 'CANCELADA' ? 'Cancelada.' : 'Ainda não paga.' }}
      </p>

      <div v-if="conta.observacao" class="rounded-xl border border-gray-100 px-3.5 py-2.5">
        <p class="text-xs text-gray-500">{{ conta.observacao }}</p>
      </div>

      <HistoricoFinanceiro :historico="historico ?? []" :carregando="isLoading" />
    </div>

    <template #footer>
      <div class="flex w-full justify-end">
        <BaseButton variant="secondary" class="px-5" @click="emit('fechar')">Fechar</BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
