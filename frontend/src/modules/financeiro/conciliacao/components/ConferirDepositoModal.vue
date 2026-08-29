<script setup lang="ts">
/**
 * "Caiu R$ 490 no dia 3" — e o sistema descobre o resto.
 *
 * A operadora deposita UM valor cobrindo VÁRIAS vendas. Aqui o dono digita o
 * que caiu de fato, vê a diferença na hora, e o backend rateia entre as
 * cobranças do dia proporcionalmente ao previsto de cada uma.
 *
 * O rateio é do SERVIDOR de propósito: é ele que garante que a soma das baixas
 * seja exatamente o depósito, centavo a centavo. Fazer a divisão aqui e mandar
 * pronto deixaria o arredondamento na mão da tela.
 */
import { computed, ref, watch } from 'vue';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseMoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import { formatCurrency } from '@/shared/utils/finance';
import { formatDataPura } from '@/shared/utils/date.utils';

import { useBaixarLote, useContasBancariasQuery } from '../../shared/composables/useFinanceiro';
import type { ConciliacaoDia } from '../../shared/schemas/financeiro.schema';

const props = defineProps<{ dia: ConciliacaoDia | null }>();
const emit = defineEmits<{ fechar: [] }>();

const { data: contasBancarias } = useContasBancariasQuery();
const baixarLote = useBaixarLote();

const valorReais = ref(0);
const contaBancariaId = ref<string | number>('');

watch(
  () => props.dia,
  (dia) => {
    if (!dia) return;
    // Começa no previsto: o caso mais comum é o depósito bater, e quando não
    // bate o dono corrige o número já vendo a diferença aparecer.
    valorReais.value = dia.total_previsto / 100;
    contaBancariaId.value = contasBancarias.value?.find((c) => c.principal)?.id ?? '';
  },
  { immediate: true },
);

const centavos = computed(() => Math.round(valorReais.value * 100));
const diferenca = computed(() => centavos.value - (props.dia?.total_previsto ?? 0));

const opcoesContas = computed(() =>
  (contasBancarias.value ?? []).map((c) => ({ value: c.id, label: c.nome })),
);

async function confirmar() {
  if (!props.dia) return;
  await baixarLote.mutateAsync({
    data: props.dia.data,
    valor_recebido: centavos.value,
    conta_bancaria_id: contaBancariaId.value ? Number(contaBancariaId.value) : null,
  });
  emit('fechar');
}
</script>

<template>
  <BaseModal
    :is-open="!!dia"
    title="Conferir depósito"
    size="sm"
    overlay
    @close="emit('fechar')"
  >
    <div v-if="dia" class="flex flex-col gap-4">
      <div class="rounded-xl bg-gray-50 px-4 py-3">
        <p class="text-sm font-semibold text-gray-800">
          Vencimento em {{ formatDataPura(dia.data) }}
        </p>
        <p class="mt-0.5 text-xs text-gray-500">
          {{ dia.quantidade }} cobrança(s) · previsto
          <strong>{{ formatCurrency(dia.total_previsto) }}</strong>
        </p>
      </div>

      <BaseMoneyInput v-model="valorReais" label="Quanto caiu de fato" />

      <!-- A diferença aparece ANTES de confirmar: é a única chance de o dono
           perceber que digitou o dia errado, e o depósito errado baixa um lote
           inteiro de uma vez. -->
      <p
        v-if="diferenca !== 0"
        class="-mt-2 rounded-xl px-3.5 py-2.5 text-xs"
        :class="diferenca < 0 ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'"
      >
        <template v-if="diferenca < 0">
          Faltam <strong>{{ formatCurrency(Math.abs(diferenca)) }}</strong> em relação ao
          previsto — normalmente é a taxa da operadora. Cada cobrança fica com a parte dela,
          proporcional ao valor.
        </template>
        <template v-else>
          Entraram <strong>{{ formatCurrency(diferenca) }}</strong> a mais que o previsto.
          Confira se o depósito é mesmo deste dia.
        </template>
      </p>

      <BaseSelect
        v-model="contaBancariaId"
        label="Caiu em"
        :options="opcoesContas"
        placeholder="Selecione a conta"
      />

      <p class="text-xs text-gray-400">
        As {{ dia.quantidade }} cobrança(s) deste dia serão baixadas de uma vez, cada uma pelo
        mesmo caminho da baixa manual — dá para estornar qualquer uma depois, em Contas a
        Receber.
      </p>
    </div>

    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <BaseButton variant="secondary" class="px-5" @click="emit('fechar')">Cancelar</BaseButton>
        <BaseButton
          variant="primary"
          class="px-5"
          :disabled="centavos <= 0"
          :is-loading="baixarLote.isPending.value"
          @click="confirmar"
        >
          Confirmar depósito
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
