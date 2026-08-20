<script setup lang="ts">
import { computed, ref } from 'vue';
import { ArrowDownCircle, ArrowUpCircle, EyeOff, Lock, Wallet } from 'lucide-vue-next';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';

import AbrirCaixaModal from './AbrirCaixaModal.vue';
import FecharCaixaModal from './FecharCaixaModal.vue';
import MovimentoCaixaModal from './MovimentoCaixaModal.vue';
import { useSessaoCaixaQuery } from '../composables/queries/useSessaoCaixaQuery';
import { useEsteTerminalQuery } from '../composables/queries/useTerminaisQuery';
import { formatarCentavos } from '../caixa.utils';

/**
 * A barra do caixa dentro do PDV.
 *
 * NÃO RENDERIZA NADA quando `controlar_caixa` está desligado — e é assim que a
 * tela de vendas continua idêntica para as lojas que não usam caixa. O `v-if`
 * mais externo é a única coisa que separa este subdomínio inteiro delas.
 *
 * Vive aqui dentro, e não num item de menu, porque o operador já está na tela de
 * venda com fila na frente: mandá-lo navegar para sangrar é atrito puro.
 */

const {
  sessao,
  caixaAberto,
  caixaHabilitado,
  fechamentoCego,
  isLoading,
} = useSessaoCaixaQuery();

const abrirAberto = ref(false);
const fecharAberto = ref(false);
const movimentoAberto = ref(false);
const tipoMovimento = ref<'sangria' | 'suprimento'>('sangria');

/**
 * O dinheiro esperado na gaveta — ou `null` quando o fechamento cego o esconde.
 *
 * A distinção é o ponto. Enquanto isto era `?? 0`, uma loja com fechamento cego
 * ligado via a barra anunciar "Em dinheiro na gaveta: R$ 0,00" o dia inteiro,
 * com a gaveta cheia e as vendas todas registradas. O operador não conclui
 * "está oculto": conclui que o sistema não está somando as vendas dele.
 */
const esperado = computed(() => sessao.value?.saldo_esperado_dinheiro ?? null);
const operador = computed(() => sessao.value?.funcionario_nome ?? '');
const terminal = computed(() => sessao.value?.terminal_nome ?? '');

function abrirMovimento(tipo: 'sangria' | 'suprimento') {
  tipoMovimento.value = tipo;
  movimentoAberto.value = true;
}

/**
 * A máquina da retaguarda não é um caixa, e não deve ser convidada a virar um.
 *
 * O computador do escritório existe para consultar relatório. Enquanto ele
 * recebia o convite "Caixa fechado — abrir caixa", o caminho fácil era o dono
 * abrir um turno ali só para tirar o aviso da frente — e aí passava a existir
 * uma sessão que nunca é fechada direito, com saldo que ninguém conta.
 *
 * `e_retaguarda` só é verdadeiro com o papel RETAGUARDA explícito: máquina
 * desconhecida, HWID indisponível ou consulta que falhou resultam em `false`, e
 * o convite continua aparecendo. Errar para "convida demais" custa um aviso na
 * tela; errar para o outro lado esconde o caixa de um caixa de verdade.
 */
const { eRetaguarda } = useEsteTerminalQuery();
</script>

<template>
  <div v-if="caixaHabilitado && !isLoading && !(eRetaguarda && !caixaAberto)">
    <!-- Caixa fechado: só o convite para abrir -->
    <div
      v-if="!caixaAberto"
      class="flex flex-col gap-3 rounded-xl border border-zinc-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <div class="flex items-center gap-3">
        <span class="rounded-lg bg-zinc-100 p-2">
          <Lock class="h-5 w-5 text-zinc-500" />
        </span>
        <div>
          <p class="font-semibold text-zinc-900">Caixa fechado</p>
          <p class="text-sm text-zinc-500">
            Abra o caixa informando o troco inicial para começar o turno.
          </p>
        </div>
      </div>
      <BaseButton variant="primary" size="md" @click="abrirAberto = true">
        Abrir caixa
      </BaseButton>
    </div>

    <!-- Caixa aberto: o estado da gaveta e as ações do turno -->
    <div
      v-else
      class="flex flex-col gap-4 rounded-xl border border-emerald-200 bg-emerald-50/50 p-4 lg:flex-row lg:items-center lg:justify-between"
    >
      <div class="flex items-center gap-3">
        <span class="rounded-lg bg-emerald-100 p-2">
          <Wallet class="h-5 w-5 text-emerald-700" />
        </span>
        <div>
          <p class="font-semibold text-zinc-900">
            Caixa aberto
            <span v-if="operador" class="font-normal text-zinc-500">· {{ operador }}</span>
            <span v-if="terminal" class="font-normal text-zinc-500">· {{ terminal }}</span>
          </p>
          <p v-if="esperado !== null" class="text-sm text-zinc-600">
            Em dinheiro na gaveta:
            <strong class="tabular-nums">{{ formatarCentavos(esperado) }}</strong>
          </p>
          <p v-else class="flex items-center gap-1.5 text-sm text-zinc-500">
            <EyeOff class="h-4 w-4 shrink-0" />
            Conferência cega — o valor aparece no fechamento
          </p>
        </div>
      </div>

      <div class="flex flex-wrap gap-2">
        <BaseButton variant="secondary" size="md" class="flex gap-1"
                    @click="abrirMovimento('suprimento')">
          <ArrowUpCircle :size="18" />
          Suprimento
        </BaseButton>
        <BaseButton variant="secondary" size="md" class="flex gap-1"
                    @click="abrirMovimento('sangria')">
          <ArrowDownCircle :size="18" />
          Sangria
        </BaseButton>
        <BaseButton variant="primary" size="md" @click="fecharAberto = true">
          Fechar caixa
        </BaseButton>
      </div>
    </div>

    <AbrirCaixaModal :is-open="abrirAberto" @close="abrirAberto = false" />
    <MovimentoCaixaModal
      :is-open="movimentoAberto"
      :tipo="tipoMovimento"
      @close="movimentoAberto = false"
    />
    <FecharCaixaModal
      :is-open="fecharAberto"
      :sessao="sessao"
      :cego="fechamentoCego"
      @close="fecharAberto = false"
    />
  </div>
</template>
