<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref } from 'vue';
import { Trash2, Minus, Plus, PackagePlus } from 'lucide-vue-next';

import { formatCurrency } from '@/shared/utils/finance';
import AvisoEstoqueNegativoModal from './AvisoEstoqueNegativoModal.vue';

import {
  useUpdateItemSaleMutation,
  useDeleteItemSaleMutation,
} from '../../composables/mutates/useItemSaleMutation';
import {
  useUpdateItemOrcamentoMutation,
  useDeleteItemOrcamentoMutation,
} from '../../composables/mutates/useItemOrcamentoMutation';

import { useItemModal } from '../../composables/flows/useItemModal';
import { focarBuscaDeProduto } from '../../focarBusca.util';

import type { SaleRead } from '../../schemas/sale.schema';
import type { OrcamentoRead } from '../../schemas/orcamento.schema';
import { getBackendBaseUrl } from '@/api/backendUrl';

type SaleOrOrcamento = SaleRead | OrcamentoRead;

const props = defineProps<{
  sale: SaleOrOrcamento | undefined;
  readonly?: boolean;
  isOrcamento?: boolean;
}>();

const { openEditItemModal } = useItemModal();

const avisoEstoqueOpen = ref(false);
const pendingItem = ref<SaleOrOrcamento['produtos'][number] | null>(null);
const pendingQuantidade = ref<number | null>(null);

const updateSaleMut = useUpdateItemSaleMutation();
const deleteSaleMut = useDeleteItemSaleMutation();
const updateOrcMut = useUpdateItemOrcamentoMutation();
const deleteOrcMut = useDeleteItemOrcamentoMutation();

const isDeleting = computed(() => props.isOrcamento ? deleteOrcMut.isPending.value : deleteSaleMut.isPending.value);

const items = computed(() => props.sale?.produtos ?? []);

function getProductDescription(item: SaleOrOrcamento['produtos'][number]) {
  if (item.tipo_produto === 'AVULSO') {
    return 'Produto avulso';
  }

  return item.produto_id ? `SKU: #${item.sku}` : 'Produto cadastrado';
}

function mutateUpdate(
  entityId: number,
  productId: number,
  payload: { quantidade: number },
  opcoes?: { onSettled?: () => void },
) {
  if (props.isOrcamento) {
    updateOrcMut.mutate({ orcamentoId: entityId, productId, payload }, opcoes);
  } else {
    updateSaleMut.mutate({ saleId: entityId, productId, payload }, opcoes);
  }
}

function mutateDelete(entityId: number, productId: number) {
  if (props.isOrcamento) {
    deleteOrcMut.mutate({ orcamentoId: entityId, productId });
  } else {
    deleteSaleMut.mutate({ saleId: entityId, productId });
  }
}

/**
 * A quantidade que a TELA mostra — a local, se houver, senão a do servidor.
 *
 * Antes cada clique no `+` era uma requisição, e enquanto ela estava no ar os
 * botões ficavam desabilitados (`isUpdating`) — para a tabela inteira. Clicar
 * rápido, que é o que se faz para chegar em 10, jogava os cliques seguintes no
 * vazio, sem nada na tela dizendo por quê. O operador conclui que "não pegou".
 *
 * Agora o número muda na hora e a gravação sai UMA vez, depois que a mão para.
 */
const quantidadesLocais = ref<Record<number, number>>({});
const gravacoesAgendadas = new Map<number, ReturnType<typeof setTimeout>>();

/** Espera curta o bastante para não parecer travado, longa o bastante para juntar cliques. */
const ESPERA_GRAVACAO = 350;

function quantidadeVisivel(item: SaleOrOrcamento['produtos'][number]) {
  return quantidadesLocais.value[item.id] ?? item.quantidade;
}

function agendarGravacao(item: SaleOrOrcamento['produtos'][number]) {
  const anterior = gravacoesAgendadas.get(item.id);
  if (anterior) clearTimeout(anterior);
  gravacoesAgendadas.set(item.id, setTimeout(() => gravarQuantidade(item), ESPERA_GRAVACAO));
}

function gravarQuantidade(item: SaleOrOrcamento['produtos'][number]) {
  gravacoesAgendadas.delete(item.id);
  if (!props.sale?.id) return;

  const nova = quantidadesLocais.value[item.id];
  if (nova === undefined) return;
  if (nova === item.quantidade) {
    delete quantidadesLocais.value[item.id];
    return;
  }

  // O valor local sai de cena quando a resposta chega — na boa, o cache já traz
  // o número novo; no erro, a tela volta sozinha para a verdade do servidor em
  // vez de continuar exibindo um número que não existe.
  mutateUpdate(props.sale.id, item.id, { quantidade: nova }, {
    onSettled: () => {
      delete quantidadesLocais.value[item.id];
    },
  });
}

function gravarAgora(item: SaleOrOrcamento['produtos'][number]) {
  const agendada = gravacoesAgendadas.get(item.id);
  if (agendada) clearTimeout(agendada);
  gravarQuantidade(item);
}

onUnmounted(() => {
  gravacoesAgendadas.forEach((t) => clearTimeout(t));
  gravacoesAgendadas.clear();
});

/**
 * A porta única da quantidade — `+`, `−` e o número digitado passam por aqui.
 *
 * A regra de estoque morava dentro do `+`. Quem digitasse a quantidade pelo
 * teclado furaria, sem querer, uma trava que o mouse obedece.
 */
function aplicarQuantidade(
  item: SaleOrOrcamento['produtos'][number],
  nova: number,
  opcoes: { ignorarEstoque?: boolean } = {},
) {
  if (props.readonly) return;
  if (!props.sale?.id) return;
  if (nova < 1) return;

  const atual = quantidadeVisivel(item);
  const estoque = item.estoque_disponivel;

  // Só o AUMENTO consulta o estoque. Reduzir nunca pode ser barrado — senão um
  // item que já está acima do disponível não conseguiria nem VOLTAR.
  if (!opcoes.ignorarEstoque && nova > atual && estoque !== null && estoque !== undefined && nova > estoque) {
    pendingItem.value = item;
    pendingQuantidade.value = nova;
    avisoEstoqueOpen.value = true;
    return;
  }

  quantidadesLocais.value[item.id] = nova;
  agendarGravacao(item);
}

function decreaseQuantity(item: SaleOrOrcamento['produtos'][number]) {
  const atual = quantidadeVisivel(item);
  if (atual <= 1) return;
  aplicarQuantidade(item, atual - 1);
}

function increaseQuantity(item: SaleOrOrcamento['produtos'][number]) {
  aplicarQuantidade(item, quantidadeVisivel(item) + 1);
}

function confirmarIncremento() {
  const item = pendingItem.value;
  const desejada = pendingQuantidade.value;
  fecharAviso();
  if (!item || desejada === null) return;
  // A quantidade desejada vem do que foi PEDIDO — digitar 12 não pode virar +1.
  aplicarQuantidade(item, desejada, { ignorarEstoque: true });
}

function fecharAviso() {
  avisoEstoqueOpen.value = false;
  pendingItem.value = null;
  pendingQuantidade.value = null;
}

/**
 * Digitar a quantidade direto na linha.
 *
 * O número era um `<span>`: de 1 para 12 eram onze cliques no `+`, e não havia
 * onde o teclado pousar.
 *
 * ⚠️ O Enter devolve o foco à busca de propósito, e isso é segurança, não
 * conforto: com o cursor parado na quantidade, a próxima bipada digitaria o
 * código de barras inteiro dentro do campo de quantidade.
 */
const editandoId = ref<number | null>(null);
const valorEditado = ref('');

function iniciarEdicao(item: SaleOrOrcamento['produtos'][number]) {
  if (props.readonly) return;
  editandoId.value = item.id;
  valorEditado.value = String(quantidadeVisivel(item));
}

function cancelarEdicao() {
  editandoId.value = null;
  valorEditado.value = '';
}

/**
 * Fecha o ciclo do teclado na venda: busca → quantidade → Finalizar → busca.
 *
 * Sem isto o Tab saía da quantidade para a ordem do HTML — os botões da linha
 * de baixo, depois desconto, entrega — e o operador perdia de vista onde estava
 * no meio de um atendimento. Três paradas, sempre as mesmas, sempre na mesma
 * ordem: é isso que deixa o caminho decorável.
 */
function focarIrParaPagamento() {
  nextTick(() => {
    const btn = document.querySelector<HTMLButtonElement>('[data-ir-pagamento]');
    // Carrinho vazio deixa o botão desabilitado; aí o Tab segue o caminho normal.
    if (btn && !btn.disabled) btn.focus();
  });
}

type DestinoDoFoco = 'busca' | 'pagamento' | null;

function confirmarEdicao(item: SaleOrOrcamento['produtos'][number], destino: DestinoDoFoco = null) {
  // O Enter já confirmou e limpou o estado; o blur que vem atrás não repete.
  if (editandoId.value !== item.id) return;

  const bruto = valorEditado.value.trim().replace(',', '.');
  cancelarEdicao();

  const nova = Number(bruto);
  // Valor vazio ou sem sentido não apaga o item nem zera a linha: fica como estava.
  if (bruto && !Number.isNaN(nova) && nova > 0 && nova !== quantidadeVisivel(item)) {
    aplicarQuantidade(item, nova);
    // Enter e Tab são "acabei": gravam na hora, sem esperar os 350 ms. Sair com
    // o mouse (blur) espera, porque ali ninguém disse que terminou.
    if (destino) gravarAgora(item);
  }

  if (destino === 'busca') focarBuscaDeProduto();
  if (destino === 'pagamento') focarIrParaPagamento();
}

function abandonarEdicao() {
  cancelarEdicao();
  focarBuscaDeProduto();
}

function removeItem(item: SaleOrOrcamento['produtos'][number]) {
  if (props.readonly) return;
  if (!props.sale?.id) return;

  mutateDelete(props.sale.id, item.id);
}
</script>

<template>
  <AvisoEstoqueNegativoModal
    :is-open="avisoEstoqueOpen"
    :nome-produto="pendingItem?.nome ?? ''"
    :estoque-atual="pendingItem?.estoque_disponivel ?? 0"
    :quantidade-desejada="pendingQuantidade ?? 1"
    @confirmar="confirmarIncremento"
    @cancelar="fecharAviso"
  />
  <section class="w-full h-full overflow-hidden rounded-xl border border-zinc-200 bg-white hover:border-brand-primary/30 transition-colors flex flex-col">
    <div class="flex-1 min-h-0 overflow-y-auto no-scrollbar">
      <table class="w-full border-collapse text-sm">
        <thead class="sticky top-0 z-10 bg-zinc-50">
          <tr
            class="h-12 border-b border-zinc-200 bg-zinc-50 text-left text-[11px] font-bold uppercase text-zinc-600"
          >
            <th class="px-5">Produto</th>
            <th class="w-16 px-2 text-center">Un.</th>
            <th class="w-32.5 px-4 text-center">Qtde.</th>
            <th class="w-37.5 px-4 text-center">Preço unit.</th>
            <th class="w-35 px-4 text-center">Desconto</th>
            <th class="w-35 px-4 text-right">Total</th>
            <th v-if="!readonly" class="w-18 px-4 text-center"></th>
          </tr>
        </thead>
        <tbody class="max-h-96 overflow-y-scroll">
          <tr v-if="items.length === 0">
            <td :colspan="readonly ? 6 : 7" class="px-6 py-8">
              <div class="mx-auto flex max-w-sm flex-col items-center justify-center text-center">
                <div class="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-brand-primary">
                  <PackagePlus class="h-5 w-5" />
                </div>
                <h3 class="text-sm font-bold text-zinc-800">Nenhum produto adicionado</h3>
                <p class="mt-1 text-xs leading-5 text-zinc-400">
                  Use a busca acima para localizar um produto pelo nome, SKU ou código de barras.
                </p>
              </div>
            </td>
          </tr>

          <tr
            v-for="(item, index) in items"
            :key="item.id"
            class="h-23 border-b border-zinc-100 last:border-b-0 hover:bg-zinc-50/70 hover:cursor-pointer"
            @click="openEditItemModal(item)"
          >
            <td class="px-5">
              <div class="flex items-center gap-4">
                <div
                  class="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-zinc-200 bg-zinc-100"
                >
                  <img
                    v-if="'imagem_url' in item && item.imagem_url"
                    :src="`${getBackendBaseUrl()}/${item.imagem_url}`"
                    :alt="item.nome"
                    class="h-full w-full object-fit"
                  />

                  <span v-else class="text-xs font-semibold text-zinc-400">
                    {{ item.nome.charAt(0).toUpperCase() }}
                  </span>
                </div>

                <div class="min-w-0">
                  <p class="truncate text-sm font-bold text-zinc-900">
                    {{ item.nome }}
                  </p>

                  <p class="mt-0.5 truncate text-xs text-zinc-500">
                    {{ getProductDescription(item) }}
                  </p>

                </div>
              </div>
            </td>

            <td class="px-2 text-center">
              <span
                v-if="'unidade_medida' in item && item.unidade_medida"
                class="inline-block px-1.5 py-0.5 text-[10px] font-semibold rounded bg-zinc-100 text-zinc-500 uppercase"
              >
                {{ item.unidade_medida }}
              </span>
              <span v-else class="text-xs text-zinc-300">—</span>
            </td>

            <td class="px-4 text-center">
              <div
                class="mx-auto flex h-10 w-28 items-center justify-between rounded-lg border border-zinc-200 bg-white px-2 shadow-sm"
              >
                <button
                  type="button"
                  :disabled="readonly || quantidadeVisivel(item) <= 1"
                  class="flex h-7 w-7 items-center justify-center rounded-md text-zinc-500 transition hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-40"
                  @click.stop="decreaseQuantity(item)"
                >
                  <Minus class="h-4 w-4" />
                </button>

                <input
                  v-if="!readonly"
                  type="text"
                  inputmode="numeric"
                  :value="editandoId === item.id ? valorEditado : quantidadeVisivel(item)"
                  :data-qtd-ultimo="index === items.length - 1 ? '' : undefined"
                  class="min-w-6 w-12 text-center text-sm font-semibold text-zinc-800 bg-transparent outline-none z-99"
                  @click.stop
                  @focus="iniciarEdicao(item); ($event.target as HTMLInputElement).select()"
                  @input="valorEditado = ($event.target as HTMLInputElement).value"
                  @keydown.enter.prevent="confirmarEdicao(item, 'busca')"
                  @keydown.tab.exact.prevent="confirmarEdicao(item, 'pagamento')"
                  @keydown.esc.prevent="abandonarEdicao()"
                  @blur="confirmarEdicao(item)"
                />
                <span v-else class="min-w-6 text-center text-sm font-semibold text-zinc-800 select-none z-99">
                  {{ quantidadeVisivel(item) }}
                </span>

                <button
                  type="button"
                  :disabled="readonly"
                  class="flex h-7 w-7 items-center justify-center rounded-md text-zinc-500 transition hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-40"
                  @click.stop="increaseQuantity(item)"
                >
                  <Plus class="h-4 w-4" />
                </button>
              </div>
            </td>

            <td class="px-4 text-center text-sm font-medium text-zinc-700">
              {{ formatCurrency(item.valor_unitario) }}
            </td>

            <td class="px-4 text-center text-sm font-medium text-zinc-700">
              {{ formatCurrency(item.desconto) }}
            </td>

            <td class="px-4 text-right text-sm font-semibold text-zinc-800">
              {{ formatCurrency(item.total) }}
            </td>

            <td v-if="!readonly" class="px-4 text-center">
              <button
                type="button"
                :disabled="isDeleting"
                class="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-zinc-200 bg-white text-zinc-500 shadow-sm transition hover:border-red-200 hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-50"
                @click.stop="removeItem(item)"
              >
                <Trash2 class="h-4 w-4" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
