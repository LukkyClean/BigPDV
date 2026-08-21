<script setup lang="ts">
import { computed, ref } from 'vue';
import { ArrowDownCircle, ArrowUpCircle, EyeOff, Lock, Wallet } from 'lucide-vue-next';

import { storeToRefs } from 'pinia';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import GerenteAprovacaoModal from '@/shared/components/commons/GerenteAprovacaoModal/GerenteAprovacaoModal.vue';
import { useGerenteAprovacao } from '@/shared/composables/useGerenteAprovacao';
import { useToast } from '@/shared/composables/useToast';
import { useAuthStore } from '@/shared/stores/auth.store';
import { useConfiguracoesStore } from '@/shared/stores/configuracoes.store';
import { verificarPinSeguranca } from '@/modules/configuracoes/services/configuracoes.service';

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
  exigeCaixaAberto,
  fechamentoCego,
  isLoading,
} = useSessaoCaixaQuery();

const abrirAberto = ref(false);
const fecharAberto = ref(false);
const pinAutorizado = ref<string | null>(null);

const gerente = useGerenteAprovacao();
const toast = useToast();
const { requerPinAbrirCaixa, temPinConfigurado, usarFilaDoCaixa } = storeToRefs(useConfiguracoesStore());
const { userData } = storeToRefs(useAuthStore());

/**
 * A autorização é pedida ANTES da tela do troco, e não depois de digitá-lo.
 *
 * A ordem importa no balcão: quem libera é o supervisor, quem conta a gaveta é
 * o operador. Pedir o PIN só na confirmação faria o operador digitar o troco,
 * ser recusado e só então chamar alguém — com a fila esperando e o valor já na
 * tela. Aqui o supervisor libera, vai embora, e o operador termina sozinho.
 *
 * Só o master dispensa, exatamente como o backend (`_validar_autorizacao_abertura`).
 * Este `computed` é conveniência de tela: quem realmente recusa é o servidor, e
 * o `AbrirCaixaModal` mantém o tratamento das sentinelas para o caso de o PIN
 * mudar entre um passo e outro.
 */
const isMaster = computed(() => userData.value?.is_master === true);
const precisaAutorizacao = computed(() => requerPinAbrirCaixa.value && !isMaster.value);

/** Valida o PIN na hora; PIN errado pergunta de novo em vez de desistir. */
async function autorizarComRetry(pin: string): Promise<string | null> {
  try {
    gerente.isLoading.value = true;
    await verificarPinSeguranca(pin);
    return pin;
  } catch (error: any) {
    if (error?.response?.data?.detail === 'PIN_GERENTE_INVALIDO') {
      toast.error('PIN do gerente inválido. Tente novamente.');
      const novoPin = await gerente.pedirPin();
      if (novoPin) return autorizarComRetry(novoPin);
    } else {
      toast.error('Não foi possível verificar o PIN do gerente.');
    }
    return null;
  } finally {
    gerente.isLoading.value = false;
  }
}

async function pedirAberturaDeCaixa() {
  pinAutorizado.value = null;

  if (!precisaAutorizacao.value) {
    abrirAberto.value = true;
    return;
  }

  // Trava ligada e nenhum PIN cadastrado: pedir a senha aqui daria "PIN
  // inválido" para sempre, porque é isso que o `verificar-pin` responde quando
  // não há PIN. O backend tem a mensagem certa para esse caso, mas ela só
  // apareceria depois do troco digitado — e sem caixa aberto a loja não vende.
  // Dizer aqui onde resolver é o único desfecho que não deixa ninguém preso.
  if (!temPinConfigurado.value) {
    toast.error(
      'Nenhum PIN de gerente cadastrado',
      'Cadastre em Configurações > Segurança para liberar a abertura do caixa.',
    );
    return;
  }

  const pin = await gerente.pedirPin();
  if (!pin) return;

  const autorizado = await autorizarComRetry(pin);
  if (!autorizado) return;

  // O PIN viaja junto na abertura: o backend confere de novo, e é ele quem
  // manda. Guardar aqui só evita pedir a mesma senha duas vezes seguidas.
  pinAutorizado.value = autorizado;
  abrirAberto.value = true;
}

function fecharAberturaDeCaixa() {
  abrirAberto.value = false;
  // O PIN não sobrevive ao modal: a próxima abertura pede autorização de novo.
  pinAutorizado.value = null;
}
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
  <!--
    Retaguarda sem turno: uma linha, sem botão.
    O convite "Abrir caixa" continua escondido aqui — a máquina do escritório não
    é um caixa, e convidá-la criava a sessão fantasma que nunca fecha direito.
    Mas ficar em branco não serve desde que a venda passou a nascer sem turno: o
    operador montaria o carrinho e levaria "Abra o caixa antes de finalizar
    vendas", conselho impossível de seguir numa máquina que não abre caixa.

    SÃO DOIS RECADOS DIFERENTES, e confundi-los foi o que criou um beco.
    Com a fila ligada, a venda tem para onde ir e a linha só informa isso. Sem a
    fila, esta máquina monta vendas que NÃO CONSEGUE FINALIZAR — e aí a linha
    precisa dizer o problema e os dois jeitos de sair dele, senão o operador
    descobre no checkout, com o cliente esperando, e sem saída nenhuma.
  -->
  <div
    v-if="caixaHabilitado && !isLoading && eRetaguarda && !caixaAberto && exigeCaixaAberto"
    :class="[
      'flex items-start gap-2.5 rounded-xl border px-4 py-2.5 text-sm',
      usarFilaDoCaixa
        ? 'border-zinc-200 bg-zinc-50 text-zinc-500'
        : 'border-amber-200 bg-amber-50 text-amber-800',
    ]"
  >
    <Lock class="h-4 w-4 shrink-0 mt-0.5" />
    <span v-if="usarFilaDoCaixa">
      Esta máquina é retaguarda — as vendas montadas aqui são finalizadas no caixa.
    </span>
    <span v-else>
      Esta máquina é retaguarda e não abre caixa, mas a loja exige caixa aberto para
      finalizar — então vendas montadas aqui não podem ser concluídas.
      Ligue a <strong class="font-semibold">Fila do caixa</strong> em Configurações →
      Regras de Vendas, ou mude o papel desta máquina para
      <strong class="font-semibold">PDV</strong> em Configurações → Terminais.
    </span>
  </div>

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
          <!--
            A frase muda com `exigir_caixa_aberto` porque a consequência muda.
            Desde 21/08/2026 a venda NASCE sem turno aberto — só o dinheiro é
            barrado. Dizer só "abra o caixa para começar o turno" deixaria quem
            trabalha sozinho montar o carrinho inteiro e descobrir a trava no
            checkout, com o cliente na frente. Era exatamente esse atrito que a
            antiga trava na criação evitava, e é ele que esta linha substitui.
          -->
          <p v-if="exigeCaixaAberto" class="text-sm text-zinc-500">
            Você pode montar vendas, mas
            <strong class="font-semibold text-zinc-700">não finalizá-las</strong>
            enquanto o caixa estiver fechado.
          </p>
          <p v-else class="text-sm text-zinc-500">
            Abra o caixa informando o troco inicial para começar o turno.
          </p>
        </div>
      </div>
      <BaseButton variant="primary" size="md" @click="pedirAberturaDeCaixa">
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

    <GerenteAprovacaoModal
      :is-open="gerente.isOpen.value"
      :is-loading="gerente.isLoading.value"
      motivo="Abertura de caixa"
      descricao="Esta loja exige autorização para abrir o caixa. Um supervisor precisa
                 informar o PIN do gerente para liberar o início do turno."
      @confirmar="gerente.confirmar"
      @cancelar="gerente.cancelar"
    />

    <AbrirCaixaModal
      :is-open="abrirAberto"
      :codigo-gerente="pinAutorizado"
      @close="fecharAberturaDeCaixa"
    />
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
