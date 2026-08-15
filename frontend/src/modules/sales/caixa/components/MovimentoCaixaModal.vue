<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ArrowDownCircle, ArrowUpCircle } from 'lucide-vue-next';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import MoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';
import GerenteAprovacaoModal from '@/shared/components/commons/GerenteAprovacaoModal/GerenteAprovacaoModal.vue';

import { useGerenteAprovacao } from '@/shared/composables/useGerenteAprovacao';
import { useToast } from '@/shared/composables/useToast';
import { useSangriaMutation, useSuprimentoMutation } from '../composables/mutates/useCaixaMutations';

const MIN_MOTIVO = 3;

const props = defineProps<{
  isOpen: boolean;
  /** 'sangria' tira dinheiro da gaveta; 'suprimento' põe. */
  tipo: 'sangria' | 'suprimento';
}>();

const emit = defineEmits<{ (e: 'close'): void; (e: 'success'): void }>();

const valorEmReais = ref(0);
const motivo = ref('');
const tocado = ref(false);

const sangriaMutation = useSangriaMutation();
const suprimentoMutation = useSuprimentoMutation();
const gerente = useGerenteAprovacao();
const toast = useToast();

const ehSangria = computed(() => props.tipo === 'sangria');
const titulo = computed(() => (ehSangria.value ? 'Sangria' : 'Suprimento'));
const explicacao = computed(() =>
  ehSangria.value
    ? 'Retirada de dinheiro da gaveta que não é venda — levar ao cofre, pagar um fornecedor na porta.'
    : 'Entrada de dinheiro na gaveta que não é venda — reforço de troco, por exemplo.',
);

const motivoLimpo = computed(() => motivo.value.trim());
const valido = computed(
  () => motivoLimpo.value.length >= MIN_MOTIVO && (valorEmReais.value || 0) > 0,
);
const mostrarErro = computed(() => tocado.value && !valido.value);

watch(
  () => props.isOpen,
  (aberto) => {
    if (aberto) {
      valorEmReais.value = 0;
      motivo.value = '';
      tocado.value = false;
    }
  },
);

async function executar(codigoGerente?: string) {
  const payload = {
    valor: Math.round((valorEmReais.value || 0) * 100),
    motivo: motivoLimpo.value,
    codigo_gerente: codigoGerente ?? null,
  };

  try {
    gerente.isLoading.value = true;
    if (ehSangria.value) {
      await sangriaMutation.mutateAsync(payload);
    } else {
      await suprimentoMutation.mutateAsync(payload);
    }
    emit('success');
    emit('close');
  } catch (error: any) {
    // Mesmo contrato de cancelamento/desconto: o backend devolve sentinelas e o
    // modal de PIN é reaproveitado inteiro.
    const detail = error?.response?.data?.detail;
    if (detail === 'REQUER_APROVACAO_GERENTE') {
      const pin = await gerente.pedirPin();
      if (pin) await executar(pin);
    } else if (detail === 'PIN_GERENTE_INVALIDO') {
      toast.error('PIN do gerente inválido');
      const pin = await gerente.pedirPin();
      if (pin) await executar(pin);
    }
  } finally {
    gerente.isLoading.value = false;
  }
}

function confirmar() {
  tocado.value = true;
  if (!valido.value) return;
  executar();
}
</script>

<template>
  <GerenteAprovacaoModal
    :is-open="gerente.isOpen.value"
    :is-loading="gerente.isLoading.value"
    @confirmar="gerente.confirmar"
    @cancelar="gerente.cancelar"
  />

  <BaseModal :is-open="props.isOpen" :title="titulo" @close="emit('close')">
    <div class="space-y-4">
      <div class="flex items-start gap-3 rounded-lg bg-zinc-50 p-3">
        <ArrowDownCircle v-if="ehSangria" class="h-5 w-5 shrink-0 text-amber-600" />
        <ArrowUpCircle v-else class="h-5 w-5 shrink-0 text-emerald-600" />
        <p class="text-sm text-zinc-600">{{ explicacao }}</p>
      </div>

      <MoneyInput v-model="valorEmReais" label="Valor" />

      <BaseInput
        v-model="motivo"
        label="Motivo"
        placeholder="Ex: envio ao cofre"
        :error="mostrarErro ? 'Informe o valor e um motivo com pelo menos 3 letras.' : ''"
      />
    </div>

    <template #footer>
      <div class="flex justify-end gap-2">
        <BaseButton variant="secondary" @click="emit('close')">Cancelar</BaseButton>
        <BaseButton @click="confirmar">Confirmar {{ titulo.toLowerCase() }}</BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
