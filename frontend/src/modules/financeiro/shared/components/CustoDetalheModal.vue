<script setup lang="ts">
/**
 * O card "Custo do que vendeu" aberto, linha a linha.
 *
 * POR QUE ISTO EXISTE. Em 05/09/2026 o dono passou uma tarde conferindo
 * R$ 846 de CMV contra as anotações de papel dele, OS por OS, e não fechava por
 * R$ 19. Não havia como descobrir: o "Custo para a loja" só aparecia dentro do
 * modal de editar item, e a aba trava quando a OS finaliza. O sistema pedia um
 * número, usava esse número no lucro e nunca mais mostrava.
 *
 * ⚠️ CUSTO É INTERNO. Esta tela é do dono. Nada daqui sai em via impressa, no
 * resumo da OS ou no resumo de pagamento — regra explícita dele.
 */
import { computed } from 'vue';
import { Package, Lock } from 'lucide-vue-next';
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import { formatCurrency } from '@/shared/utils/finance';
import { useCustoDetalheQuery } from '../composables/useFinanceiro';

const props = defineProps<{
  aberto: boolean;
  inicio: string;
  fim: string;
  /** O total do resumo. Serve de conferência: os dois TÊM que bater. */
  totalEsperado: number;
}>();

const emit = defineEmits<{ fechar: [] }>();

const aberto = computed(() => props.aberto);
const { data, isLoading, isError } = useCustoDetalheQuery(
  computed(() => props.inicio),
  computed(() => props.fim),
  aberto,
);

const linhas = computed(() => data.value?.linhas ?? []);

/**
 * Divergência entre o detalhe e o card. Deve ser sempre zero — as duas somas
 * saem das mesmas quatro parcelas. Mostrar em vez de esconder: um detalhe que
 * não fecha com o total é bug, e esconder isso destrói a confiança nos dois.
 */
const divergencia = computed(() => (data.value?.total ?? 0) - props.totalEsperado);

const FONTE_ROTULO: Record<string, { label: string; cls: string }> = {
  ESTOQUE: { label: 'Estoque', cls: 'bg-slate-100 text-slate-600' },
  DECLARADO: { label: 'Declarado', cls: 'bg-amber-50 text-amber-700' },
  ESTORNO: { label: 'Estorno', cls: 'bg-emerald-50 text-emerald-700' },
};

function fonteBadge(fonte: string) {
  return FONTE_ROTULO[fonte] ?? FONTE_ROTULO.ESTOQUE;
}

function diaMes(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? '—'
    : `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`;
}
</script>

<template>
  <BaseModal
    :is-open="aberto"
    title="Custo do que vendeu"
    subtitle="Cada peça que saiu, e de qual venda ou ordem de serviço"
    size="xl"
    @close="emit('fechar')"
  >
    <p class="flex items-center gap-1.5 mb-3 text-[11px] text-slate-400">
      <Lock :size="11" class="shrink-0" />
      Informação interna — nunca sai em via do cliente.
    </p>

    <div v-if="isLoading" class="py-10 text-center text-sm text-slate-400">Carregando…</div>

    <div v-else-if="isError" class="py-10 text-center text-sm text-red-500">
      Não foi possível carregar o detalhamento.
    </div>

    <div v-else-if="!linhas.length" class="py-10 text-center">
      <Package :size="28" class="mx-auto text-slate-300" />
      <p class="mt-2 text-sm text-slate-500">Nenhuma peça saiu neste período.</p>
      <p class="mt-1 text-xs text-slate-400">
        Serviço sem peça não gera custo aqui — e isso está certo.
      </p>
    </div>

    <template v-else>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-[11px] uppercase tracking-wide text-slate-400 border-b border-slate-200">
              <th class="py-2 pr-3 text-left font-medium">Data</th>
              <th class="py-2 px-3 text-left font-medium">Origem</th>
              <th class="py-2 px-3 text-left font-medium">Item</th>
              <th class="py-2 px-3 text-right font-medium">Qtd</th>
              <th class="py-2 px-3 text-left font-medium">Fonte</th>
              <th class="py-2 pl-3 text-right font-medium">Custo</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(l, idx) in linhas"
              :key="`${l.origem}-${l.referencia}-${idx}`"
              class="border-b border-slate-100 last:border-0"
            >
              <td class="py-2 pr-3 text-slate-500 tabular-nums">{{ diaMes(l.data) }}</td>
              <td class="py-2 px-3 text-slate-700 font-medium whitespace-nowrap">
                {{ l.origem === 'OS' ? 'OS' : 'Venda' }} {{ l.referencia }}
              </td>
              <td class="py-2 px-3 text-slate-600">{{ l.descricao }}</td>
              <td class="py-2 px-3 text-right text-slate-500 tabular-nums">{{ l.quantidade }}</td>
              <td class="py-2 px-3">
                <span
                  class="text-[10px] font-bold px-1.5 py-0.5 rounded-full"
                  :class="fonteBadge(l.fonte).cls"
                >
                  {{ fonteBadge(l.fonte).label }}
                </span>
              </td>
              <td
                class="py-2 pl-3 text-right font-semibold tabular-nums"
                :class="l.custo < 0 ? 'text-emerald-600' : 'text-slate-800'"
              >
                {{ formatCurrency(l.custo) }}
              </td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="border-t-2 border-slate-200">
              <td colspan="5" class="py-2.5 pr-3 text-right text-xs font-bold uppercase text-slate-500">
                Total
              </td>
              <td class="py-2.5 pl-3 text-right text-base font-black text-slate-800 tabular-nums">
                {{ formatCurrency(data?.total ?? 0) }}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      <!-- Só aparece se houver bug. Ver o comentário em `divergencia`. -->
      <p v-if="divergencia !== 0" class="mt-3 text-xs text-red-600">
        Este detalhamento soma {{ formatCurrency(divergencia) }} a
        {{ divergencia > 0 ? 'mais' : 'menos' }} que o card. Avise o suporte — os dois
        deveriam ser o mesmo número.
      </p>
      <p v-else class="mt-3 text-xs text-slate-400">
        Linha <strong class="text-amber-700">Declarado</strong> é o "Custo para a loja" que
        você digitou no item da OS. <strong class="text-emerald-700">Estorno</strong> é peça
        que voltou — entra negativo porque o custo sai da conta.
      </p>
    </template>
  </BaseModal>
</template>
