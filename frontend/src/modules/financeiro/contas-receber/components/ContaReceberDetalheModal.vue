<script setup lang="ts">
/**
 * Tudo sobre uma cobrança, incluindo a trilha de auditoria.
 *
 * A lista mostra cinco colunas; o documento guarda o dobro disso — quanto era
 * previsto, quanto de juros e para ONDE ele foi, o que de fato entrou na loja,
 * em qual conta caiu, e quem mexeu no quê. Sem esta tela, a metade mais
 * importante ficava só no banco.
 */
import { computed } from 'vue';
import { ArrowRight } from 'lucide-vue-next';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { formatCurrency } from '@/shared/utils/finance';
import { formatData, formatDataPura } from '@/shared/utils/date.utils';

import HistoricoFinanceiro from '../../shared/components/HistoricoFinanceiro.vue';
import { useHistoricoRecebimentoQuery } from '../../shared/composables/useFinanceiro';
import type { ContaReceber } from '../../shared/schemas/financeiro.schema';

const props = defineProps<{ conta: ContaReceber | null }>();
const emit = defineEmits<{ fechar: [] }>();

const contaId = computed(() => props.conta?.id ?? null);
const { data: historico, isLoading } = useHistoricoRecebimentoQuery(contaId);

const recebida = computed(() => props.conta?.status === 'RECEBIDA');

/**
 * O que de fato entrou na loja.
 *
 * Diverge do que o cliente desembolsou exatamente quando o juros é da
 * operadora — e é essa diferença que a tela precisa deixar explícita, senão o
 * lojista lê o total e acha que recebeu tudo.
 */
const entrouNaLoja = computed(() => {
  const c = props.conta;
  if (!c || c.valor_recebido == null) return 0;
  return c.juros_destino === 'OPERADORA' ? c.valor_recebido - c.juros : c.valor_recebido;
});

const origem = computed(() => {
  const c = props.conta;
  if (!c) return '';
  if (c.venda_pagamento_id) return 'Nasceu do fechamento de uma venda';
  if (c.ordem_servico_pagamento_id) return 'Nasceu do fechamento de uma OS';
  return 'Lançada à mão';
});
</script>

<template>
  <BaseModal
    :is-open="!!conta"
    title="Detalhes da cobrança"
    size="sm"
    overlay
    @close="emit('fechar')"
  >
    <div v-if="conta" class="flex flex-col gap-5">
      <div>
        <p class="text-sm font-semibold text-gray-800">{{ conta.descricao }}</p>
        <p class="mt-0.5 text-xs text-gray-400">
          {{ origem }}<template v-if="conta.cliente_nome"> · {{ conta.cliente_nome }}</template>
        </p>
      </div>

      <!-- Valores -->
      <dl class="flex flex-col gap-2 rounded-xl bg-gray-50 px-4 py-3 text-sm">
        <div class="flex justify-between gap-3">
          <dt class="text-gray-500">Previsto</dt>
          <dd class="font-medium text-gray-800 tabular-nums">{{ formatCurrency(conta.valor) }}</dd>
        </div>
        <div class="flex justify-between gap-3">
          <dt class="text-gray-500">Vencimento</dt>
          <dd class="text-gray-800">{{ formatDataPura(conta.vencimento) }}</dd>
        </div>
        <div v-if="conta.taxa > 0" class="flex justify-between gap-3">
          <dt class="text-gray-500">Taxa da operadora</dt>
          <dd class="text-gray-800 tabular-nums">{{ formatCurrency(conta.taxa) }}</dd>
        </div>

        <template v-if="recebida">
          <div v-if="conta.juros > 0" class="flex justify-between gap-3 border-t border-gray-200 pt-2">
            <dt class="text-gray-500">
              Juros
              <span class="text-[11px] text-gray-400">
                ({{ conta.juros_destino === 'OPERADORA' ? 'fica com a operadora' : 'fica com a loja' }})
              </span>
            </dt>
            <dd class="text-gray-800 tabular-nums">{{ formatCurrency(conta.juros) }}</dd>
          </div>

          <div class="flex justify-between gap-3" :class="conta.juros > 0 ? '' : 'border-t border-gray-200 pt-2'">
            <dt class="text-gray-500">O cliente pagou</dt>
            <dd class="font-medium text-gray-800 tabular-nums">
              {{ formatCurrency(conta.valor_recebido ?? 0) }}
            </dd>
          </div>

          <!-- Só aparece quando os dois números divergem: repetir o mesmo valor
               duas vezes com nomes diferentes confundiria mais que explicaria. -->
          <div
            v-if="entrouNaLoja !== (conta.valor_recebido ?? 0)"
            class="flex justify-between gap-3 rounded-lg bg-amber-50 px-2.5 py-1.5"
          >
            <dt class="font-medium text-amber-700">Entrou na loja</dt>
            <dd class="font-bold text-amber-800 tabular-nums">{{ formatCurrency(entrouNaLoja) }}</dd>
          </div>
        </template>
      </dl>

      <!-- Como e onde -->
      <dl v-if="recebida" class="flex flex-col gap-2 text-sm">
        <div class="flex justify-between gap-3">
          <dt class="text-gray-500">Recebido em</dt>
          <dd class="text-gray-800">{{ formatData(conta.recebido_em) }}</dd>
        </div>
        <div v-if="conta.conta_bancaria_nome" class="flex justify-between gap-3">
          <dt class="text-gray-500">Caiu em</dt>
          <dd class="text-gray-800">{{ conta.conta_bancaria_nome }}</dd>
        </div>
      </dl>

      <p v-else class="flex items-center gap-1.5 text-sm text-gray-500">
        <ArrowRight :size="14" class="text-gray-400" />
        Ainda não recebida.
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
