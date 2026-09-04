<script setup lang="ts">
import { computed, ref } from 'vue';
import { z } from 'zod';
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

/**
 * O contrato da listagem, validado.
 *
 * Sem esta validação, um backend mais antigo (que devolve o formato anterior de
 * `GET /caixa/`) preenchia a tabela com campos indefinidos — e a tela mostrava
 * R$ 0,00 em tudo. Um relatório de dinheiro tem que QUEBRAR quando não entende
 * a resposta, não inventar zeros.
 */
const HistoricoItemSchema = z.object({
  sessao_id: z.number(),
  status: z.string(),
  funcionario_nome: z.string().nullable().optional(),
  terminal_nome: z.string().nullable().optional(),
  data_abertura: z.string(),
  data_fechamento: z.string().nullable().optional(),
  saldo_inicial: z.number(),
  saldo_esperado: z.number().nullable(),
  saldo_contado: z.number().nullable(),
  diferenca: z.number().nullable(),
});

const CONTRATO_INVALIDO = 'CONTRATO_INVALIDO';

const historico = useQuery({
  queryKey: computed(() => ['caixa', 'historico', props.inicio, props.fim]),
  queryFn: async () => {
    const { data } = await api.get('/caixa/', {
      params: { inicio: props.inicio, fim: props.fim },
    });
    const parsed = z.array(HistoricoItemSchema).safeParse(data);
    if (!parsed.success) throw new Error(CONTRATO_INVALIDO);
    return parsed.data;
  },
  // 403 (não é gerente) e contrato inválido não melhoram com repetição.
  retry: false,
});

const sessoes = computed(() => historico.data.value ?? []);

const contratoInvalido = computed(
  () => (historico.error.value as Error | null)?.message === CONTRATO_INVALIDO,
);
const semPermissao = computed(() => historico.isError.value && !contratoInvalido.value);

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

/**
 * Falta é o que dói; sobra é sinal de lançamento perdido. Cores diferentes.
 *
 * `== null` pega null E undefined de propósito. A versão anterior usava
 * `=== null`, e um campo AUSENTE (backend mais antigo, resposta truncada)
 * escapava por baixo dos dois `if` e caía no último caso — que dizia
 * "Bateu certo". Uma tela de dinheiro que, sem dado, AFIRMA que está tudo certo
 * é pior que uma tela quebrada: o dono acredita e não confere.
 */
function classeDiferenca(diferenca: number | null | undefined): string {
  if (diferenca == null) return 'text-slate-400';
  if (diferenca < 0) return 'text-red-600 font-bold';
  if (diferenca > 0) return 'text-amber-600 font-semibold';
  return 'text-emerald-600';
}

function rotuloDiferenca(diferenca: number | null | undefined): string {
  if (diferenca == null) return '—';
  if (diferenca < 0) return `${formatarCentavos(diferenca)} · faltou`;
  if (diferenca > 0) return `+${formatarCentavos(diferenca)} · sobrou`;
  return 'Bateu certo';
}

/** Valor monetário que pode não ter vindo. Ausente vira travessão, nunca zero. */
function moeda(valor: number | null | undefined): string {
  return valor == null ? '—' : formatarCentavos(valor);
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

    <p v-if="contratoInvalido" class="text-sm text-red-600 py-6 text-center">
      Não foi possível ler o histórico de caixas: o servidor respondeu num
      formato que esta tela não entende. Se o sistema foi atualizado agora,
      reinicie o servidor.
    </p>

    <p v-else-if="semPermissao" class="text-sm text-slate-500 py-6 text-center">
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
                {{ moeda(s.saldo_esperado) }}
              </td>
              <td class="py-2 px-2 text-right tabular-nums text-slate-600">
                {{ moeda(s.saldo_contado) }}
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
