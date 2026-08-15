<script setup lang="ts">
import { computed, ref } from 'vue';
import { useQuery } from '@tanstack/vue-query';
import { ChevronDown, ChevronRight, Wallet } from 'lucide-vue-next';

import api from '@/api/axios';
import { formatarCentavos } from '@/modules/sales/caixa/caixa.utils';
import { SessaoCaixaResumoSchema } from '@/modules/sales/caixa/schemas/caixa.schema';
import { formatDataHora } from '@/shared/utils/date.utils';

/**
 * O histórico de turnos, na visão do dono.
 *
 * Responde as duas perguntas que ele faz olhando o mês: **quem fechou faltando
 * dinheiro** e **quem fechou sobrando**. As duas saem da mesma coluna, e as duas
 * importam — sobra costuma ser troco não registrado ou venda não lançada, que é
 * problema tanto quanto a falta.
 */

const props = defineProps<{ inicio: string; fim: string }>();

const expandida = ref<number | null>(null);

const historico = useQuery({
  queryKey: computed(() => ['caixa', 'historico', props.inicio, props.fim]),
  queryFn: async () => {
    const { data } = await api.get('/caixa/', {
      params: { inicio: props.inicio, fim: props.fim },
    });
    return data as Array<{
      sessao_id: number;
      status: string;
      funcionario_nome: string | null;
      terminal_nome: string | null;
      data_abertura: string;
      data_fechamento: string | null;
      saldo_inicial: number;
      saldo_esperado: number | null;
      saldo_contado: number | null;
      diferenca: number | null;
    }>;
  },
  // 403/400 aqui é esperado para quem não é gerente — não vale reexecutar.
  retry: false,
});

const sessoes = computed(() => historico.data.value ?? []);
const semPermissao = computed(() => historico.isError.value);

const extrato = useQuery({
  queryKey: computed(() => ['caixa', 'sessao', expandida.value]),
  queryFn: async () => {
    const { data } = await api.get(`/caixa/${expandida.value}`);
    return SessaoCaixaResumoSchema.parse(data);
  },
  enabled: computed(() => expandida.value !== null),
});

function alternar(sessaoId: number) {
  expandida.value = expandida.value === sessaoId ? null : sessaoId;
}

/** Falta é o que dói; sobra é sinal de lançamento perdido. Cores diferentes. */
function classeDiferenca(diferenca: number | null): string {
  if (diferenca === null) return 'text-slate-400';
  if (diferenca < 0) return 'text-red-600 font-bold';
  if (diferenca > 0) return 'text-amber-600 font-semibold';
  return 'text-emerald-600';
}

function rotuloDiferenca(diferenca: number | null): string {
  if (diferenca === null) return '—';
  if (diferenca < 0) return `${formatarCentavos(diferenca)} · faltou`;
  if (diferenca > 0) return `+${formatarCentavos(diferenca)} · sobrou`;
  return 'Bateu certo';
}

const ORIGEM_ROTULO: Record<string, string> = {
  ABERTURA: 'Troco de abertura',
  VENDA: 'Venda',
  ORDEM_SERVICO: 'Ordem de serviço',
  SANGRIA: 'Sangria',
  SUPRIMENTO: 'Suprimento',
  RECEBIMENTO: 'Recebimento',
  DESPESA: 'Despesa',
};
</script>

<template>
  <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
    <div class="flex items-center gap-2 mb-3">
      <Wallet class="h-4 w-4 text-slate-500" />
      <h3 class="text-sm font-bold text-slate-700">Caixa — turnos do período</h3>
    </div>

    <p v-if="semPermissao" class="text-sm text-slate-500 py-6 text-center">
      Só o responsável pela loja pode ver o histórico de caixas.
    </p>

    <p v-else-if="historico.isLoading.value" class="text-sm text-slate-400 py-6 text-center">
      Carregando…
    </p>

    <p v-else-if="sessoes.length === 0" class="text-sm text-slate-500 py-6 text-center">
      Nenhum turno de caixa aberto neste período.
    </p>

    <div v-else class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-xs uppercase tracking-wide text-slate-500 border-b border-slate-200">
            <th class="py-2 px-2"></th>
            <th class="py-2 px-2">Operador</th>
            <th class="py-2 px-2">Terminal</th>
            <th class="py-2 px-2">Abertura</th>
            <th class="py-2 px-2">Fechamento</th>
            <th class="py-2 px-2 text-right">Esperado</th>
            <th class="py-2 px-2 text-right">Contado</th>
            <th class="py-2 px-2 text-right">Diferença</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="s in sessoes" :key="s.sessao_id">
            <tr
              class="border-b border-slate-100 hover:bg-slate-50 cursor-pointer"
              @click="alternar(s.sessao_id)"
            >
              <td class="py-2 px-2 text-slate-400">
                <ChevronDown v-if="expandida === s.sessao_id" :size="16" />
                <ChevronRight v-else :size="16" />
              </td>
              <td class="py-2 px-2 font-medium text-slate-800">
                {{ s.funcionario_nome ?? '—' }}
              </td>
              <td class="py-2 px-2 text-slate-500">{{ s.terminal_nome ?? '—' }}</td>
              <td class="py-2 px-2 text-slate-600">{{ formatDataHora(s.data_abertura) }}</td>
              <td class="py-2 px-2 text-slate-600">
                <span v-if="s.data_fechamento">{{ formatDataHora(s.data_fechamento) }}</span>
                <span v-else class="text-emerald-600 font-medium">Em aberto</span>
              </td>
              <td class="py-2 px-2 text-right tabular-nums text-slate-600">
                {{ s.saldo_esperado === null ? '—' : formatarCentavos(s.saldo_esperado) }}
              </td>
              <td class="py-2 px-2 text-right tabular-nums text-slate-600">
                {{ s.saldo_contado === null ? '—' : formatarCentavos(s.saldo_contado) }}
              </td>
              <td class="py-2 px-2 text-right tabular-nums" :class="classeDiferenca(s.diferenca)">
                {{ rotuloDiferenca(s.diferenca) }}
              </td>
            </tr>

            <!-- O extrato: cada movimento com motivo e o nome de quem fez. É aqui
                 que "saiu R$ 200" vira "o Fulano tirou R$ 200 às 14h pro cofre". -->
            <tr v-if="expandida === s.sessao_id" :key="`extrato-${s.sessao_id}`">
              <td colspan="8" class="bg-slate-50 px-4 py-3">
                <p v-if="extrato.isLoading.value" class="text-xs text-slate-400">Carregando extrato…</p>
                <div v-else-if="extrato.data.value" class="space-y-2">
                  <div class="flex flex-wrap gap-4 text-xs text-slate-600">
                    <span>Troco inicial: <strong>{{ formatarCentavos(extrato.data.value.saldo_inicial) }}</strong></span>
                    <span>Vendas: <strong>{{ formatarCentavos(extrato.data.value.total_vendas) }}</strong></span>
                    <span>Suprimentos: <strong>{{ formatarCentavos(extrato.data.value.total_suprimentos) }}</strong></span>
                    <span>Sangrias: <strong>{{ formatarCentavos(extrato.data.value.total_sangrias) }}</strong></span>
                  </div>

                  <table class="w-full text-xs mt-2">
                    <thead>
                      <tr class="text-left text-slate-400">
                        <th class="py-1">Quando</th>
                        <th class="py-1">O quê</th>
                        <th class="py-1">Quem</th>
                        <th class="py-1">Motivo</th>
                        <th class="py-1 text-right">Valor</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="m in extrato.data.value.movimentos"
                        :key="m.id"
                        class="border-t border-slate-200"
                      >
                        <td class="py-1 text-slate-500">{{ formatDataHora(m.criado_em) }}</td>
                        <td class="py-1 text-slate-700">{{ ORIGEM_ROTULO[m.origem] ?? m.origem }}</td>
                        <td class="py-1 text-slate-700">{{ m.funcionario_nome ?? '—' }}</td>
                        <td class="py-1 text-slate-500">{{ m.motivo ?? '—' }}</td>
                        <td
                          class="py-1 text-right tabular-nums"
                          :class="m.tipo === 'SAIDA' ? 'text-red-600' : 'text-slate-700'"
                        >
                          {{ m.tipo === 'SAIDA' ? '−' : '' }}{{ formatarCentavos(m.valor) }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</template>
