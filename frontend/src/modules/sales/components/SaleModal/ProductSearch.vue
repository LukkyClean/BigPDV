<script setup lang="ts">
import { computed, ref } from 'vue';
import { ArchiveX, Keyboard } from 'lucide-vue-next';

import ShortcutsModal from './ShortcutsModal.vue';
import BaseSearchInput from '@/shared/components/ui/BaseSearchInput/BaseSearchInput.vue';
import ProductOption from './ProductOption.vue';
import AvisoEstoqueNegativoModal from './AvisoEstoqueNegativoModal.vue';

import { useProductSearch } from '../../composables/flows/useProductSearch';
import { useItemModal } from '../../composables/flows/useItemModal';
import { useAddProductModal } from '../../composables/flows/useAddProductModal';
import { SALE_SHORTCUTS, ORCAMENTO_SHORTCUTS } from '../../constants';
import { pareceCodigoDeBarras } from '../../leitorCodigoBarras.util';

import type { ProductSaleRead } from '../../schemas/productSale.schema';

const props = defineProps<{
  saleId: number | null;
  isOrcamento?: boolean;
  currentItems?: ProductSaleRead[];
}>();

const currentItemsRef = computed(() => props.currentItems);
const searchContainerRef = ref<HTMLElement | null>(null);

const {
  searchTerm,
  isSearching,
  products,
  isLoading,
  highlightedIndex,
  handleInputChange,
  handleKeydown: navegarNaLista,
  resetSelection,
  aplicarBuscaAgora,
  tentarAdicionarProduto,
  avisarResultado,
  avisoEstoqueAberto,
  avisoEstoqueDados,
  confirmarAvisoEstoque,
  cancelarAvisoEstoque,
} = useProductSearch(props.isOrcamento, currentItemsRef, searchContainerRef);

const { openCreateItemModal } = useItemModal();

const shortcutsModalIsOpen = ref(false);

function handleAddAvulso() {
  const termo = searchTerm.value.trim();
  resetSelection();
  openCreateItemModal(termo);
}

/** Clique na lista: a mesma porta do teclado e do leitor. */
async function handleAutoAdd(product: { id: number }) {
  const produto = products.value.find((p) => p.id === product.id);
  if (!produto) return;
  avisarResultado(await tentarAdicionarProduto({ saleId: props.saleId, produto }));
}

/**
 * A ponte para a tela de quantidade.
 *
 * Esta busca sempre soma 1 — é o ritmo do balcão. Quando o caso é "3 unidades
 * com desconto", o lugar é a modal Adicionar Produto, que abre já buscando o
 * produto que a pessoa tinha na frente.
 */
const addProductModal = useAddProductModal();

function handleSelectForQuantity(product: { nome: string }) {
  resetSelection();
  addProductModal.openAddProductModal(product.nome);
}

/**
 * O atalho do LEITOR de código de barras.
 *
 * O leitor digita o código todo em milissegundos e manda Enter na sequência —
 * antes da busca debounced (300 ms) sair. Por isso este caminho consulta o
 * serviço DIRETO, sem esperar o debounce.
 *
 * O que mudou: quando ele NÃO resolve, o Enter deixou de morrer. Antes o fluxo
 * caía numa lista que ainda não existia (o debounce nem tinha disparado) e o
 * operador ficava sem resposta nenhuma. Agora a busca é publicada na hora
 * (`aplicarBuscaAgora`) e o primeiro resultado já nasce destacado — então o
 * Enter seguinte escolhe, sem seta e sem mouse.
 */
const bipando = ref(false);

async function handleKeydown(e: KeyboardEvent) {
  // Tab vai para a quantidade do ÚLTIMO item — o que acabou de ser bipado.
  //
  // "Bipei, agora são 3" é o passo seguinte mais comum do balcão, e ele só
  // existia no mouse: o Tab andava para os botões da barra e a quantidade era
  // um texto, sem onde pousar. Com o carrinho vazio não há o que ajustar, então
  // o Tab segue o caminho normal.
  if (e.key === 'Tab' && !e.shiftKey) {
    const qtd = document.querySelector<HTMLInputElement>('[data-qtd-ultimo]');
    if (qtd) {
      e.preventDefault();
      qtd.focus();
    }
    return;
  }

  if (e.key === 'Enter') {
    const termo = searchTerm.value.trim();
    const pareceBipada = pareceCodigoDeBarras(searchTerm.value);

    // Com a lista na tela e um item destacado, o Enter é ESCOLHA, não busca.
    // Ir ao servidor aqui atrasaria o que já está resolvido na frente do
    // operador — e é esse caminho que a seta + Enter usa.
    const temEscolhaNaTela = (products.value?.length ?? 0) > 0 && highlightedIndex.value >= 0;

    // Resolver por código EXATO é seguro para qualquer texto: `impressora` não
    // bate literalmente com nenhum `codigo_barras` nem `sku`. Antes esta porta
    // só abria para código só-de-dígitos, e um código alfanumérico bipado caía
    // no caminho de quem digita: o Enter do leitor chegava antes da busca sair e
    // morria, obrigando um segundo Enter. Mesmo gesto, dois comportamentos, e
    // nada na tela explicando — o operador conclui que "o leitor às vezes falha".
    if (termo && (pareceBipada || !temEscolhaNaTela)) {
      e.preventDefault();
      if (bipando.value) return;

      bipando.value = true;
      let resultado;
      try {
        resultado = await tentarAdicionarProduto({ saleId: props.saleId, termo });
      } finally {
        bipando.value = false;
      }

      // O toast de "não achei" continua sendo só do ramo numérico, onde a
      // intenção de bipar é inequívoca. Quem digitou um pedaço do nome e apertou
      // Enter cedo demais não errou nada — ali a LISTA é a resposta, e um aviso
      // de erro por cima dela seria mentira. Falha de rede e recusa de estoque
      // falam sempre, nos dois ramos.
      const silenciar =
        !pareceBipada && (resultado.tipo === 'not_found' || resultado.tipo === 'ambiguous');
      if (!silenciar) avisarResultado(resultado);

      // Sem certeza sobre o código: a lista assume, e assume AGORA.
      if (resultado.tipo === 'not_found' || resultado.tipo === 'ambiguous') {
        aplicarBuscaAgora();
      }
      return;
    }
  }

  const escolhido = navegarNaLista(e);
  if (escolhido) {
    avisarResultado(await tentarAdicionarProduto({ saleId: props.saleId, produto: escolhido }));
  }
}
</script>

<template>
  <AvisoEstoqueNegativoModal
    :is-open="avisoEstoqueAberto"
    :nome-produto="avisoEstoqueDados?.nome ?? ''"
    :estoque-atual="avisoEstoqueDados?.estoqueAtual ?? 0"
    :quantidade-desejada="avisoEstoqueDados?.quantidadeDesejada ?? 1"
    @confirmar="confirmarAvisoEstoque"
    @cancelar="cancelarAvisoEstoque"
  />
  <div class="flex items-center gap-2 w-full">
    <!-- Campo de busca + dropdown -->
    <div class="relative flex-1" data-search-products ref="searchContainerRef">
      <BaseSearchInput
        v-model="searchTerm"
        placeholder="Digite o nome ou código do produto"
        @focusChange="handleInputChange"
        @keydown="handleKeydown"
      />

      <div
        v-if="isSearching"
        class="absolute left-0 top-full z-9999 mt-2 w-full min-h-20 rounded-xl shadow-lg bg-zinc-50"
      >
        <div
          :class="[
            'w-full py-3 px-6 select-none',
            products?.length ? 'border-b-2 border-zinc-200' : '',
          ]"
        >
          <p class="font-poppins font-semibold text-[10px] uppercase text-mid-gray">
            {{ `Produtos encontrados (${products?.length || 0})` }}
          </p>
        </div>

        <div class="w-full min-h-20 max-h-80 overflow-y-auto bg-white flex items-center justify-center">
          <div
            v-if="isLoading"
            class="h-8 w-8 animate-spin rounded-full border-4 border-zinc-300 border-t-brand-primary"
          />
          <div v-else-if="products?.length == 0" class="py-5 flex flex-col items-center">
            <ArchiveX :size="30" class="text-mid-gray" />
            <p class="mt-1 font-poppins font-semibold text-xs text-mid-gray">
              Nenhum produto encontrado
            </p>
          </div>
          <div v-else class="w-full">
            <ProductOption
              v-for="(product, index) in products"
              :key="product.id"
              :product="product"
              :highlighted="highlightedIndex === index"
              :data-product-index="index"
              @click="handleAutoAdd(product)"
              @select-for-quantity="handleSelectForQuantity(product)"
            />
          </div>
        </div>

        <div class="w-full py-3 px-6">
          <p class="font-poppins font-bold text-[10px] text-mid-gray">
            Não encontrou o produto?
            <span
              class="font-poppins font-semibold text-[10px] text-brand-primary/90 hover:underline cursor-pointer"
              @click="handleAddAvulso"
            >
              Adicionar produto avulso
              <kbd
                class="ml-1 inline-flex items-center rounded border border-zinc-300 bg-zinc-100 px-1 text-[9px] font-semibold text-zinc-500"
              >F4</kbd>
            </span>
          </p>
        </div>
      </div>
    </div>

    <!-- Botão de atalhos -->
    <button
      type="button"
      class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-zinc-200 text-zinc-400 hover:bg-brand-primary/10 hover:text-brand-primary hover:border-brand-primary/30 transition-all cursor-pointer"
      title="Atalhos do teclado"
      @click="shortcutsModalIsOpen = true"
    >
      <Keyboard :size="16" />
    </button>

    <ShortcutsModal
      :is-open="shortcutsModalIsOpen"
      :shortcuts="isOrcamento ? ORCAMENTO_SHORTCUTS : SALE_SHORTCUTS"
      @close="shortcutsModalIsOpen = false"
    />
  </div>
</template>
