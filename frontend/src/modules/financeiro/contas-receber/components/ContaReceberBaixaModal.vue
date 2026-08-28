<script setup lang="ts">
/**
 * O recebimento: a promessa vira dinheiro e o livro registra a entrada.
 *
 * É o momento que o fecho da venda já deixava marcado no código — "o movimento
 * nasce no dia em que o cliente pagar".
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

import { usePaymentMethodsQuery } from '@/modules/sales/composables/queries/usePaymentMethodsQuery';

import {
  useContasBancariasQuery,
  useReceberConta,
} from '../../shared/composables/useFinanceiro';
import type { ContaReceber } from '../../shared/schemas/financeiro.schema';

const props = defineProps<{ conta: ContaReceber | null }>();
const emit = defineEmits<{ fechar: [] }>();

const toast = useToast();
const { data: contasBancarias } = useContasBancariasQuery();
const receber = useReceberConta();

// O catálogo é o mesmo do PDV e da OS: reusar em vez de duplicar é o que
// garante que a forma escolhida aqui seja a mesma que aparece no relatório.
const { formasPagamento } = usePaymentMethodsQuery();

const valorReais = ref(0);
const jurosReais = ref(0);

/**
 * Para ONDE vai o juros — e é a diferença entre registrar dinheiro que existe e
 * dinheiro que não existe.
 *
 * LOJA é multa por atraso: receita dela, entra no caixa com o principal.
 * OPERADORA é o juros do parcelamento na maquininha: o cliente desembolsa, mas
 * esse pedaço nunca chega na loja. Lançá-lo como entrada mostraria saldo que a
 * conta bancária não tem, e o caixa fecharia com sobra em todo parcelamento.
 */
const jurosDestino = ref<'LOJA' | 'OPERADORA'>('LOJA');
const recebidoEm = ref('');
const contaBancariaId = ref<string | number>('');
const formaPagamentoId = ref<string | number>('');

function hojeLocal(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

watch(
  () => props.conta,
  (conta) => {
    if (!conta) return;
    valorReais.value = conta.valor / 100;
    jurosReais.value = 0;
    jurosDestino.value = 'LOJA';
    formaPagamentoId.value = '';
    recebidoEm.value = hojeLocal();
    contaBancariaId.value = contasBancarias.value?.find((c) => c.principal)?.id ?? '';
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

const opcoesFormas = computed(() =>
  formasPagamento.value.filter((f) => f.ativo).map((f) => ({ value: f.id, label: f.nome })),
);

/**
 * O total sobe sozinho quando há juros.
 *
 * Quem cobrou multa quer receber principal + multa, e obrigar a somar de cabeça
 * no balcão convida ao erro. O campo continua editável para o recebimento
 * PARCIAL -- o cliente que devia 200 e trouxe 150.
 */
watch(jurosReais, (juros, anterior) => {
  if (!props.conta) return;
  const esperadoAntes = props.conta.valor / 100 + (anterior ?? 0);
  // Só reajusta se o operador não tinha mexido no total à mão.
  if (Math.abs(valorReais.value - esperadoAntes) < 0.005) {
    valorReais.value = props.conta.valor / 100 + juros;
  }
});

/** O que de fato entra na loja: sem o juros quando ele é da operadora. */
const entraNaLoja = computed(() => {
  const total = Math.round(valorReais.value * 100);
  return jurosDestino.value === 'OPERADORA'
    ? total - Math.round(jurosReais.value * 100)
    : total;
});

/**
 * Quanto falta (ou sobra) sobre o que era ESPERADO — principal mais juros.
 *
 * Comparar com o principal puro faria o juros aparecer duas vezes: uma no campo
 * dele e outra como "entrou a mais". O que interessa aqui é o outro caso: o
 * cliente devia R$ 200 e trouxe R$ 150.
 */
const diferenca = computed(() => {
  if (!props.conta) return 0;
  const esperado = props.conta.valor + Math.round(jurosReais.value * 100);
  return Math.round(valorReais.value * 100) - esperado;
});

function confirmar() {
  if (!props.conta || valorReais.value <= 0) return;
  receber.mutate(
    {
      id: props.conta.id,
      payload: {
        valor_recebido: Math.round(valorReais.value * 100),
        juros: Math.round(jurosReais.value * 100),
        juros_destino: jurosDestino.value,
        recebido_em: recebidoEm.value,
        conta_bancaria_id: contaBancariaId.value === '' ? null : Number(contaBancariaId.value),
        forma_pagamento_id: formaPagamentoId.value === '' ? null : Number(formaPagamentoId.value),
      },
    },
    {
      onSuccess: () => emit('fechar'),
      onError: (e: any) =>
        toast.error(e?.response?.data?.detail ?? 'Não foi possível registrar o recebimento'),
    },
  );
}
</script>

<template>
  <BaseModal
    :is-open="!!conta"
    title="Registrar recebimento"
    size="sm"
    overlay
    @close="emit('fechar')"
  >
    <div v-if="conta" class="flex flex-col gap-4">
      <div class="rounded-xl bg-gray-50 px-4 py-3">
        <p class="text-sm font-semibold text-gray-800">{{ conta.descricao }}</p>
        <p class="mt-0.5 text-xs text-gray-500">
          Previsto {{ formatCurrency(conta.valor) }} · vence {{ formatDataPura(conta.vencimento) }}
          <template v-if="conta.taxa > 0">
            · taxa da operadora {{ formatCurrency(conta.taxa) }}
          </template>
        </p>
      </div>

      <BaseSelect
        v-model="formaPagamentoId"
        :options="opcoesFormas"
        label="Como está pagando"
        placeholder="Selecione a forma"
      />

      <BaseMoneyInput v-model="jurosReais" label="Juros / multa" />

      <!-- Sem esta escolha, o juros da maquininha entraria no caixa como se
           fosse dinheiro da loja. -->
      <fieldset v-if="jurosReais > 0" class="-mt-1 flex flex-col gap-2">
        <legend class="mb-1 block text-xs font-medium text-gray-700">Esse juros fica com</legend>
        <div class="grid gap-2 sm:grid-cols-2">
          <label
            v-for="opcao in [
              { valor: 'LOJA', titulo: 'A loja', ajuda: 'Multa por atraso' },
              { valor: 'OPERADORA', titulo: 'A operadora', ajuda: 'Juros do parcelamento' },
            ]"
            :key="opcao.valor"
            class="cursor-pointer rounded-xl border px-3 py-2 transition"
            :class="jurosDestino === opcao.valor
              ? 'border-brand-primary bg-brand-primary/5 ring-1 ring-brand-primary'
              : 'border-gray-200 hover:border-gray-300'"
          >
            <input v-model="jurosDestino" type="radio" :value="opcao.valor" class="sr-only" />
            <span class="block text-sm font-medium text-gray-800">{{ opcao.titulo }}</span>
            <span class="block text-[11px] text-gray-400">{{ opcao.ajuda }}</span>
          </label>
        </div>
      </fieldset>

      <BaseMoneyInput v-model="valorReais" label="Valor recebido (total)" />
      <p v-if="diferenca !== 0" class="-mt-2 text-xs" :class="diferenca > 0 ? 'text-emerald-600' : 'text-amber-600'">
        {{ diferenca > 0 ? 'Entrou' : 'Faltou' }}
        {{ formatCurrency(Math.abs(diferenca)) }} em relação ao previsto.
      </p>

      <p v-if="jurosDestino === 'OPERADORA' && jurosReais > 0" class="-mt-2 rounded-xl bg-amber-50 px-3.5 py-2.5 text-xs text-amber-700">
        O cliente desembolsa {{ formatCurrency(Math.round(valorReais * 100)) }}, mas entram
        <strong>{{ formatCurrency(entraNaLoja) }}</strong> na loja — o resto fica com a operadora.
      </p>

      <BaseInput v-model="recebidoEm" type="date" label="Data do recebimento" required />

      <BaseSelect
        v-model="contaBancariaId"
        :options="opcoesContas"
        label="Entrou em"
        placeholder="Selecione a conta"
      />

      <p class="text-xs text-gray-400">
        Quitar uma dívida antiga não é venda no PDV. Se o dinheiro entrou na gaveta, registre
        um suprimento à parte.
      </p>
    </div>

    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <BaseButton variant="secondary" class="px-5" @click="emit('fechar')">Cancelar</BaseButton>
        <BaseButton
          variant="primary"
          class="px-5"
          :disabled="valorReais <= 0"
          :is-loading="receber.isPending.value"
          @click="confirmar"
        >
          Confirmar recebimento
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
