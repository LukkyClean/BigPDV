<script setup lang="ts">
import { nextTick, ref, watch } from 'vue';
import { Wallet } from 'lucide-vue-next';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import MoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';

import GerenteAprovacaoModal from '@/shared/components/commons/GerenteAprovacaoModal/GerenteAprovacaoModal.vue';
import { useGerenteAprovacao } from '@/shared/composables/useGerenteAprovacao';
import { useToast } from '@/shared/composables/useToast';

import { useAbrirCaixaMutation } from '../composables/mutates/useCaixaMutations';
import { obterHwid } from '@/shared/services/system/hwid.service';

const props = defineProps<{
  isOpen: boolean;
  /**
   * PIN já autorizado pela `CaixaBar`, quando a loja exige liberação.
   *
   * A autorização acontece ANTES desta tela para o supervisor não precisar
   * esperar o operador contar a gaveta. Aqui ele só viaja junto no payload — o
   * backend confere de novo, e é ele quem manda.
   */
  codigoGerente?: string | null;
}>();
const emit = defineEmits<{ (e: 'close'): void; (e: 'success'): void }>();

const trocoEmReais = ref(0);
const trocoRef = ref();
const abrirMutation = useAbrirCaixaMutation();
const gerente = useGerenteAprovacao();
const toast = useToast();

// Limpa ao reabrir: um valor herdado da abertura anterior seria confirmado sem
// ninguém reparar, e o troco errado contamina o fechamento do dia inteiro.
/**
 * O cursor nasce no troco, e o Enter confirma.
 *
 * Abrir o caixa é o primeiro ato do turno, com fila já se formando. Sem isto o
 * operador precisava clicar no campo para digitar e clicar no botão para
 * confirmar — dois desvios para o mouse numa tela de dois controles.
 *
 * `select()` e não só `focus()`: o campo nasce em R$ 0,00, e digitar por cima
 * de um valor selecionado é o que a mão espera. É o mesmo que o sub-modal de
 * pagamento da venda já faz.
 *
 * Duas tentativas porque o `BaseModal` monta dentro de um `<Transition>`: o
 * primeiro `focus()` pode acontecer antes de o campo existir de verdade.
 */
watch(
  () => props.isOpen,
  (aberto) => {
    if (!aberto) return;
    trocoEmReais.value = 0;

    const tentar = () => {
      const input = trocoRef.value?.inputRef;
      if (!input) return false;
      input.focus();
      input.select();
      return document.activeElement === input;
    };

    nextTick(() => {
      if (tentar()) return;
      requestAnimationFrame(() => void tentar());
    });
  },
);

/**
 * REDE DE SEGURANÇA, não o caminho normal.
 *
 * Quando a loja exige liberação, quem pede o PIN é a `CaixaBar`, antes desta
 * tela abrir. O tratamento das sentinelas fica aqui para os casos em que aquela
 * autorização não vale mais no momento do envio — o PIN mudou entre um passo e
 * outro, ou alguém abriu este modal por outro caminho. O backend é a autoridade;
 * a tela nunca decide sozinha que pode dispensar.
 *
 * A recursão é de um nível só na prática: o PIN errado devolve a mesma
 * sentinela e volta a pedir, e cancelar (`pin` nulo) encerra sem repetir.
 *
 * Os outros erros — terminal ocupado, operador que já tem caixa aberto — caem
 * no `else` e sobem, para a mutation mostrar o toast de sempre. Engoli-los aqui
 * faria a abertura falhar em silêncio.
 */
async function abrir(codigoGerente?: string) {
  // O HWID identifica a máquina e é o que permite dois caixas ao mesmo tempo.
  // Se não vier, o backend trata como loja de um PC só — que é o caso da
  // maioria — em vez de recusar a abertura.
  let terminal_hwid: string | null = null;
  try {
    terminal_hwid = await obterHwid();
  } catch {
    terminal_hwid = null;
  }

  try {
    gerente.isLoading.value = true;
    await abrirMutation.mutateAsync({
      saldo_inicial: Math.round((trocoEmReais.value || 0) * 100),
      terminal_hwid,
      // O da retentativa vence o da prop: se o backend recusou o que veio da
      // barra (PIN trocado entre um passo e outro), quem vale é o que o
      // supervisor acabou de digitar aqui.
      codigo_gerente: codigoGerente ?? props.codigoGerente ?? null,
    });
    emit('success');
    emit('close');
  } catch (error: any) {
    const detail = error?.response?.data?.detail;
    if (detail === 'REQUER_APROVACAO_GERENTE') {
      const pin = await gerente.pedirPin();
      if (pin) await abrir(pin);
    } else if (detail === 'PIN_GERENTE_INVALIDO') {
      toast.error('PIN do gerente inválido');
      const pin = await gerente.pedirPin();
      if (pin) await abrir(pin);
    } else {
      throw error;
    }
  } finally {
    gerente.isLoading.value = false;
  }
}

function confirmar() {
  abrir();
}
</script>

<template>
  <GerenteAprovacaoModal
    :is-open="gerente.isOpen.value"
    :is-loading="gerente.isLoading.value"
    motivo="Abertura de caixa"
    descricao="Esta loja exige autorização para abrir o caixa. Um supervisor precisa
               informar o PIN do gerente para liberar o início do turno."
    @confirmar="gerente.confirmar"
    @cancelar="gerente.cancelar"
  />

  <BaseModal :is-open="props.isOpen" title="Abrir caixa" @close="emit('close')">
    <div class="space-y-4">
      <div class="flex items-start gap-3 rounded-lg bg-zinc-50 p-3">
        <Wallet class="h-5 w-5 shrink-0 text-zinc-500" />
        <p class="text-sm text-zinc-600">
          Informe o dinheiro que está na gaveta agora, para troco. Ele entra no
          caixa como abertura e é considerado no fechamento.
        </p>
      </div>

      <MoneyInput ref="trocoRef" v-model="trocoEmReais" label="Troco inicial" @enter="confirmar" />
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
