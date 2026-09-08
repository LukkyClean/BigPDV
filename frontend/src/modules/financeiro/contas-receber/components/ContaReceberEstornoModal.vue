<script setup lang="ts">
/**
 * Estorno de um recebimento lançado errado — o cheque voltou, o PIX não caiu.
 *
 * Gêmeo do estorno de pagamento: o motivo é obrigatório porque é o que a
 * auditoria lê, e nada é apagado do livro. Um lançamento contrário entra com a
 * data de hoje.
 */
import { computed, ref, watch } from 'vue';
import { Undo2 } from 'lucide-vue-next';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { useToast } from '@/shared/composables/useToast';
import { formatCurrency } from '@/shared/utils/finance';
import { formatData } from '@/shared/utils/date.utils';

import { useEstornarRecebimento } from '../../shared/composables/useFinanceiro';
import type { ContaReceber } from '../../shared/schemas/financeiro.schema';

const props = defineProps<{ conta: ContaReceber | null }>();
const emit = defineEmits<{ fechar: [] }>();

const toast = useToast();
const estornar = useEstornarRecebimento();

const motivo = ref('');
watch(() => props.conta, () => { motivo.value = ''; });

const podeConfirmar = computed(() => motivo.value.trim().length >= 3);

function confirmar() {
  if (!props.conta || !podeConfirmar.value) return;
  estornar.mutate(
    { id: props.conta.id, motivo: motivo.value.trim() },
    {
      onSuccess: () => emit('fechar'),
      onError: (e: any) =>
        toast.error(e?.response?.data?.detail ?? 'Não foi possível estornar o recebimento'),
    },
  );
}
</script>

<template>
  <BaseModal
    :is-open="!!conta"
    title="Estornar recebimento"
    subtitle="A cobrança volta para em aberto"
    size="sm"
    overlay
    @close="emit('fechar')"
  >
    <div v-if="conta" class="flex flex-col gap-4">
      <div class="rounded-xl bg-zinc-50 px-4 py-3">
        <p class="text-sm font-semibold text-zinc-800">{{ conta.descricao }}</p>
        <p class="mt-0.5 text-xs text-zinc-500">
          Recebido {{ formatCurrency(conta.valor_recebido ?? conta.valor) }}
          <template v-if="conta.recebido_em"> em {{ formatData(conta.recebido_em) }}</template>
        </p>
      </div>

      <div class="w-full">
        <label for="motivo-estorno-receber" class="mb-1 block select-none text-xs font-medium text-zinc-700">
          Motivo <span class="text-red-600">*</span>
        </label>
        <textarea
          id="motivo-estorno-receber"
          v-model="motivo"
          rows="3"
          placeholder="Ex.: o cheque voltou"
          class="w-full resize-none rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-700 outline-none transition-colors duration-200 placeholder:text-zinc-400 focus:border-brand-primary focus:ring-1 focus:ring-brand-primary"
        />
      </div>

      <div class="flex items-start gap-2.5 rounded-xl border border-amber-100 bg-amber-50 p-3 text-amber-700">
        <Undo2 :size="16" class="mt-0.5 shrink-0" />
        <p class="text-xs leading-snug">
          O recebimento não é apagado. Um lançamento contrário entra no livro com a data de
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
