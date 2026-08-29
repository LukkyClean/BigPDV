<script setup lang="ts">
/**
 * "Onde a loja está precisando de atenção."
 *
 * O backend manda só o CÓDIGO e os números; a frase e o destino moram aqui. É
 * o que permite mudar a redação, o rótulo por segmento e o idioma sem tocar em
 * regra de negócio — e o que impede a tela de virar um tradutor de enum.
 *
 * REGRA DE OURO: todo alerta aponta para o lugar que resolve. Aviso sem ação é
 * o que faz um painel destes morrer — quem vê aviso todo dia para de ler, e
 * some junto o aviso que importava. Lista vazia é boa notícia, e some da tela.
 */
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { AlertTriangle, ArrowRight, CircleAlert } from 'lucide-vue-next';

import { formatCurrency } from '@/shared/utils/finance';
import { formatDataPura } from '@/shared/utils/date.utils';

import type { AlertaFinanceiro } from '../schemas/financeiro.schema';

const props = defineProps<{ alertas: AlertaFinanceiro[] }>();
const emit = defineEmits<{ informarSaldo: [] }>();

const router = useRouter();

interface Texto {
  titulo: string;
  detalhe: string;
  acao?: string;
  rota?: string;
  evento?: 'informarSaldo';
}

function traduzir(alerta: AlertaFinanceiro): Texto | null {
  const valor = formatCurrency(Math.abs(alerta.valor ?? 0));

  switch (alerta.codigo) {
    case 'CAIXA_NEGATIVO':
      return {
        titulo: `O dinheiro acaba em ${formatDataPura(alerta.data ?? '')}`,
        detalhe: `Pelo que está agendado, o saldo fica negativo nesse dia e chega a ${valor}. Dá para adiar uma conta, cobrar um fiado ou reforçar o caixa até lá.`,
        acao: 'Ver a projeção',
        rota: 'finance-cashflow',
      };
    case 'CONTAS_VENCIDAS':
      return {
        titulo: `${valor} em contas vencidas`,
        detalhe: 'Passou do vencimento e continua devido. Quanto mais tempo, maior a multa.',
        acao: 'Ver contas a pagar',
        rota: 'finance-payable',
      };
    case 'FIADO_ATRASADO':
      return {
        titulo: `${valor} atrasado a receber`,
        detalhe: 'Dinheiro seu que já deveria ter voltado. Cobrar cedo é o que separa atraso de calote.',
        acao: 'Ver quem deve',
        rota: 'finance-receivable',
      };
    case 'MES_NO_VERMELHO':
      return {
        titulo: `O mês está negativo em ${valor}`,
        detalhe: 'Saiu mais do que entrou no período. Veja abaixo para onde o dinheiro foi.',
      };
    case 'SALDO_NUNCA_INFORMADO':
      return {
        titulo: 'O sistema não sabe quanto você tem hoje',
        detalhe: 'Sem esse número não há projeção possível — e ele é o único que só você tem.',
        acao: 'Informar saldo',
        evento: 'informarSaldo',
      };
    case 'SALDO_DESATUALIZADO':
      return {
        titulo: `Saldo informado há ${alerta.quantidade} dias`,
        detalhe: 'O saldo não anda sozinho: dar baixa numa conta não o move. Confira e atualize.',
        acao: 'Atualizar saldo',
        evento: 'informarSaldo',
      };
    case 'DESPESA_SEM_CATEGORIA':
      return {
        titulo: `${valor} gastos sem categoria`,
        detalhe: 'Enquanto a maior fatia se chamar "Sem categoria", o resumo não diz para onde o dinheiro foi.',
        acao: 'Classificar',
        rota: 'finance-payable',
      };
    // Código desconhecido não vira linha em branco: some. Um backend mais novo
    // que este frontend não deve desenhar caixa vazia na tela do lojista.
    default:
      return null;
  }
}

const itens = computed(() =>
  props.alertas
    .map((alerta) => ({ alerta, texto: traduzir(alerta) }))
    .filter((item): item is { alerta: AlertaFinanceiro; texto: Texto } => item.texto !== null),
);

function agir(item: { alerta: AlertaFinanceiro; texto: Texto }) {
  if (item.texto.evento) return emit(item.texto.evento);
  if (item.texto.rota) router.push({ name: item.texto.rota });
}
</script>

<template>
  <section v-if="itens.length" class="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
    <h3 class="flex items-center gap-2 text-sm font-bold text-gray-800">
      <CircleAlert :size="16" class="text-amber-500" /> Precisa de atenção
    </h3>

    <ul class="mt-4 flex flex-col divide-y divide-gray-100">
      <li
        v-for="item in itens"
        :key="item.alerta.codigo"
        class="flex flex-wrap items-start justify-between gap-3 py-3 first:pt-0 last:pb-0"
      >
        <div class="flex min-w-0 gap-3">
          <!-- A cor é o único peso visual que separa "resolva hoje" de
               "resolva esta semana". Ícone igual para os dois deixaria o
               painel achatado. -->
          <AlertTriangle
            :size="16"
            class="mt-0.5 shrink-0"
            :class="item.alerta.severidade === 'CRITICO' ? 'text-rose-500' : 'text-amber-500'"
          />
          <div class="min-w-0">
            <p
              class="text-sm font-semibold"
              :class="item.alerta.severidade === 'CRITICO' ? 'text-rose-700' : 'text-gray-800'"
            >
              {{ item.texto.titulo }}
            </p>
            <p class="mt-0.5 text-xs text-gray-500">{{ item.texto.detalhe }}</p>
          </div>
        </div>

        <button
          v-if="item.texto.acao"
          type="button"
          class="flex shrink-0 items-center gap-1 text-xs font-semibold text-brand-primary cursor-pointer hover:underline underline-offset-2"
          @click="agir(item)"
        >
          {{ item.texto.acao }} <ArrowRight :size="13" />
        </button>
      </li>
    </ul>
  </section>
</template>
