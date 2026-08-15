<script setup lang="ts">
import { computed, ref } from 'vue';
import { ArrowDownCircle, ArrowUpCircle, Lock, Wallet } from 'lucide-vue-next';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';

import AbrirCaixaModal from './AbrirCaixaModal.vue';
import FecharCaixaModal from './FecharCaixaModal.vue';
import MovimentoCaixaModal from './MovimentoCaixaModal.vue';
import { useSessaoCaixaQuery } from '../composables/queries/useSessaoCaixaQuery';
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

const esperado = computed(() => sessao.value?.saldo_esperado_dinheiro ?? 0);
const operador = computed(() => sessao.value?.funcionario_nome ?? '');
const terminal = computed(() => sessao.value?.terminal_nome ?? '');

function abrirMovimento(tipo: 'sangria' | 'suprimento') {
  tipoMovimento.value = tipo;
  movimentoAberto.value = true;
}
</script>

<template>
  <div v-if="caixaHabilitado && !isLoading">
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
          <p class="text-sm text-zinc-600">
            Em dinheiro na gaveta:
            <strong class="tabular-nums">{{ formatarCentavos(esperado) }}</strong>
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
