<script setup lang="ts">
import { ref, watch } from 'vue';
import { Wallet } from 'lucide-vue-next';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import MoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';

import { useAbrirCaixaMutation } from '../composables/mutates/useCaixaMutations';
import { obterHwid } from '@/shared/services/system/hwid.service';

const props = defineProps<{ isOpen: boolean }>();
const emit = defineEmits<{ (e: 'close'): void; (e: 'success'): void }>();

const trocoEmReais = ref(0);
const abrirMutation = useAbrirCaixaMutation();

// Limpa ao reabrir: um valor herdado da abertura anterior seria confirmado sem
// ninguém reparar, e o troco errado contamina o fechamento do dia inteiro.
watch(
  () => props.isOpen,
  (aberto) => {
    if (aberto) trocoEmReais.value = 0;
  },
);

async function confirmar() {
  // O HWID identifica a máquina e é o que permite dois caixas ao mesmo tempo.
  // Se não vier, o backend trata como loja de um PC só — que é o caso da
  // maioria — em vez de recusar a abertura.
  let terminal_hwid: string | null = null;
  try {
    terminal_hwid = await obterHwid();
  } catch {
    terminal_hwid = null;
  }

  await abrirMutation.mutateAsync({
    saldo_inicial: Math.round((trocoEmReais.value || 0) * 100),
    terminal_hwid,
  });
  emit('success');
  emit('close');
}
</script>

<template>
  <BaseModal :is-open="props.isOpen" title="Abrir caixa" @close="emit('close')">
    <div class="space-y-4">
      <div class="flex items-start gap-3 rounded-lg bg-zinc-50 p-3">
        <Wallet class="h-5 w-5 shrink-0 text-zinc-500" />
        <p class="text-sm text-zinc-600">
          Informe o dinheiro que está na gaveta agora, para troco. Ele entra no
          caixa como abertura e é considerado no fechamento.
        </p>
      </div>

      <MoneyInput v-model="trocoEmReais" label="Troco inicial" />
    </div>

    <template #footer>
      <div class="flex justify-end gap-2">
        <BaseButton variant="secondary" @click="emit('close')">Cancelar</BaseButton>
        <BaseButton :disabled="abrirMutation.isPending.value" @click="confirmar">
          Abrir caixa
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
