<script setup lang="ts">
/**
 * "Quanto você tem hoje?" — a única pergunta que o sistema não sabe responder
 * sozinho.
 *
 * O livro do dinheiro só recebe venda e OS onde `controlar_caixa` está ligado,
 * então calcular o saldo daria um número falso na loja que não usa caixa. Aqui
 * o dono declara, conta por conta, e o servidor carimba a data — é o que
 * permite a tela avisar depois que o retrato envelheceu.
 *
 * Uma conta por linha, e não um campo só com o total: a projeção soma as
 * contas ATIVAS, e o dono precisa enxergar de onde cada pedaço veio para
 * corrigir a que estiver errada.
 */
import { ref, watch } from 'vue';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseMoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';
import { formatDataPura } from '@/shared/utils/date.utils';

import {
  useAtualizarContaBancaria,
  useContasBancariasQuery,
} from '../../shared/composables/useFinanceiro';

const props = defineProps<{ aberto: boolean }>();
const emit = defineEmits<{ fechar: [] }>();

const { data: contas } = useContasBancariasQuery();
const atualizar = useAtualizarContaBancaria();

// Chaveado por id: o v-model de cada linha precisa de um lugar próprio, e o
// índice do array não serve — a lista pode chegar depois de o modal abrir.
const valores = ref<Record<number, number>>({});

function recarregar() {
  const mapa: Record<number, number> = {};
  for (const conta of contas.value ?? []) mapa[conta.id] = (conta.saldo_informado ?? 0) / 100;
  valores.value = mapa;
}

watch(() => [props.aberto, contas.value] as const, recarregar, { immediate: true });

async function salvar() {
  // Só manda o que MUDOU. Sem isso, abrir e fechar o modal recarimbaria a data
  // de todas as contas, e o aviso de "informado há N dias" nunca apareceria —
  // o número ficaria velho fingindo ser novo.
  const alteradas = (contas.value ?? []).filter(
    (conta) => Math.round((valores.value[conta.id] ?? 0) * 100) !== (conta.saldo_informado ?? 0),
  );

  for (const conta of alteradas) {
    await atualizar.mutateAsync({
      id: conta.id,
      saldo_informado: Math.round((valores.value[conta.id] ?? 0) * 100),
    });
  }
  emit('fechar');
}
</script>

<template>
  <BaseModal :is-open="aberto" title="Saldo de hoje" size="sm" overlay @close="emit('fechar')">
    <div class="flex flex-col gap-4">
      <p class="text-sm text-gray-500">
        Informe quanto há em cada conta <strong>agora</strong>. É daqui que a projeção parte —
        o sistema não tem como saber esse número sozinho.
      </p>

      <div v-for="conta in contas ?? []" :key="conta.id" class="flex flex-col gap-1">
        <BaseMoneyInput v-model="valores[conta.id]" :label="conta.nome" />
        <p class="text-xs text-gray-400">
          <template v-if="conta.saldo_informado_em">
            Informado em {{ formatDataPura(conta.saldo_informado_em) }}
          </template>
          <template v-else>Nunca informado</template>
        </p>
      </div>

      <p class="rounded-xl bg-gray-50 px-3.5 py-2.5 text-xs text-gray-500">
        O saldo não anda sozinho: ele não muda quando você dá baixa numa conta. Volte aqui e
        atualize sempre que quiser conferir a projeção com a realidade.
      </p>
    </div>

    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <BaseButton variant="secondary" class="px-5" @click="emit('fechar')">Cancelar</BaseButton>
        <BaseButton
          variant="primary"
          class="px-5"
          :is-loading="atualizar.isPending.value"
          @click="salvar"
        >
          Salvar saldo
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
