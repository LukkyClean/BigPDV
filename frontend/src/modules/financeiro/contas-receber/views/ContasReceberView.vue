<script setup lang="ts">
/**
 * O que ainda não entrou.
 *
 * A maioria destas linhas NASCE SOZINHA, no fecho da venda ou da OS, quando o
 * operador marca "vou receber depois". As lançadas à mão existem para o que não
 * passou pelo sistema — o cliente que já devia antes do módulo existir.
 */
import { computed, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { Filter, ChevronLeft, ChevronRight, Plus, Undo2, Wallet, AlertTriangle, CheckCircle2 } from 'lucide-vue-next';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import PageReview from '@/shared/components/layout/PageReview/PageReview.vue';
import BaseStatsCard from '@/shared/components/layout/StatsCard/BaseStatsCard.vue';
import BaseTableContainer from '@/shared/components/commons/BaseTableContainer/BaseTableContainer.vue';
import BaseSearchInput from '@/shared/components/ui/BaseSearchInput/BaseSearchInput.vue';
import BaseConfirmModal from '@/shared/components/commons/BaseConfirmModal/BaseConfirmModal.vue';
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import BaseMoneyInput from '@/shared/components/ui/BaseMoneyInput/MoneyInput.vue';
import { useConfirmacao } from '@/shared/composables/useConfirmacao';
import { useToast } from '@/shared/composables/useToast';
import { formatCurrency } from '@/shared/utils/finance';
import { formatDataPura } from '@/shared/utils/date.utils';

import ContaReceberBaixaModal from '../components/ContaReceberBaixaModal.vue';
import ContaReceberDetalheModal from '../components/ContaReceberDetalheModal.vue';
import ContaReceberEstornoModal from '../components/ContaReceberEstornoModal.vue';
import { usePeriodoMes } from '../../shared/composables/usePeriodoMes';
import {
  useCancelarContaReceber,
  useContasReceberQuery,
  useCriarContaReceber,
} from '../../shared/composables/useFinanceiro';
import type { ContaReceber } from '../../shared/schemas/financeiro.schema';

const toast = useToast();
const confirmacao = useConfirmacao();
const { range, rotulo, anterior, proximo } = usePeriodoMes();

const statusFiltro = ref('');
const busca = ref('');

// Mesmo recorte vindo do painel de atenção, pela mesma razão da tela de Contas
// a Pagar: o alerta sabe quais linhas o originaram, e `vencidas` ignora o mês.
const route = useRoute();
const recorte = ref<string>((route.query.filtro as string) ?? '');

const ROTULO_RECORTE: Record<string, string> = {
  vencidas: 'só as cobranças vencidas',
};

// Mesmo ritmo de Contas a Pagar e do resto do sistema.
const POR_PAGINA = 20;
const pagina = ref(1);

const filtros = computed(() => ({
  limit: POR_PAGINA,
  offset: (pagina.value - 1) * POR_PAGINA,
  inicio: range.value.inicio,
  fim: range.value.fim,
  status: statusFiltro.value || undefined,
  busca: busca.value.trim() || undefined,
  vencidas: recorte.value === 'vencidas' || undefined,
}));

// Trocar de mes, status ou busca volta para a primeira pagina: quem estava na
// pagina 4 veria tela vazia, com resultado existindo mais acima.
watch([range, statusFiltro, busca, recorte], () => { pagina.value = 1; });

const { data: listagem, isLoading, isError } = useContasReceberQuery(filtros);

const totalPaginas = computed(() =>
  Math.max(1, Math.ceil((listagem.value?.total_itens ?? 0) / POR_PAGINA)),
);
const cancelar = useCancelarContaReceber();
const criar = useCriarContaReceber();

const contaParaBaixa = ref<ContaReceber | null>(null);
const contaParaEstorno = ref<ContaReceber | null>(null);
const contaParaDetalhe = ref<ContaReceber | null>(null);

const ABAS = [
  { valor: '', rotulo: 'Todas' },
  { valor: 'PENDENTE', rotulo: 'Em aberto' },
  { valor: 'RECEBIDA', rotulo: 'Recebidas' },
  { valor: 'CANCELADA', rotulo: 'Canceladas' },
];

// --- Lançamento manual ---
const formAberto = ref(false);
const novaDescricao = ref('');
const novoValor = ref(0);
const novoVencimento = ref('');

function abrirForm() {
  const d = new Date();
  d.setDate(d.getDate() + 30);
  novaDescricao.value = '';
  novoValor.value = 0;
  novoVencimento.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  formAberto.value = true;
}

const podeSalvar = computed(
  () => !!novaDescricao.value.trim() && novoValor.value > 0 && !!novoVencimento.value,
);

function salvarNova() {
  if (!podeSalvar.value) return;
  criar.mutate(
    {
      descricao: novaDescricao.value.trim(),
      valor: Math.round(novoValor.value * 100),
      vencimento: novoVencimento.value,
    },
    {
      onSuccess: () => (formAberto.value = false),
      onError: (e: any) =>
        toast.error(e?.response?.data?.detail ?? 'Não foi possível lançar a cobrança'),
    },
  );
}

async function confirmarCancelamento(conta: ContaReceber) {
  const ok = await confirmacao.pedirConfirmacao({
    titulo: 'Cancelar esta cobrança?',
    descricao:
      `<strong>${conta.descricao}</strong> deixa de ser cobrada, mas continua no histórico ` +
      'como cancelada. Nada é excluído.',
    confirmLabel: 'Cancelar cobrança',
    cancelLabel: 'Voltar',
    variant: 'warning',
  });
  if (!ok) return;
  cancelar.mutate(conta.id);
}

function classeStatus(conta: ContaReceber): string {
  if (conta.status === 'RECEBIDA') return 'bg-emerald-50 text-emerald-700';
  if (conta.status === 'CANCELADA') return 'bg-zinc-100 text-zinc-500';
  if (conta.vencida) return 'bg-rose-50 text-rose-700';
  return 'bg-amber-50 text-amber-700';
}

function rotuloStatus(conta: ContaReceber): string {
  if (conta.status === 'RECEBIDA') return 'Recebida';
  if (conta.status === 'CANCELADA') return 'Cancelada';
  return conta.vencida ? 'Atrasada' : 'Em aberto';
}
</script>

<template>
  <div class="flex flex-col gap-6 md:gap-8">
    <!-- Cabecalho da secao. Mesmo padrao de Clientes e Produtos:
         PageReview a esquerda, acao principal a direita. -->
    <div class="flex items-center justify-between gap-4">
      <PageReview title="Contas a Receber" description="Cobranças em aberto e o que já foi quitado" />
      <BaseButton variant="primary" @click="abrirForm">
        <Plus :size="16" class="mr-1.5" /> Nova cobrança
      </BaseButton>
    </div>

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

    </div>


    <!-- Indicadores. Mesmo card do resto do sistema; o tom `perigo`
         acende quando ha atraso -- e o numero que o dono ve primeiro. -->
    <div v-if="listagem" class="grid gap-3 sm:grid-cols-3">
      <BaseStatsCard
        :icon="Wallet"
        label="A receber"
        :value="formatCurrency(listagem.total_pendente)"
      />
      <BaseStatsCard
        :icon="AlertTriangle"
        label="Atrasado"
        :value="formatCurrency(listagem.total_vencido)"
        :tone="listagem.total_vencido > 0 ? 'perigo' : 'neutro'"
      />
      <BaseStatsCard
        :icon="CheckCircle2"
        label="Recebido no período"
        :value="formatCurrency(listagem.total_recebido)"
      />
    </div>

    <!-- Lista. Container padrao: moldura, estados e paginacao. -->
    <BaseTableContainer
      :is-loading="isLoading"
      :is-error="isError"
      :is-empty="!listagem?.itens.length"
      :current-page="pagina"
      :total-pages="totalPaginas"
      :total-items="listagem?.total_itens ?? 0"
      item-label="cobrança"
      item-label-plural="cobranças"
      empty-title="Nada a receber neste período"
      empty-description="Ao fechar uma venda ou OS, marque “Vou receber depois” e a cobrança aparece aqui."
      @update:current-page="pagina = $event"
    >
      <!-- Busca e filtro moram DENTRO da tabela, como em Clientes e
           Produtos: sao ferramentas da listagem, nao da pagina. -->
      <template #toolbar>
        <BaseSearchInput v-model="busca" placeholder="Buscar pela descrição" />
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
      </template>

    <table class="w-full min-w-180 text-sm">
      <thead>
        <tr class="border-b border-zinc-100 text-left text-[11px] font-semibold uppercase tracking-wide text-zinc-500">
          <th class="px-5 py-3">Descrição</th>
          <th class="px-5 py-3">Cliente</th>
          <th class="px-5 py-3">Vencimento</th>
          <th class="px-5 py-3 text-right">Valor</th>
          <th class="px-5 py-3">Situação</th>
          <th class="px-5 py-3 text-right">Ações</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-zinc-100">
        <tr v-for="conta in listagem?.itens ?? []" :key="conta.id" class="hover:bg-zinc-50/60">
          <td class="px-5 py-3">
            <button
              type="button"
              class="text-left font-medium text-zinc-800 hover:underline underline-offset-2 cursor-pointer"
              @click="contaParaDetalhe = conta"
            >
              {{ conta.descricao }}
            </button>
            <!-- "automática" = reflexo de um documento fechado. Vale dizer,
                 porque explica por que a linha apareceu sem ninguém digitar. -->
            <span v-if="conta.automatica" class="ml-2 rounded-full bg-sky-50 px-1.5 py-0.5 text-[10px] font-medium text-sky-600">
              do fechamento
            </span>
          </td>
          <td class="px-5 py-3 text-zinc-500">{{ conta.cliente_nome ?? '—' }}</td>
          <td class="px-5 py-3 text-zinc-600">{{ formatDataPura(conta.vencimento) }}</td>
          <td class="px-5 py-3 text-right font-semibold text-zinc-800 tabular-nums">
            {{ formatCurrency(conta.valor_recebido ?? conta.valor) }}
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
                  Receber
                </button>
                <button type="button" class="text-xs font-medium text-zinc-600 underline-offset-2 hover:text-zinc-900 hover:underline cursor-pointer" @click="confirmarCancelamento(conta)">
                  Cancelar
                </button>
              </template>
              <button
                v-else-if="conta.status === 'RECEBIDA'"
                type="button"
                class="flex items-center gap-1 text-xs font-medium text-zinc-600 hover:text-zinc-900 cursor-pointer"
                @click="contaParaEstorno = conta"
              >
                <Undo2 :size="13" /> Estornar
              </button>
              <span v-else class="text-xs text-zinc-300">—</span>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
    </BaseTableContainer>

    <ContaReceberDetalheModal :conta="contaParaDetalhe" @fechar="contaParaDetalhe = null" />
    <ContaReceberBaixaModal :conta="contaParaBaixa" @fechar="contaParaBaixa = null" />
    <ContaReceberEstornoModal :conta="contaParaEstorno" @fechar="contaParaEstorno = null" />

    <BaseModal
      :is-open="formAberto"
      title="Nova cobrança"
      subtitle="Para o que não passou pela venda nem pela OS"
      size="sm"
      overlay
      @close="formAberto = false"
    >
      <div class="flex flex-col gap-4">
        <BaseInput v-model="novaDescricao" label="Descrição" placeholder="Ex.: Acerto de agosto" required />
        <BaseMoneyInput v-model="novoValor" label="Valor" />
        <BaseInput v-model="novoVencimento" type="date" label="Quando vai receber" required />
      </div>
      <template #footer>
        <div class="flex w-full justify-end gap-2">
          <BaseButton variant="secondary" class="px-5" @click="formAberto = false">Cancelar</BaseButton>
          <BaseButton
            variant="primary" class="px-5"
            :disabled="!podeSalvar" :is-loading="criar.isPending.value"
            @click="salvarNova"
          >
            Salvar
          </BaseButton>
        </div>
      </template>
    </BaseModal>

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
