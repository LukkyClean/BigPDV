<script setup lang="ts">
import { ref, watch } from 'vue';
import { FileText, Unlock, Banknote, ArrowLeft } from 'lucide-vue-next';
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import { formatCurrency } from '@/shared/utils/finance';

interface Props {
  isOpen: boolean;
  /** True quando a OS tem valor já pago/registrado — aí perguntamos se o cliente pagou. */
  temPagamento?: boolean;
  /** Valor já pago (centavos), só para exibição na pergunta. */
  valorPago?: number;
}

const props = withDefaults(defineProps<Props>(), {
  temPagamento: false,
  valorPago: 0,
});

const emit = defineEmits<{
  cancel: [];
  textOnly: [];
  /** clientePagou: false quando o operador confirma que o cliente NÃO pagou o valor anterior. */
  full: [clientePagou: boolean];
}>();

// 'opcoes' = escolha texto/completa; 'pagamento' = pergunta "o cliente já pagou?"
const step = ref<'opcoes' | 'pagamento'>('opcoes');

// Sempre reinicia no passo de opções ao (re)abrir.
watch(() => props.isOpen, (open) => {
  if (open) step.value = 'opcoes';
});

function onFullClick() {
  // Só pergunta se há dinheiro em jogo; senão não há nada a preservar/apagar.
  if (props.temPagamento) {
    step.value = 'pagamento';
  } else {
    emit('full', true);
  }
}
</script>

<template>
  <BaseModal
    :is-open="isOpen"
    :title="step === 'pagamento' ? 'O cliente já pagou?' : 'Reabrir OS'"
    :subtitle="step === 'pagamento'
      ? 'Isso decide o que fazer com o valor da finalização anterior.'
      : 'Escolha o nível de edição necessário.'"
    size="sm"
    @close="emit('cancel')"
  >
    <!-- Passo 1: nível de edição -->
    <div v-if="step === 'opcoes'" class="flex flex-col gap-2">
      <button
        type="button"
        class="flex items-center gap-3 px-3 py-2.5 rounded-xl border-2 border-zinc-200 hover:border-brand-primary hover:bg-brand-primary-light transition-all text-left group cursor-pointer"
        @click="emit('textOnly')"
      >
        <div class="p-2 rounded-lg bg-zinc-100 group-hover:bg-brand-primary/10 shrink-0 transition-colors">
          <FileText :size="16" class="text-zinc-500 group-hover:text-brand-primary transition-colors" />
        </div>
        <div>
          <p class="text-sm font-semibold text-zinc-700 group-hover:text-brand-primary transition-colors">Ajustar Apenas Texto</p>
          <p class="text-xs text-zinc-400 leading-tight">Edite diagnóstico e observações. Financeiro travado.</p>
        </div>
      </button>

      <button
        type="button"
        class="flex items-center gap-3 px-3 py-2.5 rounded-xl border-2 border-zinc-200 hover:border-amber-400 hover:bg-amber-50 transition-all text-left group cursor-pointer"
        @click="onFullClick"
      >
        <div class="p-2 rounded-lg bg-zinc-100 group-hover:bg-amber-100 shrink-0 transition-colors">
          <Unlock :size="16" class="text-zinc-500 group-hover:text-amber-600 transition-colors" />
        </div>
        <div>
          <p class="text-sm font-semibold text-zinc-700 group-hover:text-amber-700 transition-colors">Reabertura Completa</p>
          <p class="text-xs text-zinc-400 leading-tight">Libera itens, valores e pagamentos. Requer nova finalização.</p>
        </div>
      </button>
    </div>

    <!-- Passo 2: o cliente já pagou o valor anterior? -->
    <div v-else class="flex flex-col gap-3">
      <div class="flex items-start gap-2 p-3 bg-zinc-50 border border-zinc-200 rounded-lg">
        <Banknote :size="16" class="text-zinc-400 shrink-0 mt-0.5" />
        <p class="text-xs text-zinc-600 leading-snug">
          Esta OS tem <strong class="text-zinc-800">{{ formatCurrency(valorPago) }}</strong> registrado como pago.
          O cliente realmente já pagou esse valor?
        </p>
      </div>

      <button
        type="button"
        class="flex flex-col items-start px-3 py-2.5 rounded-xl border-2 border-zinc-200 hover:border-emerald-400 hover:bg-emerald-50 transition-all text-left cursor-pointer"
        @click="emit('full', true)"
      >
        <p class="text-sm font-semibold text-zinc-700">Sim, já pagou</p>
        <p class="text-xs text-zinc-400 leading-tight">
          O valor vira crédito da OS e é abatido do novo total.
        </p>
      </button>

      <button
        type="button"
        class="flex flex-col items-start px-3 py-2.5 rounded-xl border-2 border-zinc-200 hover:border-amber-400 hover:bg-amber-50 transition-all text-left cursor-pointer"
        @click="emit('full', false)"
      >
        <p class="text-sm font-semibold text-zinc-700">Não pagou ainda</p>
        <p class="text-xs text-zinc-400 leading-tight">
          Apaga o pagamento registrado — a OS volta a cobrar o valor cheio.
        </p>
      </button>

      <button
        type="button"
        class="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-600 transition-colors self-start"
        @click="step = 'opcoes'"
      >
        <ArrowLeft :size="13" /> Voltar
      </button>
    </div>

    <template #footer>
      <div class="flex justify-end w-full">
        <BaseButton variant="secondary" class="px-5" @click="emit('cancel')">
          Cancelar
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
