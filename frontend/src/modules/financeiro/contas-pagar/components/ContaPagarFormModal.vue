<script setup lang="ts">
/**
 * Cadastro e edição de uma conta a pagar.
 *
 * Conta já PAGA não chega aqui: o backend recusa a edição, porque o valor já
 * virou lançamento no livro e mexer no documento faria a despesa do relatório
 * discordar do movimento. Para corrigir, estorna-se primeiro.
 */
import { computed, ref, watch } from 'vue';
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseMoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';
import BaseSelect from '@/shared/components/ui/BaseSelect/BaseSelect.vue';
import { useToast } from '@/shared/composables/useToast';
import { formatCurrency } from '@/shared/utils/finance';

import {
  useAtualizarContaPagar,
  useCriarContaPagar,
  usePlanoContasQuery,
} from '../../shared/composables/useFinanceiro';
import type { ContaPagar } from '../../shared/schemas/financeiro.schema';

const props = defineProps<{ aberto: boolean; conta?: ContaPagar | null }>();
const emit = defineEmits<{ fechar: [] }>();

const toast = useToast();
const { data: categorias } = usePlanoContasQuery(true);
const criar = useCriarContaPagar();
const atualizar = useAtualizarContaPagar();

const editando = computed(() => !!props.conta);

const descricao = ref('');
// Em REAIS aqui, porque é o que o BaseMoneyInput manipula; a conversão para
// centavos acontece num ponto só, no envio.
const valorReais = ref(0);
const vencimento = ref('');
const planoContaId = ref<string | number>('');
const observacao = ref('');

/**
 * Como esta conta se repete — três opções mutuamente exclusivas.
 *
 * É a distinção que Odoo, ERPNext, Omie e Conta Azul fazem igual, e que os dois
 * campos que o backend já tem (`parcelas` e `recorrente`) expressam sem precisar
 * de enum:
 *
 *   UNICA      parcelas=1, recorrente=false
 *   PARCELADA  parcelas=N, recorrente=false  → dívida única dividida, com fim
 *   MENSAL     parcelas=1, recorrente=true   → repetição sem total conhecido
 *
 * Parcelada e mensal se excluem: uma compra em 10x não se repete para sempre, e
 * o backend recusa as duas juntas com 422.
 */
type Repeticao = 'UNICA' | 'PARCELADA' | 'MENSAL';
const repeticao = ref<Repeticao>('UNICA');
const parcelas = ref(2);

const opcoesCategoria = computed(() => [
  { value: '', label: 'Sem categoria' },
  ...(categorias.value ?? []).map((c) => ({ value: c.id, label: c.nome })),
]);

function hojeLocal(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

// Repovoa a cada abertura. Sem isto, abrir para editar depois de ter criado
// deixaria os campos da conta anterior na tela.
watch(
  () => [props.aberto, props.conta] as const,
  ([aberto]) => {
    if (!aberto) return;
    const c = props.conta;
    descricao.value = c?.descricao ?? '';
    valorReais.value = c ? c.valor / 100 : 0;
    vencimento.value = c?.vencimento ?? hojeLocal();
    planoContaId.value = c?.plano_conta_id ?? '';
    observacao.value = c?.observacao ?? '';
    repeticao.value = c?.recorrente ? 'MENSAL' : 'UNICA';
    parcelas.value = 2;
  },
  { immediate: true },
);

/**
 * Parcelamento só existe na CRIAÇÃO.
 *
 * Editando, cada parcela é uma linha independente — como no Odoo, onde a
 * unidade de controle é a data de vencimento e não o contrato. Reparcelar do
 * formulário significaria apagar e recriar as parcelas restantes, e as que já
 * foram pagas não têm como voltar atrás.
 */
const podeParcelar = computed(() => !editando.value);

/** Meses somados ao vencimento, ancorados no dia original (igual ao backend). */
function somarMeses(iso: string, meses: number): Date | null {
  if (!iso) return null;
  const [a, m, d] = iso.split('-').map(Number);
  if (!a || !m || !d) return null;
  const total = m - 1 + meses;
  const ano = a + Math.floor(total / 12);
  const mes = ((total % 12) + 12) % 12;
  // Dia 0 do mês seguinte = último dia deste; encolhe 31 para 28/30 sem vazar.
  const ultimoDia = new Date(ano, mes + 1, 0).getDate();
  return new Date(ano, mes, Math.min(d, ultimoDia));
}

function mesAno(dt: Date | null): string {
  if (!dt) return '';
  return dt.toLocaleDateString('pt-BR', { month: 'short', year: 'numeric' }).replace('.', '');
}

/**
 * A simulação, copiada da Omie: mostra o que vai acontecer ANTES de salvar.
 *
 * Gerar dez linhas de uma vez sem avisar assusta na primeira vez, e o usuário
 * não tem como saber se errou a quantidade antes de ver a lista cheia.
 */
const simulacao = computed(() => {
  if (repeticao.value !== 'PARCELADA' || parcelas.value < 2 || !vencimento.value) return null;
  const n = parcelas.value;
  const primeira = somarMeses(vencimento.value, 0);
  const ultima = somarMeses(vencimento.value, n - 1);
  return {
    n,
    de: mesAno(primeira),
    ate: mesAno(ultima),
    total: Math.round(valorReais.value * 100) * n,
  };
});

const salvando = computed(() => criar.isPending.value || atualizar.isPending.value);

const podeSalvar = computed(
  () => !!descricao.value.trim() && valorReais.value > 0 && !!vencimento.value,
);

function salvar() {
  if (!podeSalvar.value) return;

  const parcelado = podeParcelar.value && repeticao.value === 'PARCELADA';

  const payload = {
    descricao: descricao.value.trim(),
    // Arredonda no fim: 12.34 * 100 dá 1233.9999... em ponto flutuante, e sem
    // o round a conta entraria um centavo menor. No parcelamento este é o valor
    // de CADA parcela, não o total.
    valor: Math.round(valorReais.value * 100),
    vencimento: vencimento.value,
    plano_conta_id: planoContaId.value === '' ? null : Number(planoContaId.value),
    recorrente: repeticao.value === 'MENSAL',
    parcelas: parcelado ? parcelas.value : 1,
    observacao: observacao.value.trim() || null,
  };

  const aoErrar = (e: any) =>
    toast.error(e?.response?.data?.detail ?? 'Não foi possível salvar a conta');

  if (editando.value && props.conta) {
    atualizar.mutate(
      { id: props.conta.id, payload },
      { onSuccess: () => emit('fechar'), onError: aoErrar },
    );
  } else {
    criar.mutate(payload, { onSuccess: () => emit('fechar'), onError: aoErrar });
  }
}
</script>

<template>
  <BaseModal
    :is-open="aberto"
    :title="editando ? 'Editar conta' : 'Nova conta a pagar'"
    size="md"
    overlay
    @close="emit('fechar')"
  >
    <div class="flex flex-col gap-4">
      <BaseInput v-model="descricao" label="Descrição" placeholder="Ex.: Aluguel de setembro" required />

      <div class="grid gap-4 sm:grid-cols-2">
        <BaseMoneyInput v-model="valorReais" label="Valor" />
        <BaseInput v-model="vencimento" type="date" label="Vencimento" required />
      </div>

      <BaseSelect v-model="planoContaId" :options="opcoesCategoria" label="Categoria" placeholder="Sem categoria" />

      <!-- Como a conta se repete. Três opções exclusivas: ver o comentário
           de `repeticao` no script para o porquê da separação. -->
      <fieldset v-if="podeParcelar" class="flex flex-col gap-2">
        <legend class="mb-1.5 block text-sm font-medium text-gray-700">Repetição</legend>
        <div class="grid gap-2 sm:grid-cols-3">
          <label
            v-for="opcao in [
              { valor: 'UNICA', titulo: 'Conta única', ajuda: 'Vence uma vez só' },
              { valor: 'PARCELADA', titulo: 'Parcelada', ajuda: 'Tem fim: 10x, 4x…' },
              { valor: 'MENSAL', titulo: 'Todo mês', ajuda: 'Aluguel, luz, internet' },
            ]"
            :key="opcao.valor"
            class="cursor-pointer rounded-xl border px-3 py-2.5 transition"
            :class="repeticao === opcao.valor
              ? 'border-brand-primary bg-brand-primary/5 ring-1 ring-brand-primary'
              : 'border-gray-200 hover:border-gray-300'"
          >
            <input v-model="repeticao" type="radio" :value="opcao.valor" class="sr-only" />
            <span class="block text-sm font-medium text-gray-800">{{ opcao.titulo }}</span>
            <span class="block text-[11px] text-gray-400">{{ opcao.ajuda }}</span>
          </label>
        </div>
      </fieldset>

      <div v-if="podeParcelar && repeticao === 'PARCELADA'" class="flex flex-col gap-2">
        <div class="w-full sm:w-40">
          <BaseInput
            v-model.number="parcelas" type="number" :min="2" :max="360"
            label="Quantas parcelas"
          />
        </div>
        <!-- A simulação vem da Omie: mostra o que vai acontecer antes de
             salvar, porque gerar dez linhas sem avisar assusta. -->
        <p v-if="simulacao" class="rounded-xl bg-gray-50 px-3.5 py-2.5 text-xs text-gray-600">
          <strong class="text-gray-800">
            {{ simulacao.n }} parcelas de {{ formatCurrency(Math.round(valorReais * 100)) }}
          </strong>
          · {{ simulacao.de }} a {{ simulacao.ate }} · total
          {{ formatCurrency(simulacao.total) }}
        </p>
      </div>

      <p v-if="podeParcelar && repeticao === 'MENSAL'" class="-mt-1 text-xs text-gray-400">
        Ao dar baixa, a conta do mês seguinte é criada automaticamente com o valor previsto.
      </p>

      <BaseInput v-model="observacao" label="Observação" placeholder="Opcional" />

    </div>

    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <BaseButton variant="secondary" class="px-5" @click="emit('fechar')">Cancelar</BaseButton>
        <BaseButton
          variant="primary"
          class="px-5"
          :disabled="!podeSalvar"
          :is-loading="salvando"
          @click="salvar"
        >
          Salvar
        </BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
