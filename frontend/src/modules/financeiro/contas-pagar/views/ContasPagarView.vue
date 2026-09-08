<script setup lang="ts">
/**
 * O que a loja deve.
 *
 * Os totais do rodapé vêm do SERVIDOR e valem para o filtro inteiro, não para a
 * página — somar os itens aqui daria o total da página, e a diferença só
 * apareceria quando a loja já tivesse contas o bastante para paginar.
 */
import { computed, ref } from 'vue';
import { useRoute } from 'vue-router';
import { Filter, ChevronLeft, ChevronRight, Plus, Undo2, RotateCcw } from 'lucide-vue-next';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseSearchInput from '@/shared/components/ui/BaseSearchInput/BaseSearchInput.vue';
import BaseConfirmModal from '@/shared/components/commons/BaseConfirmModal/BaseConfirmModal.vue';
import { useConfirmacao } from '@/shared/composables/useConfirmacao';
import { useToast } from '@/shared/composables/useToast';
import { formatCurrency } from '@/shared/utils/finance';
import { formatDataPura } from '@/shared/utils/date.utils';

import ContaPagarBaixaModal from '../components/ContaPagarBaixaModal.vue';
import ContaPagarCategoriaModal from '../components/ContaPagarCategoriaModal.vue';
import ContaPagarDetalheModal from '../components/ContaPagarDetalheModal.vue';
import ContaPagarEstornoModal from '../components/ContaPagarEstornoModal.vue';
import ContaPagarFormModal from '../components/ContaPagarFormModal.vue';
import { usePeriodoMes } from '../../shared/composables/usePeriodoMes';
import {
  useCancelarContaPagar,
  useReativarContaPagar,
  useContasPagarQuery,
} from '../../shared/composables/useFinanceiro';
import type { ContaPagar } from '../../shared/schemas/financeiro.schema';

const toast = useToast();
const { range, rotulo, anterior, proximo } = usePeriodoMes();

const statusFiltro = ref('');
const busca = ref('');

/**
 * O recorte que o painel de atenção mandou junto na rota.
 *
 * Chegar aqui pelo alerta e cair na lista inteira devolveria ao dono o trabalho
 * que o sistema já tinha feito — ele sabia QUAIS contas geraram o aviso. Com
 * `vencidas`, o backend ignora o mês de propósito: conta vencida é de mês
 * anterior quase sempre, e o recorte do mês esconderia justamente ela.
 */
const route = useRoute();
const recorte = ref<string>((route.query.filtro as string) ?? '');

const ROTULO_RECORTE: Record<string, string> = {
  vencidas: 'só as contas vencidas',
  'sem-categoria': 'só as contas sem categoria',
};

const filtros = computed(() => ({
  inicio: range.value.inicio,
  fim: range.value.fim,
  status: statusFiltro.value || undefined,
  busca: busca.value.trim() || undefined,
  vencidas: recorte.value === 'vencidas' || undefined,
  sem_categoria: recorte.value === 'sem-categoria' || undefined,
}));

const { data: listagem, isLoading } = useContasPagarQuery(filtros);
const cancelar = useCancelarContaPagar();
const reativar = useReativarContaPagar();
const confirmacao = useConfirmacao();

const formAberto = ref(false);
const contaEmEdicao = ref<ContaPagar | null>(null);
const contaParaBaixa = ref<ContaPagar | null>(null);
const contaParaEstorno = ref<ContaPagar | null>(null);
const contaParaDetalhe = ref<ContaPagar | null>(null);
const contaParaClassificar = ref<ContaPagar | null>(null);

const ABAS = [
  { valor: '', rotulo: 'Todas' },
  { valor: 'PENDENTE', rotulo: 'Em aberto' },
  { valor: 'PAGA', rotulo: 'Pagas' },
  { valor: 'CANCELADA', rotulo: 'Canceladas' },
];

function novaConta() {
  contaEmEdicao.value = null;
  formAberto.value = true;
}

function editar(conta: ContaPagar) {
  // Conta paga não se edita: o backend recusa, porque o valor já virou
  // lançamento. Barrar aqui evita o usuário preencher o formulário à toa.
  if (conta.status === 'PAGA') {
    toast.error('Esta conta já foi paga', 'Estorne o pagamento antes de alterá-la.');
    return;
  }
  contaEmEdicao.value = conta;
  formAberto.value = true;
}

/**
 * Cancelar usa o modal de confirmação da casa, não o `window.confirm`.
 *
 * O diálogo nativo do navegador aparece como "localhost:1420 diz" — fora do
 * visual do sistema, e num app desktop denuncia que ali dentro é uma página web.
 */
/**
 * Confirma antes de reativar pelo mesmo motivo do cancelamento: a conta volta a
 * contar no "a pagar em aberto" e no Fluxo de Caixa, e num parcelamento ela
 * reaparece no meio da fila.
 */
async function confirmarReativacao(conta: ContaPagar) {
  const ok = await confirmacao.pedirConfirmacao({
    titulo: 'Reativar esta conta?',
    descricao:
      `<strong>${conta.descricao}</strong> volta para <strong>em aberto</strong> e passa a ` +
      'contar de novo no que a loja deve, no vencimento original.',
    confirmLabel: 'Reativar',
    cancelLabel: 'Voltar',
  });
  if (!ok) return;
  reativar.mutate(conta.id);
}

async function confirmarCancelamento(conta: ContaPagar) {
  const ok = await confirmacao.pedirConfirmacao({
    titulo: 'Cancelar esta conta?',
    descricao:
      `<strong>${conta.descricao}</strong> deixa de ser cobrada, mas continua no histórico ` +
      'como cancelada. Nada é excluído.',
    confirmLabel: 'Cancelar conta',
    cancelLabel: 'Voltar',
    variant: 'warning',
  });
  if (!ok) return;
  cancelar.mutate(conta.id);
}

function classeStatus(conta: ContaPagar): string {
  if (conta.status === 'PAGA') return 'bg-emerald-50 text-emerald-700';
  if (conta.status === 'CANCELADA') return 'bg-zinc-100 text-zinc-500';
  if (conta.vencida) return 'bg-rose-50 text-rose-700';
  return 'bg-amber-50 text-amber-700';
}

function rotuloStatus(conta: ContaPagar): string {
  if (conta.status === 'PAGA') return 'Paga';
  if (conta.status === 'CANCELADA') return 'Cancelada';
  return conta.vencida ? 'Vencida' : 'Em aberto';
}
</script>

<template>
  <div class="flex flex-col gap-6 md:gap-8">
    <!-- O aviso de que a lista NÃO é o mês: quem chegou pelo painel de atenção
         está vendo um recorte, e sem dizer isso a tela parece ter esquecido
         contas. "Mostrar tudo" devolve o comportamento normal. -->
    <div
      v-if="recorte"
      class="flex flex-wrap items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-800"
    >
      <Filter :size="13" />
      <span>
        Mostrando <strong>{{ ROTULO_RECORTE[recorte] ?? recorte }}</strong>, de qualquer mês —
        veio do aviso da Visão Geral.
      </span>
      <button
        type="button"
        class="font-semibold underline underline-offset-2 cursor-pointer"
        @click="recorte = ''"
      >
        Mostrar tudo
      </button>
    </div>

    <!-- Filtros -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <button type="button" @click="anterior" class="p-2 rounded-lg border border-zinc-200 hover:bg-zinc-50 cursor-pointer" aria-label="Mês anterior">
          <ChevronLeft :size="18" class="text-zinc-600" />
        </button>
        <span class="font-semibold text-zinc-800 min-w-40 text-center">{{ rotulo }}</span>
        <button type="button" @click="proximo" class="p-2 rounded-lg border border-zinc-200 hover:bg-zinc-50 cursor-pointer" aria-label="Próximo mês">
          <ChevronRight :size="18" class="text-zinc-600" />
        </button>
      </div>

      <BaseButton variant="primary" @click="novaConta">
        <Plus :size="16" class="mr-1.5" /> Nova conta
      </BaseButton>
    </div>

    <div class="flex flex-wrap items-center gap-3">
      <div class="flex rounded-xl bg-zinc-100 p-1">
        <button
          v-for="aba in ABAS" :key="aba.valor" type="button"
          class="rounded-lg px-3 py-1.5 text-sm font-medium transition cursor-pointer"
          :class="statusFiltro === aba.valor ? 'bg-white text-zinc-800 shadow-sm' : 'text-zinc-500 hover:text-zinc-700'"
          @click="statusFiltro = aba.valor"
        >
          {{ aba.rotulo }}
        </button>
      </div>
      <div class="w-full sm:w-64">
        <BaseSearchInput v-model="busca" placeholder="Buscar pela descrição" />
      </div>
    </div>

    <!-- Totais: do filtro inteiro, não da página -->
    <div v-if="listagem" class="grid gap-3 sm:grid-cols-3">
      <div class="rounded-xl border border-zinc-100 bg-white px-4 py-3 shadow-sm">
        <p class="text-[11px] font-semibold uppercase tracking-wide text-zinc-500">Em aberto</p>
        <p class="mt-1 text-lg font-bold text-zinc-800 tabular-nums">{{ formatCurrency(listagem.total_pendente) }}</p>
      </div>
      <div class="rounded-xl border px-4 py-3 shadow-sm"
           :class="listagem.total_vencido > 0 ? 'border-rose-200 bg-rose-50' : 'border-zinc-100 bg-white'">
        <p class="text-[11px] font-semibold uppercase tracking-wide"
           :class="listagem.total_vencido > 0 ? 'text-rose-600' : 'text-zinc-500'">Vencido</p>
        <p class="mt-1 text-lg font-bold tabular-nums"
           :class="listagem.total_vencido > 0 ? 'text-rose-700' : 'text-zinc-800'">
          {{ formatCurrency(listagem.total_vencido) }}
        </p>
      </div>
      <div class="rounded-xl border border-zinc-100 bg-white px-4 py-3 shadow-sm">
        <p class="text-[11px] font-semibold uppercase tracking-wide text-zinc-500">Pago no período</p>
        <p class="mt-1 text-lg font-bold text-zinc-800 tabular-nums">{{ formatCurrency(listagem.total_pago) }}</p>
      </div>
    </div>

    <!-- Lista -->
    <div v-if="isLoading" class="text-sm text-zinc-500">Carregando…</div>

    <div v-else-if="!listagem?.itens.length" class="rounded-2xl border border-dashed border-zinc-200 px-6 py-12 text-center">
      <p class="text-sm font-medium text-zinc-700">Nenhuma conta neste período</p>
      <p class="mt-1 text-sm text-zinc-400">Lance aluguel, fornecedores e despesas fixas para ver o resultado real do mês.</p>
    </div>

    <div v-else class="overflow-x-auto rounded-2xl border border-zinc-100 bg-white shadow-sm">
      <table class="w-full min-w-180 text-sm">
        <thead>
          <tr class="border-b border-zinc-100 text-left text-[11px] font-semibold uppercase tracking-wide text-zinc-500">
            <th class="px-5 py-3">Descrição</th>
            <th class="px-5 py-3">Categoria</th>
            <th class="px-5 py-3">Vencimento</th>
            <th class="px-5 py-3 text-right">Valor</th>
            <th class="px-5 py-3">Situação</th>
            <th class="px-5 py-3 text-right">Ações</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-zinc-100">
          <tr v-for="conta in listagem.itens" :key="conta.id" class="hover:bg-zinc-50/60">
            <td class="px-5 py-3">
              <!-- Abre o DETALHE, como em Contas a Receber — não o formulário.
                   A trilha de auditoria só existe aqui dentro, e enquanto este
                   clique chamava `editar` ela era inalcançável: o modal estava
                   montado na tela e nada nunca o preenchia. Editar continua a
                   um clique, na coluna de ações. -->
              <button
                type="button"
                class="text-left font-medium text-zinc-800 hover:underline underline-offset-2 cursor-pointer"
                @click="contaParaDetalhe = conta"
              >
                {{ conta.descricao }}
              </button>
              <!-- Uma marca ou outra, nunca as duas: parcelado e mensal são
                   mecanismos que se excluem. -->
              <span
                v-if="conta.parcela_total"
                class="ml-2 rounded-full bg-violet-50 px-1.5 py-0.5 text-[10px] font-medium text-violet-600 tabular-nums"
              >
                {{ conta.parcela_numero }}/{{ conta.parcela_total }}
              </span>
              <span v-else-if="conta.recorrente" class="ml-2 rounded-full bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-600">
                mensal
              </span>
            </td>
            <td class="px-5 py-3 text-zinc-500">{{ conta.plano_conta_nome ?? '—' }}</td>
            <td class="px-5 py-3 text-zinc-600">{{ formatDataPura(conta.vencimento) }}</td>
            <td class="px-5 py-3 text-right font-semibold text-zinc-800 tabular-nums">
              {{ formatCurrency(conta.valor_pago ?? conta.valor) }}
            </td>
            <td class="px-5 py-3">
              <span class="rounded-full px-2 py-0.5 text-[11px] font-semibold" :class="classeStatus(conta)">
                {{ rotuloStatus(conta) }}
              </span>
            </td>
            <td class="px-5 py-3">
              <div class="flex items-center justify-end gap-3">
                <template v-if="conta.status === 'PENDENTE'">
                  <button type="button" class="text-xs font-semibold text-brand-primary cursor-pointer" @click="contaParaBaixa = conta">
                    Pagar
                  </button>
                  <!-- Discreto ao lado de "Pagar", mas nunca cinza-desabilitado:
                       em `text-zinc-400` ele lia como rótulo morto e ninguém
                       achava a ação. Continua secundário pela ausência de cor
                       de marca, não pela falta de contraste. -->
                  <button type="button" class="text-xs font-medium text-zinc-600 underline-offset-2 hover:text-zinc-900 hover:underline cursor-pointer" @click="editar(conta)">
                    Editar
                  </button>
                  <button type="button" class="text-xs font-medium text-zinc-600 underline-offset-2 hover:text-zinc-900 hover:underline cursor-pointer" @click="confirmarCancelamento(conta)">
                    Cancelar
                  </button>
                </template>
                <template v-else-if="conta.status === 'PAGA'">
                  <!-- Classificar uma conta PAGA é permitido de propósito: a
                       categoria nunca entrou no livro do dinheiro, e sem esta
                       ação o alerta "gastos sem categoria" não teria como sair
                       da tela — ele conta justamente as despesas pagas. -->
                  <button
                    type="button"
                    class="text-xs font-medium text-zinc-600 underline-offset-2 hover:text-zinc-900 hover:underline cursor-pointer"
                    @click="contaParaClassificar = conta"
                  >
                    Classificar
                  </button>
                  <button
                    type="button"
                    class="flex items-center gap-1 text-xs font-medium text-zinc-500 hover:text-zinc-700 cursor-pointer"
                    @click="contaParaEstorno = conta"
                  >
                    <Undo2 :size="13" /> Estornar
                  </button>
                </template>
                <!-- CANCELADA tinha um "—" e nada mais: a conta saía da lista
                     de "em aberto" e não voltava nunca. Numa parcela 9/72 de um
                     empréstimo, o controle inteiro ficava furado por um clique
                     errado. -->
                <template v-else-if="conta.status === 'CANCELADA'">
                  <button
                    type="button"
                    class="flex items-center gap-1 text-xs font-medium text-brand-primary cursor-pointer"
                    @click="confirmarReativacao(conta)"
                  >
                    <RotateCcw :size="13" /> Reativar
                  </button>
                </template>
                <span v-else class="text-xs text-zinc-300">—</span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <ContaPagarFormModal
      :aberto="formAberto"
      :conta="contaEmEdicao"
      @fechar="formAberto = false"
    />
    <ContaPagarDetalheModal :conta="contaParaDetalhe" @fechar="contaParaDetalhe = null" />
    <ContaPagarCategoriaModal
      :conta="contaParaClassificar"
      @fechar="contaParaClassificar = null"
    />
    <ContaPagarBaixaModal :conta="contaParaBaixa" @fechar="contaParaBaixa = null" />
    <ContaPagarEstornoModal :conta="contaParaEstorno" @fechar="contaParaEstorno = null" />

    <BaseConfirmModal
      :is-open="confirmacao.isOpen.value"
      :title="confirmacao.opcoes.value.titulo"
      :description="confirmacao.opcoes.value.descricao"
      :confirm-label="confirmacao.opcoes.value.confirmLabel"
      :cancel-label="confirmacao.opcoes.value.cancelLabel"
      :variant="confirmacao.opcoes.value.variant"
      overlay
      @confirm="confirmacao.confirmar"
      @close="confirmacao.cancelar"
    />
  </div>
</template>
