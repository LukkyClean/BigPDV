<script setup lang="ts">
/**
 * As categorias que classificam cada conta que a loja paga.
 *
 * NÃO existe excluir, só desativar — e isso é regra, não limitação da tela: a
 * categoria pode estar amarrada a contas antigas, e apagá-la faria o relatório
 * do ano passado mostrar "sem categoria" onde sempre houve uma.
 *
 * A NATUREZA (despesa ou custo) entrou aqui em 02/09/2026, e não é detalhe de
 * organização: ela decide QUANDO o gasto sai do lucro. Comprar mercadoria não
 * empobrece a loja — converte dinheiro em estoque — e só vira custo no dia em
 * que a peça é vendida. Sem essa distinção, a mesma peça era descontada duas
 * vezes do lucro: uma na compra, outra na venda.
 */
import { computed, ref } from 'vue';
import { Plus, Check, X } from 'lucide-vue-next';

import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseInput from '@/shared/components/ui/BaseInput/BaseInput.vue';
import { useToast } from '@/shared/composables/useToast';

import type { PlanoContaTipo } from '../../shared/schemas/financeiro.schema';
import {
  useAtualizarPlanoConta,
  useCriarPlanoConta,
  usePlanoContasQuery,
} from '../../shared/composables/useFinanceiro';

const toast = useToast();
const { data: categorias, isLoading } = usePlanoContasQuery(false);
const criar = useCriarPlanoConta();
const atualizar = useAtualizarPlanoConta();

const novoNome = ref('');
const novoTipo = ref<PlanoContaTipo>('DESPESA');
const editandoId = ref<number | null>(null);
const nomeEditado = ref('');

/**
 * As duas naturezas que a tela oferece.
 *
 * RECEITA fica de fora de propósito: esta tela classifica o que a loja PAGA, e
 * oferecer receita aqui só produziria categoria de entrada em contas a pagar —
 * uma escolha errada que ninguém consegue desfazer depois que há conta lançada.
 */
const NATUREZAS: { valor: PlanoContaTipo; rotulo: string; ajuda: string }[] = [
  {
    valor: 'DESPESA',
    rotulo: 'Despesa',
    ajuda: 'Gasto para a loja funcionar: aluguel, luz, internet, salário.',
  },
  {
    valor: 'CUSTO',
    rotulo: 'Compra de mercadoria',
    ajuda: 'Peça ou produto para revender. Só entra no lucro quando for vendido.',
  },
];

const ajudaDaNatureza = computed(
  () => NATUREZAS.find((n) => n.valor === novoTipo.value)?.ajuda ?? '',
);

function adicionar() {
  const nome = novoNome.value.trim();
  if (!nome) return;
  criar.mutate(
    { nome, tipo: novoTipo.value },
    {
      onSuccess: () => {
        novoNome.value = '';
        novoTipo.value = 'DESPESA';
      },
      // O backend recusa nome repetido com 400 e uma mensagem pronta. Mostrar a
      // dele em vez de uma genérica é o que diz ao usuário QUAL nome colidiu.
      onError: (e: any) =>
        toast.error(e?.response?.data?.detail ?? 'Não foi possível criar a categoria'),
    },
  );
}

/**
 * Vira a chave entre despesa e compra de mercadoria.
 *
 * Corrigir a natureza de uma categoria ANTIGA é o ponto: quem já lançava
 * "Compra de peças" como despesa estava descontando a peça duas vezes do lucro,
 * e o conserto tem que alcançar os meses passados — e alcança, porque o lucro
 * é recalculado na leitura.
 */
function alternarNatureza(id: number, tipo: string) {
  atualizar.mutate({ id, dados: { tipo: tipo === 'CUSTO' ? 'DESPESA' : 'CUSTO' } });
}

function abrirEdicao(id: number, nome: string) {
  editandoId.value = id;
  nomeEditado.value = nome;
}

function salvarEdicao(id: number) {
  const nome = nomeEditado.value.trim();
  if (!nome) return;
  atualizar.mutate({ id, dados: { nome } }, { onSuccess: () => (editandoId.value = null) });
}

function alternarAtivo(id: number, ativo: boolean) {
  atualizar.mutate({ id, dados: { ativo: !ativo } });
}
</script>

<template>
  <div class="flex flex-col gap-6 md:gap-8">
    <p class="max-w-2xl text-sm text-zinc-500">
      As categorias classificam cada conta que você lança. É o que faz o resultado do mês
      dizer <strong class="text-zinc-700">onde</strong> o dinheiro foi, e não só quanto saiu —
      e é o que separa o que é gasto do que é compra de mercadoria.
    </p>

    <!-- Nova categoria -->
    <form class="flex flex-wrap items-end gap-3" @submit.prevent="adicionar">
      <div class="w-full sm:w-72">
        <BaseInput v-model="novoNome" label="Nova categoria" placeholder="Ex.: Contador" />
      </div>

      <!-- Botões e não um <select>: são duas opções, e a diferença entre elas
           precisa estar VISÍVEL na hora da escolha. Escondida atrás de um
           dropdown, ninguém descobre que existe — e a classificação errada só
           aparece meses depois, como lucro que não fecha. -->
      <div class="flex flex-col gap-1">
        <span class="text-xs font-medium text-zinc-600">O que é isso?</span>
        <div class="flex rounded-lg border border-zinc-200 p-0.5">
          <button
            v-for="n in NATUREZAS" :key="n.valor"
            type="button"
            class="rounded-md px-3 py-1.5 text-xs font-semibold cursor-pointer"
            :class="
              novoTipo === n.valor
                ? 'bg-brand-primary text-white'
                : 'text-zinc-500 hover:text-zinc-700'
            "
            @click="novoTipo = n.valor"
          >
            {{ n.rotulo }}
          </button>
        </div>
      </div>

      <BaseButton type="submit" variant="primary" :disabled="!novoNome.trim() || criar.isPending.value">
        <Plus :size="16" class="mr-1.5" /> Adicionar
      </BaseButton>
    </form>

    <p class="-mt-3 text-xs text-zinc-400">{{ ajudaDaNatureza }}</p>

    <div v-if="isLoading" class="text-sm text-zinc-500">Carregando…</div>

    <div v-else class="overflow-hidden rounded-2xl border border-zinc-100 bg-white shadow-sm">
      <ul class="divide-y divide-zinc-100">
        <li
          v-for="c in categorias" :key="c.id"
          class="flex flex-wrap items-center gap-3 px-5 py-3.5"
          :class="!c.ativo && 'bg-zinc-50'"
        >
          <!-- Modo edição -->
          <template v-if="editandoId === c.id">
            <div class="w-full sm:w-64">
              <BaseInput v-model="nomeEditado" @keyup.enter="salvarEdicao(c.id)" />
            </div>
            <button type="button" class="p-1.5 text-emerald-600 cursor-pointer" @click="salvarEdicao(c.id)" aria-label="Salvar">
              <Check :size="18" />
            </button>
            <button type="button" class="p-1.5 text-zinc-400 cursor-pointer" @click="editandoId = null" aria-label="Cancelar">
              <X :size="18" />
            </button>
          </template>

          <!-- Modo leitura -->
          <template v-else>
            <button
              type="button"
              class="flex-1 min-w-0 text-left cursor-pointer"
              @click="abrirEdicao(c.id, c.nome)"
            >
              <span class="text-sm font-medium" :class="c.ativo ? 'text-zinc-800' : 'text-zinc-400 line-through'">
                {{ c.nome }}
              </span>
            </button>

            <!-- A natureza é clicável: é assim que a loja corrige uma categoria
                 de compra que estava marcada como despesa, e o lucro dos meses
                 passados se acerta junto. -->
            <button
              type="button"
              class="rounded-full px-2.5 py-0.5 text-[11px] font-semibold cursor-pointer"
              :class="
                c.tipo === 'CUSTO'
                  ? 'bg-amber-50 text-amber-700 hover:bg-amber-100'
                  : c.tipo === 'RECEITA'
                    ? 'bg-emerald-50 text-emerald-700'
                    : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'
              "
              :disabled="c.tipo === 'RECEITA'"
              :title="
                c.tipo === 'CUSTO'
                  ? 'Compra de mercadoria: só entra no lucro quando for vendida. Clique para virar despesa.'
                  : c.tipo === 'RECEITA'
                    ? 'Categoria de entrada'
                    : 'Despesa: sai do lucro no mês em que é paga. Clique para marcar como compra de mercadoria.'
              "
              @click="alternarNatureza(c.id, c.tipo)"
            >
              {{ c.tipo === 'CUSTO' ? 'compra de mercadoria' : c.tipo === 'RECEITA' ? 'receita' : 'despesa' }}
            </button>

            <span v-if="c.em_uso" class="rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-600">
              em uso
            </span>

            <button
              type="button"
              class="text-xs font-semibold cursor-pointer"
              :class="c.ativo ? 'text-zinc-500 hover:text-zinc-700' : 'text-brand-primary'"
              @click="alternarAtivo(c.id, c.ativo)"
            >
              {{ c.ativo ? 'Desativar' : 'Reativar' }}
            </button>
          </template>
        </li>
      </ul>
    </div>

    <div class="flex flex-col gap-1.5 text-xs text-zinc-400">
      <p>
        Categorias desativadas somem dos novos lançamentos, mas continuam valendo nas contas
        antigas — por isso não existe excluir.
      </p>
      <p>
        <strong class="text-zinc-500">Compra de mercadoria</strong> sai do caixa no dia em que
        você paga, e aparece no Fluxo de Caixa — mas só desconta do lucro no dia em que a
        peça for vendida. É o que impede a mesma peça de ser descontada duas vezes.
      </p>
    </div>
  </div>
</template>
