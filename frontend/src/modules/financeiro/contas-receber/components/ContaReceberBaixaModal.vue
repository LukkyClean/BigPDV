<script setup lang="ts">
/**
 * O recebimento: a promessa vira dinheiro e o livro registra a entrada.
 *
 * É o momento que o fecho da venda já deixava marcado no código — "o movimento
 * nasce no dia em que o cliente pagar".
 */
import { computed, ref, watch } from 'vue';
import { Banknote, CreditCard, FileText, Plus, QrCode, Wallet } from 'lucide-vue-next';

import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseMoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import { useToast } from '@/shared/composables/useToast';
import { formatCurrency } from '@/shared/utils/finance';
import { formatDataPura } from '@/shared/utils/date.utils';

import { usePaymentMethodsQuery } from '@/modules/sales/composables/queries/usePaymentMethodsQuery';

import {
  useContasBancariasQuery,
  useCriarContaBancaria,
  useReceberConta,
} from '../../shared/composables/useFinanceiro';
import type { ContaReceber } from '../../shared/schemas/financeiro.schema';

const props = defineProps<{ conta: ContaReceber | null }>();
const emit = defineEmits<{ fechar: [] }>();

const toast = useToast();
const { data: contasBancarias } = useContasBancariasQuery();
const receber = useReceberConta();
const criarConta = useCriarContaBancaria();

// O catálogo é o mesmo do PDV e da OS: reusar em vez de duplicar é o que
// garante que a forma escolhida aqui seja a mesma que aparece no relatório.
const { formasPagamento } = usePaymentMethodsQuery();

const valorReais = ref(0);
const jurosReais = ref(0);

/**
 * Para ONDE vai o juros — e é a diferença entre registrar dinheiro que existe e
 * dinheiro que não existe.
 *
 * LOJA é multa por atraso: receita dela, entra no caixa com o principal.
 * OPERADORA é o juros do parcelamento na maquininha: o cliente desembolsa, mas
 * esse pedaço nunca chega na loja. Lançá-lo como entrada mostraria saldo que a
 * conta bancária não tem, e o caixa fecharia com sobra em todo parcelamento.
 */
const jurosDestino = ref<'LOJA' | 'OPERADORA'>('LOJA');
const recebidoEm = ref('');
const contaBancariaId = ref<string | number>('');
const formaPagamentoId = ref<string | number>('');

function hojeLocal(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

watch(
  () => props.conta,
  (conta) => {
    if (!conta) return;
    valorReais.value = conta.valor / 100;
    jurosReais.value = 0;
    jurosDestino.value = 'LOJA';
    formaPagamentoId.value = '';
    recebidoEm.value = hojeLocal();
    contaBancariaId.value = contasBancarias.value?.find((c) => c.principal)?.id ?? '';
  },
  { immediate: true },
);

watch(contasBancarias, (lista) => {
  if (!contaBancariaId.value && lista?.length) {
    contaBancariaId.value = lista.find((c) => c.principal)?.id ?? lista[0].id;
  }
});

const opcoesContas = computed(() =>
  (contasBancarias.value ?? []).map((c) => ({ value: c.id, label: c.nome })),
);

const formasAtivas = computed(() => formasPagamento.value.filter((f) => f.ativo));

/**
 * Mesmos ícones do PDV e da OS, de propósito.
 *
 * O operador já reconhece esse grid dos outros dois lugares onde recebe
 * dinheiro; obrigá-lo a aprender um seletor diferente só porque a tela é do
 * financeiro seria atrito sem motivo.
 *
 * O que NÃO se reusa é a `OSPagamentoModal` inteira: ela exige `ordemServico`,
 * `dadosOs` e `descontoOs`, e é construída em torno de "vários pagamentos que
 * precisam somar o total da OS". Um recebimento é um pagamento só.
 */
function iconeDaForma(forma: { tipo?: string | null; nome: string }) {
  switch (forma.tipo ?? forma.nome.toUpperCase()) {
    case 'PIX': return QrCode;
    case 'CARTAO_CREDITO': return CreditCard;
    case 'CARTAO_DEBITO': return Wallet;
    case 'BOLETO': return FileText;
    default: return Banknote;
  }
}

/**
 * O total sobe sozinho quando há juros.
 *
 * Quem cobrou multa quer receber principal + multa, e obrigar a somar de cabeça
 * no balcão convida ao erro. O campo continua editável para o recebimento
 * PARCIAL -- o cliente que devia 200 e trouxe 150.
 */
watch(jurosReais, (juros, anterior) => {
  if (!props.conta) return;
  const esperadoAntes = props.conta.valor / 100 + (anterior ?? 0);
  // Só reajusta se o operador não tinha mexido no total à mão.
  if (Math.abs(valorReais.value - esperadoAntes) < 0.005) {
    valorReais.value = props.conta.valor / 100 + juros;
  }
});

/**
 * Cadastro de conta SEM sair do recebimento.
 *
 * A conta que falta só se descobre aqui, no meio do fluxo -- e é por isso que o
 * cadastro mora aqui, e não numa tela à parte: mandar o operador sair e voltar
 * perderia o que ele estava fazendo, que é o atrito que faz o módulo ser
 * abandonado.
 */
const cadastrandoConta = ref(false);
const nomeNovaConta = ref('');
const tipoNovaConta = ref('BANCO');

function salvarNovaConta() {
  const nome = nomeNovaConta.value.trim();
  if (!nome) return;
  criarConta.mutate(
    { nome, tipo: tipoNovaConta.value },
    {
      onSuccess: (conta) => {
        // Já deixa selecionada: quem acabou de cadastrar quer usar agora.
        contaBancariaId.value = conta.id;
        cadastrandoConta.value = false;
        nomeNovaConta.value = '';
      },
      onError: (e: any) =>
        toast.error(e?.response?.data?.detail ?? 'Não foi possível cadastrar a conta'),
    },
  );
}

/** O que de fato entra na loja: sem o juros quando ele é da operadora. */
const entraNaLoja = computed(() => {
  const total = Math.round(valorReais.value * 100);
  return jurosDestino.value === 'OPERADORA'
    ? total - Math.round(jurosReais.value * 100)
    : total;
});

/**
 * Quanto falta (ou sobra) sobre o que era ESPERADO — principal mais juros.
 *
 * Comparar com o principal puro faria o juros aparecer duas vezes: uma no campo
 * dele e outra como "entrou a mais". O que interessa aqui é o outro caso: o
 * cliente devia R$ 200 e trouxe R$ 150.
 */
const diferenca = computed(() => {
  if (!props.conta) return 0;
  const esperado = props.conta.valor + Math.round(jurosReais.value * 100);
  return Math.round(valorReais.value * 100) - esperado;
});

function confirmar() {
  if (!props.conta || valorReais.value <= 0) return;
  receber.mutate(
    {
      id: props.conta.id,
      payload: {
        valor_recebido: Math.round(valorReais.value * 100),
        juros: Math.round(jurosReais.value * 100),
        juros_destino: jurosDestino.value,
        recebido_em: recebidoEm.value,
        conta_bancaria_id: contaBancariaId.value === '' ? null : Number(contaBancariaId.value),
        forma_pagamento_id: formaPagamentoId.value === '' ? null : Number(formaPagamentoId.value),
      },
    },
    {
      onSuccess: () => emit('fechar'),
      onError: (e: any) =>
        toast.error(e?.response?.data?.detail ?? 'Não foi possível registrar o recebimento'),
    },
  );
}
</script>

<template>
  <BaseModal
    :is-open="!!conta"
    title="Registrar recebimento"
    size="sm"
    overlay
    @close="emit('fechar')"
  >
    <div v-if="conta" class="flex flex-col gap-4">
      <div class="rounded-xl bg-zinc-50 px-4 py-3">
        <p class="text-sm font-semibold text-zinc-800">{{ conta.descricao }}</p>
        <p class="mt-0.5 text-xs text-zinc-500">
          Previsto {{ formatCurrency(conta.valor) }} · vence {{ formatDataPura(conta.vencimento) }}
          <template v-if="conta.taxa > 0">
            · taxa da operadora {{ formatCurrency(conta.taxa) }}
          </template>
        </p>
      </div>

      <div>
        <p class="mb-1.5 block select-none text-xs font-medium text-zinc-700">Como está pagando</p>
        <div class="grid grid-cols-3 gap-1.5">
          <button
            v-for="forma in formasAtivas" :key="forma.id" type="button"
            class="flex flex-col items-center justify-center gap-0.5 rounded-lg border-2 p-2 transition-all cursor-pointer"
            :class="formaPagamentoId === forma.id
              ? 'border-brand-primary bg-brand-primary/5 text-brand-primary'
              : 'border-zinc-200 bg-white text-zinc-500 hover:border-zinc-300 hover:bg-zinc-50'"
            @click="formaPagamentoId = forma.id"
          >
            <component :is="iconeDaForma(forma)" :size="15" />
            <span class="text-[11px] font-medium leading-tight text-center">{{ forma.nome }}</span>
          </button>
        </div>
      </div>

      <BaseMoneyInput v-model="jurosReais" label="Juros / multa" />

      <!-- Sem esta escolha, o juros da maquininha entraria no caixa como se
           fosse dinheiro da loja. -->
      <fieldset v-if="jurosReais > 0" class="-mt-1 flex flex-col gap-2">
        <legend class="mb-1 block text-xs font-medium text-zinc-700">Esse juros fica com</legend>
        <div class="grid gap-2 sm:grid-cols-2">
          <label
            v-for="opcao in [
              { valor: 'LOJA', titulo: 'A loja', ajuda: 'Multa por atraso' },
              { valor: 'OPERADORA', titulo: 'A operadora', ajuda: 'Juros do parcelamento' },
            ]"
            :key="opcao.valor"
            class="cursor-pointer rounded-xl border px-3 py-2 transition"
            :class="jurosDestino === opcao.valor
              ? 'border-brand-primary bg-brand-primary/5 ring-1 ring-brand-primary'
              : 'border-zinc-200 hover:border-zinc-300'"
          >
            <input v-model="jurosDestino" type="radio" :value="opcao.valor" class="sr-only" />
            <span class="block text-sm font-medium text-zinc-800">{{ opcao.titulo }}</span>
            <span class="block text-[11px] text-zinc-400">{{ opcao.ajuda }}</span>
          </label>
        </div>
      </fieldset>

      <BaseMoneyInput v-model="valorReais" label="Valor recebido (total)" />
      <p v-if="diferenca !== 0" class="-mt-2 text-xs" :class="diferenca > 0 ? 'text-emerald-600' : 'text-amber-600'">
        {{ diferenca > 0 ? 'Entrou' : 'Faltou' }}
        {{ formatCurrency(Math.abs(diferenca)) }} em relação ao previsto.
      </p>

      <p v-if="jurosDestino === 'OPERADORA' && jurosReais > 0" class="-mt-2 rounded-xl bg-amber-50 px-3.5 py-2.5 text-xs text-amber-700">
        O cliente desembolsa {{ formatCurrency(Math.round(valorReais * 100)) }}, mas entram
        <strong>{{ formatCurrency(entraNaLoja) }}</strong> na loja — o resto fica com a operadora.
      </p>

      <BaseInput v-model="recebidoEm" type="date" label="Data do recebimento" required />

      <div>
        <BaseSelect
          v-model="contaBancariaId"
          :options="opcoesContas"
          label="Entrou em"
          placeholder="Selecione a conta"
        />

        <button
          v-if="!cadastrandoConta" type="button"
          class="mt-1.5 flex items-center gap-1 text-xs font-medium text-brand-primary cursor-pointer"
          @click="cadastrandoConta = true"
        >
          <Plus :size="13" /> Cadastrar outra conta
        </button>

        <div v-else class="mt-2 flex flex-col gap-2 rounded-xl border border-zinc-200 p-3">
          <BaseInput v-model="nomeNovaConta" label="Nome da conta" placeholder="Ex.: Nubank" />
          <div class="grid grid-cols-3 gap-1.5">
            <button
              v-for="op in [
                { valor: 'CAIXA', titulo: 'Caixa' },
                { valor: 'BANCO', titulo: 'Banco' },
                { valor: 'CARTAO_CREDITO', titulo: 'Cartão' },
              ]"
              :key="op.valor" type="button"
              class="rounded-lg border-2 px-2 py-1.5 text-xs font-medium transition cursor-pointer"
              :class="tipoNovaConta === op.valor
                ? 'border-brand-primary bg-brand-primary/5 text-brand-primary'
                : 'border-zinc-200 text-zinc-500 hover:border-zinc-300'"
              @click="tipoNovaConta = op.valor"
            >
              {{ op.titulo }}
            </button>
          </div>
          <div class="flex justify-end gap-2">
            <button type="button" class="text-xs text-zinc-500 cursor-pointer" @click="cadastrandoConta = false">
              Cancelar
            </button>
            <button
              type="button"
              class="text-xs font-semibold text-brand-primary disabled:opacity-40 cursor-pointer"
              :disabled="!nomeNovaConta.trim() || criarConta.isPending.value"
              @click="salvarNovaConta"
            >
              Salvar conta
            </button>
          </div>
        </div>
      </div>

      <p class="text-xs text-zinc-400">
        Quitar uma dívida antiga não é venda no PDV. Se o dinheiro entrou na gaveta, registre
        um suprimento à parte.
      </p>
    </div>

    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <BaseButton variant="secondary" class="px-5" @click="emit('fechar')">Cancelar</BaseButton>
        <BaseButton
          variant="primary"
          class="px-5"
          :disabled="valorReais <= 0"
          :is-loading="receber.isPending.value"
          @click="confirmar"
        >
          Confirmar recebimento
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
