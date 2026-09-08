<script setup lang="ts">
/**
 * "Quanto você tem hoje?" — o PONTO DE PARTIDA, não o saldo.
 *
 * O sistema sabe tudo que entrou e saiu desde que começou a ser usado, mas não
 * sabe o que já havia na gaveta antes disso. Essa é a única coisa que se
 * pergunta ao dono — e uma vez só: dali em diante cada venda, OS e conta paga
 * entra no saldo sozinha. É o mesmo desenho do "saldo inicial" do Conta Azul e
 * do Omie.
 *
 * O servidor carimba a data E o instante da declaração. O instante é o que
 * impede a venda da manhã de ser contada duas vezes quando o dono confere a
 * gaveta à tarde: ela já está dentro do número que ele acabou de contar.
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
      <p class="text-sm text-zinc-500">
        Informe quanto há em cada conta <strong>agora</strong>. É o ponto de partida: o
        sistema não sabe o que já havia aí antes de ele existir.
      </p>

      <div v-for="conta in contas ?? []" :key="conta.id" class="flex flex-col gap-1">
        <BaseMoneyInput v-model="valores[conta.id]" :label="conta.nome" />
        <p class="text-xs text-zinc-400">
          <template v-if="conta.saldo_informado_em">
            Informado em {{ formatDataPura(conta.saldo_informado_em) }}
          </template>
          <template v-else>Nunca informado</template>
        </p>
      </div>

      <p class="rounded-xl bg-zinc-50 px-3.5 py-2.5 text-xs text-zinc-500">
        Daqui em diante o saldo anda sozinho: cada venda, OS e conta paga entra nele. Você só
        precisa voltar aqui se conferir a gaveta e o número não bater — aí o que você digitar
        vira o novo ponto de partida.
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
