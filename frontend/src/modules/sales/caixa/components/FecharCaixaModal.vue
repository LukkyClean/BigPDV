<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { EyeOff } from 'lucide-vue-next';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import MoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';

import { useFecharCaixaMutation } from '../composables/mutates/useCaixaMutations';
import type { SessaoCaixaResumo } from '../schemas/caixa.schema';
import { formatarCentavos } from '../caixa.utils';

const props = defineProps<{
  isOpen: boolean;
  sessao: SessaoCaixaResumo | null;
  /** Quando ligado, o operador digita o contado SEM ver o esperado. */
  cego: boolean;
}>();

const emit = defineEmits<{ (e: 'close'): void; (e: 'success'): void }>();

const contadoEmReais = ref(0);
const resultado = ref<SessaoCaixaResumo | null>(null);
const fecharMutation = useFecharCaixaMutation();

watch(
  () => props.isOpen,
  (aberto) => {
    if (aberto) {
      contadoEmReais.value = 0;
      resultado.value = null;
    }
  },
);

// Só é lido no ramo NÃO cego — ali o backend sempre manda o número. O `?? 0`
// existe para o intervalo em que a sessão ainda não carregou, não para o modo
// cego (que nem renderiza este bloco).
const esperado = computed(() => props.sessao?.saldo_esperado_dinheiro ?? 0);

// A diferença só aparece DEPOIS de fechar. Mostrá-la enquanto o operador digita
// transformaria a conferência em "acerte o número até zerar".
const diferenca = computed(() => resultado.value?.diferenca ?? null);

async function confirmar() {
  resultado.value = await fecharMutation.mutateAsync({
    saldo_contado: Math.round((contadoEmReais.value || 0) * 100),
    observacao: null,
  });
  emit('success');
}
</script>

<template>
  <BaseModal :is-open="props.isOpen" title="Fechar caixa" @close="emit('close')">
    <!-- Antes de fechar: conferência -->
    <div v-if="!resultado" class="space-y-4">
      <div v-if="props.cego" class="flex items-start gap-3 rounded-lg bg-zinc-50 p-3">
        <EyeOff class="h-5 w-5 shrink-0 text-zinc-500" />
        <p class="text-sm text-zinc-600">
          Conte o dinheiro da gaveta e informe o valor. O que o sistema esperava
          aparece depois da conferência.
        </p>
      </div>

      <div v-else class="rounded-lg bg-zinc-50 p-3">
        <p class="text-xs uppercase tracking-wide text-zinc-500">Esperado em dinheiro</p>
        <p class="text-xl font-bold text-zinc-900 tabular-nums">
          {{ formatarCentavos(esperado) }}
        </p>
      </div>

      <MoneyInput v-model="contadoEmReais" label="Dinheiro contado na gaveta" />
    </div>

    <!-- Depois de fechar: o espelho -->
    <div v-else class="space-y-3">
      <div class="grid grid-cols-2 gap-3">
        <div class="rounded-lg bg-zinc-50 p-3">
          <p class="text-xs uppercase tracking-wide text-zinc-500">Esperado</p>
          <p class="text-lg font-semibold tabular-nums">
            {{ formatarCentavos(resultado.saldo_esperado_dinheiro ?? 0) }}
          </p>
        </div>
        <div class="rounded-lg bg-zinc-50 p-3">
          <p class="text-xs uppercase tracking-wide text-zinc-500">Contado</p>
          <p class="text-lg font-semibold tabular-nums">
            {{ formatarCentavos(resultado.saldo_contado ?? 0) }}
          </p>
        </div>
      </div>

      <div
        class="rounded-lg p-3"
        :class="diferenca === 0 ? 'bg-emerald-50' : 'bg-amber-50'"
      >
        <p class="text-xs uppercase tracking-wide text-zinc-500">Diferença</p>
        <p
          class="text-xl font-bold tabular-nums"
          :class="diferenca === 0 ? 'text-emerald-700' : 'text-amber-700'"
        >
          {{ formatarCentavos(diferenca ?? 0) }}
        </p>
        <p v-if="(diferenca ?? 0) < 0" class="mt-1 text-xs text-amber-700">
          Falta dinheiro na gaveta.
        </p>
        <p v-else-if="(diferenca ?? 0) > 0" class="mt-1 text-xs text-amber-700">
          Sobrou dinheiro na gaveta.
        </p>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-end gap-2">
        <template v-if="!resultado">
          <BaseButton variant="secondary" @click="emit('close')">Cancelar</BaseButton>
          <BaseButton :disabled="fecharMutation.isPending.value" @click="confirmar">
            Fechar caixa
          </BaseButton>
        </template>
        <BaseButton v-else @click="emit('close')">Concluir</BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
