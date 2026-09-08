<script setup lang="ts">
/**
 * Classificar uma conta — inclusive uma já PAGA.
 *
 * Modal próprio, e não o formulário completo, porque a pergunta aqui é uma só:
 * "de que categoria foi esse gasto?". Abrir o formulário inteiro com valor e
 * vencimento desabilitados diria ao dono que ele pode mexer neles, e o backend
 * recusaria — a categoria é o único campo que continua livre depois do
 * pagamento, porque é o único que nunca entrou no livro do dinheiro.
 *
 * É o fim do laço que o primeiro uso encontrou: o alerta "gastos sem
 * categoria" conta despesa PAGA, e conta paga não tinha como ser classificada.
 * O aviso não sairia da tela nunca.
 */
import { computed, ref, watch } from 'vue';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import { formatCurrency } from '@/shared/utils/finance';
import { formatDataPura } from '@/shared/utils/date.utils';

import {
  useAtualizarContaPagar,
  usePlanoContasQuery,
} from '../../shared/composables/useFinanceiro';
import type { ContaPagar } from '../../shared/schemas/financeiro.schema';

const props = defineProps<{ conta: ContaPagar | null }>();
const emit = defineEmits<{ fechar: [] }>();

const { data: planos } = usePlanoContasQuery(true);
const atualizar = useAtualizarContaPagar();

const planoContaId = ref<string | number>('');

watch(
  () => props.conta,
  (conta) => {
    planoContaId.value = conta?.plano_conta_id ?? '';
  },
  { immediate: true },
);

const opcoes = computed(() =>
  (planos.value ?? []).map((p) => ({ value: p.id, label: p.nome })),
);

function salvar() {
  if (!props.conta) return;
  atualizar.mutate(
    {
      id: props.conta.id,
      payload: {
        plano_conta_id: planoContaId.value === '' ? null : Number(planoContaId.value),
      },
    },
    { onSuccess: () => emit('fechar') },
  );
}
</script>

<template>
  <BaseModal :is-open="!!conta" title="Classificar conta" size="sm" overlay @close="emit('fechar')">
    <div v-if="conta" class="flex flex-col gap-4">
      <div class="rounded-xl bg-zinc-50 px-4 py-3">
        <p class="text-sm font-semibold text-zinc-800">{{ conta.descricao }}</p>
        <p class="mt-0.5 text-xs text-zinc-500">
          {{ formatCurrency(conta.valor_pago ?? conta.valor) }} · vence
          {{ formatDataPura(conta.vencimento) }}
        </p>
      </div>

      <BaseSelect
        v-model="planoContaId"
        label="Categoria"
        :options="opcoes"
        placeholder="Sem categoria"
      />

      <p class="text-xs text-zinc-400">
        A categoria é a leitura contábil do gasto — ela não entrou no livro do dinheiro, e por
        isso pode ser corrigida mesmo depois do pagamento. Valor e vencimento, não: para
        mudá-los é preciso estornar antes.
      </p>
    </div>

    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <BaseButton variant="secondary" class="px-5" @click="emit('fechar')">Cancelar</BaseButton>
        <BaseButton
          variant="primary"
          class="px-5"
          :is-loading="atualizar.isPending.value"
          @click="salvar"
        >
          Salvar categoria
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
