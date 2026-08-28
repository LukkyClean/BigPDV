<script setup lang="ts">
/**
 * Estorno de um pagamento lançado errado.
 *
 * O motivo é obrigatório porque é o que a auditoria lê depois: sem ele,
 * `historico_financeiro` registraria que alguém desfez um pagamento de R$ 2.500
 * e ninguém saberia por quê.
 *
 * O estorno NÃO apaga a baixa: gera um movimento contrário no livro do dinheiro,
 * com a data de HOJE. Está escrito na tela porque o usuário precisa entender
 * que a operação deixa rastro — quem espera que "some" fica desconfiado ao ver
 * dois lançamentos depois.
 */
import { computed, ref, watch } from 'vue';
import { Undo2 } from 'lucide-vue-next';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { useToast } from '@/shared/composables/useToast';
import { formatCurrency } from '@/shared/utils/finance';
import { formatData } from '@/shared/utils/date.utils';

import { useEstornarPagamento } from '../../shared/composables/useFinanceiro';
import type { ContaPagar } from '../../shared/schemas/financeiro.schema';

const props = defineProps<{ conta: ContaPagar | null }>();
const emit = defineEmits<{ fechar: [] }>();

const toast = useToast();
const estornar = useEstornarPagamento();

const motivo = ref('');

// Limpa a cada abertura: o motivo do estorno anterior não tem nada a ver com
// este, e deixá-lo no campo convida a confirmar sem ler.
watch(() => props.conta, () => { motivo.value = ''; });

// O backend exige 3 caracteres. Barrar aqui evita a viagem até o 422.
const podeConfirmar = computed(() => motivo.value.trim().length >= 3);

function confirmar() {
  if (!props.conta || !podeConfirmar.value) return;
  estornar.mutate(
    { id: props.conta.id, motivo: motivo.value.trim() },
    {
      onSuccess: () => emit('fechar'),
      onError: (e: any) =>
        toast.error(e?.response?.data?.detail ?? 'Não foi possível estornar o pagamento'),
    },
  );
}
</script>

<template>
  <BaseModal
    :is-open="!!conta"
    title="Estornar pagamento"
    subtitle="A conta volta para em aberto"
    size="sm"
    overlay
    @close="emit('fechar')"
  >
    <div v-if="conta" class="flex flex-col gap-4">
      <div class="rounded-xl bg-gray-50 px-4 py-3">
        <p class="text-sm font-semibold text-gray-800">{{ conta.descricao }}</p>
        <p class="mt-0.5 text-xs text-gray-500">
          Pago {{ formatCurrency(conta.valor_pago ?? conta.valor) }}
          <template v-if="conta.pago_em"> em {{ formatData(conta.pago_em) }}</template>
        </p>
      </div>

      <div class="w-full">
        <label for="motivo-estorno" class="mb-1 block select-none text-xs font-medium text-gray-700">
          Motivo <span class="text-red-600">*</span>
        </label>
        <textarea
          id="motivo-estorno"
          v-model="motivo"
          rows="3"
          placeholder="Ex.: lançado na conta errada"
          class="w-full resize-none rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 outline-none transition-colors duration-200 placeholder:text-gray-400 focus:border-brand-primary focus:ring-1 focus:ring-brand-primary"
        />
      </div>

      <div class="flex items-start gap-2.5 rounded-xl border border-amber-100 bg-amber-50 p-3 text-amber-700">
        <Undo2 :size="16" class="mt-0.5 shrink-0" />
        <p class="text-xs leading-snug">
          O pagamento não é apagado. Um lançamento contrário entra no livro com a data de
          hoje, e os dois ficam no histórico.
        </p>
      </div>
    </div>

    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <BaseButton variant="secondary" class="px-5" @click="emit('fechar')">Cancelar</BaseButton>
        <BaseButton
          variant="primary"
          class="px-5"
          :disabled="!podeConfirmar"
          :is-loading="estornar.isPending.value"
          @click="confirmar"
        >
          Estornar
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
