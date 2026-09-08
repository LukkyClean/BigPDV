<script setup lang="ts">
/**
 * A baixa: é aqui que o documento vira lançamento no livro do dinheiro.
 *
 * O valor pago vem preenchido com o previsto, mas é EDITÁVEL — juros por
 * atraso e desconto por antecipação são a regra, não a exceção, e o relatório
 * soma o que saiu do bolso e não o que se previa.
 */
import { computed, ref, watch } from 'vue';
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseMoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import { useToast } from '@/shared/composables/useToast';
import { formatCurrency } from '@/shared/utils/finance';
import { formatDataPura } from '@/shared/utils/date.utils';

import {
  useContasBancariasQuery,
  usePagarConta,
} from '../../shared/composables/useFinanceiro';
import type { ContaPagar } from '../../shared/schemas/financeiro.schema';

const props = defineProps<{ conta: ContaPagar | null }>();
const emit = defineEmits<{ fechar: [] }>();

const toast = useToast();
const { data: contasBancarias } = useContasBancariasQuery();
const pagar = usePagarConta();

const valorReais = ref(0);
const pagoEm = ref('');
const contaBancariaId = ref<string | number>('');

function hojeLocal(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

watch(
  () => props.conta,
  (conta) => {
    if (!conta) return;
    valorReais.value = conta.valor / 100;
    pagoEm.value = hojeLocal();
    // Pré-seleciona a conta marcada como principal: o lojista paga quase sempre
    // do mesmo lugar, e escolher toda vez é atrito puro.
    contaBancariaId.value =
      contasBancarias.value?.find((c) => c.principal)?.id ?? '';
  },
  { immediate: true },
);

watch(contasBancarias, (lista) => {
  if (!contaBancariaId.value && lista?.length) {
    contaBancariaId.value = lista.find((c) => c.principal)?.id ?? lista[0].id;
  }
});

const opcoesContas = computed(() =>
  (contasBancarias.value ?? []).map((c) => ({ value: c.id, label: c.nome })),
);

const diferenca = computed(() => {
  if (!props.conta) return 0;
  return Math.round(valorReais.value * 100) - props.conta.valor;
});

function confirmar() {
  if (!props.conta || valorReais.value <= 0) return;

  pagar.mutate(
    {
      id: props.conta.id,
      payload: {
        valor_pago: Math.round(valorReais.value * 100),
        pago_em: pagoEm.value,
        conta_bancaria_id: contaBancariaId.value === '' ? null : Number(contaBancariaId.value),
      },
    },
    {
      onSuccess: () => emit('fechar'),
      onError: (e: any) =>
        toast.error(e?.response?.data?.detail ?? 'Não foi possível registrar o pagamento'),
    },
  );
}
</script>

<template>
  <BaseModal
    :is-open="!!conta"
    title="Registrar pagamento"
    size="sm"
    overlay
    @close="emit('fechar')"
  >
    <div v-if="conta" class="flex flex-col gap-4">
      <div class="rounded-xl bg-zinc-50 px-4 py-3">
        <p class="text-sm font-semibold text-zinc-800">{{ conta.descricao }}</p>
        <p class="mt-0.5 text-xs text-zinc-500">
          Previsto {{ formatCurrency(conta.valor) }} · vence {{ formatDataPura(conta.vencimento) }}
        </p>
      </div>

      <BaseMoneyInput v-model="valorReais" label="Valor pago" />
      <p v-if="diferenca !== 0" class="-mt-2 text-xs" :class="diferenca > 0 ? 'text-amber-600' : 'text-emerald-600'">
        {{ diferenca > 0 ? 'Acréscimo' : 'Desconto' }} de
        {{ formatCurrency(Math.abs(diferenca)) }} sobre o previsto.
      </p>

      <BaseInput v-model="pagoEm" type="date" label="Data do pagamento" required />

      <BaseSelect
        v-model="contaBancariaId"
        :options="opcoesContas"
        label="Saiu de"
        placeholder="Selecione a conta"
      />

      <p class="text-xs text-zinc-400">
        Pagar fornecedor não é sangria de caixa. Se o dinheiro saiu da gaveta, registre a
        sangria à parte no PDV.
      </p>
    </div>

    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <BaseButton variant="secondary" class="px-5" @click="emit('fechar')">Cancelar</BaseButton>
        <BaseButton
          variant="primary"
          class="px-5"
          :disabled="valorReais <= 0"
          :is-loading="pagar.isPending.value"
          @click="confirmar"
        >
          Confirmar pagamento
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
