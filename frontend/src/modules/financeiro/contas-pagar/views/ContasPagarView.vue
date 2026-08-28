<script setup lang="ts">
/**
 * O que a loja deve.
 *
 * Os totais do rodapé vêm do SERVIDOR e valem para o filtro inteiro, não para a
 * página — somar os itens aqui daria o total da página, e a diferença só
 * apareceria quando a loja já tivesse contas o bastante para paginar.
 */
import { computed, ref } from 'vue';
import { ChevronLeft, ChevronRight, Plus, Undo2 } from 'lucide-vue-next';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseSearchInput from '@/shared/components/ui/BaseSearchInput/BaseSearchInput.vue';
import { useToast } from '@/shared/composables/useToast';
import { formatCurrency } from '@/shared/utils/finance';
import { formatDataPura } from '@/shared/utils/date.utils';

import ContaPagarBaixaModal from '../components/ContaPagarBaixaModal.vue';
import ContaPagarFormModal from '../components/ContaPagarFormModal.vue';
import { usePeriodoMes } from '../../shared/composables/usePeriodoMes';
import {
  useCancelarContaPagar,
  useContasPagarQuery,
  useEstornarPagamento,
} from '../../shared/composables/useFinanceiro';
import type { ContaPagar } from '../../shared/schemas/financeiro.schema';

const toast = useToast();
const { range, rotulo, anterior, proximo } = usePeriodoMes();

const statusFiltro = ref('');
const busca = ref('');

const filtros = computed(() => ({
  inicio: range.value.inicio,
  fim: range.value.fim,
  status: statusFiltro.value || undefined,
  busca: busca.value.trim() || undefined,
}));

const { data: listagem, isLoading } = useContasPagarQuery(filtros);
const cancelar = useCancelarContaPagar();
const estornar = useEstornarPagamento();

const formAberto = ref(false);
const contaEmEdicao = ref<ContaPagar | null>(null);
const contaParaBaixa = ref<ContaPagar | null>(null);

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

function confirmarCancelamento(conta: ContaPagar) {
  if (!window.confirm(`Cancelar a conta "${conta.descricao}"?`)) return;
  cancelar.mutate(conta.id);
}

function confirmarEstorno(conta: ContaPagar) {
  // O motivo é obrigatório no backend, e é o que a auditoria lê depois.
  const motivo = window.prompt('Por que este pagamento está sendo estornado?');
  if (!motivo || motivo.trim().length < 3) return;
  estornar.mutate({ id: conta.id, motivo: motivo.trim() });
}

function classeStatus(conta: ContaPagar): string {
  if (conta.status === 'PAGA') return 'bg-emerald-50 text-emerald-700';
  if (conta.status === 'CANCELADA') return 'bg-gray-100 text-gray-500';
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
  <div class="flex flex-col gap-5">
    <!-- Filtros -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <button type="button" @click="anterior" class="p-2 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer" aria-label="Mês anterior">
          <ChevronLeft :size="18" class="text-gray-600" />
        </button>
        <span class="font-semibold text-gray-800 min-w-40 text-center">{{ rotulo }}</span>
        <button type="button" @click="proximo" class="p-2 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer" aria-label="Próximo mês">
          <ChevronRight :size="18" class="text-gray-600" />
        </button>
      </div>

      <BaseButton variant="primary" @click="novaConta">
        <Plus :size="16" class="mr-1.5" /> Nova conta
      </BaseButton>
    </div>

    <div class="flex flex-wrap items-center gap-3">
      <div class="flex rounded-xl bg-gray-100 p-1">
        <button
          v-for="aba in ABAS" :key="aba.valor" type="button"
          class="rounded-lg px-3 py-1.5 text-sm font-medium transition cursor-pointer"
          :class="statusFiltro === aba.valor ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'"
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
      <div class="rounded-xl border border-gray-100 bg-white px-4 py-3 shadow-sm">
        <p class="text-[11px] font-semibold uppercase tracking-wide text-gray-500">Em aberto</p>
        <p class="mt-1 text-lg font-bold text-gray-800 tabular-nums">{{ formatCurrency(listagem.total_pendente) }}</p>
      </div>
      <div class="rounded-xl border px-4 py-3 shadow-sm"
           :class="listagem.total_vencido > 0 ? 'border-rose-200 bg-rose-50' : 'border-gray-100 bg-white'">
        <p class="text-[11px] font-semibold uppercase tracking-wide"
           :class="listagem.total_vencido > 0 ? 'text-rose-600' : 'text-gray-500'">Vencido</p>
        <p class="mt-1 text-lg font-bold tabular-nums"
           :class="listagem.total_vencido > 0 ? 'text-rose-700' : 'text-gray-800'">
          {{ formatCurrency(listagem.total_vencido) }}
        </p>
      </div>
      <div class="rounded-xl border border-gray-100 bg-white px-4 py-3 shadow-sm">
        <p class="text-[11px] font-semibold uppercase tracking-wide text-gray-500">Pago no período</p>
        <p class="mt-1 text-lg font-bold text-gray-800 tabular-nums">{{ formatCurrency(listagem.total_pago) }}</p>
      </div>
    </div>

    <!-- Lista -->
    <div v-if="isLoading" class="text-sm text-gray-500">Carregando…</div>

    <div v-else-if="!listagem?.itens.length" class="rounded-2xl border border-dashed border-gray-200 px-6 py-12 text-center">
      <p class="text-sm font-medium text-gray-700">Nenhuma conta neste período</p>
      <p class="mt-1 text-sm text-gray-400">Lance aluguel, fornecedores e despesas fixas para ver o resultado real do mês.</p>
    </div>

    <div v-else class="overflow-x-auto rounded-2xl border border-gray-100 bg-white shadow-sm">
      <table class="w-full min-w-180 text-sm">
        <thead>
          <tr class="border-b border-gray-100 text-left text-[11px] font-semibold uppercase tracking-wide text-gray-500">
            <th class="px-5 py-3">Descrição</th>
            <th class="px-5 py-3">Categoria</th>
            <th class="px-5 py-3">Vencimento</th>
            <th class="px-5 py-3 text-right">Valor</th>
            <th class="px-5 py-3">Situação</th>
            <th class="px-5 py-3 text-right">Ações</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="conta in listagem.itens" :key="conta.id" class="hover:bg-gray-50/60">
            <td class="px-5 py-3">
              <button type="button" class="text-left font-medium text-gray-800 cursor-pointer" @click="editar(conta)">
                {{ conta.descricao }}
              </button>
              <span v-if="conta.recorrente" class="ml-2 rounded-full bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-600">
                mensal
              </span>
            </td>
            <td class="px-5 py-3 text-gray-500">{{ conta.plano_conta_nome ?? '—' }}</td>
            <td class="px-5 py-3 text-gray-600">{{ formatDataPura(conta.vencimento) }}</td>
            <td class="px-5 py-3 text-right font-semibold text-gray-800 tabular-nums">
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
                  <button type="button" class="text-xs font-medium text-gray-400 hover:text-gray-600 cursor-pointer" @click="confirmarCancelamento(conta)">
                    Cancelar
                  </button>
                </template>
                <button
                  v-else-if="conta.status === 'PAGA'"
                  type="button"
                  class="flex items-center gap-1 text-xs font-medium text-gray-500 hover:text-gray-700 cursor-pointer"
                  @click="confirmarEstorno(conta)"
                >
                  <Undo2 :size="13" /> Estornar
                </button>
                <span v-else class="text-xs text-gray-300">—</span>
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
    <ContaPagarBaixaModal :conta="contaParaBaixa" @fechar="contaParaBaixa = null" />
  </div>
</template>
