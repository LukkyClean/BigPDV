<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import { PackageSearch, ArchiveX, ShoppingCart, Plus, Minus, Check, PackagePlus } from 'lucide-vue-next';
import BaseModal from '@/shared/components/commons/BaseModal/BaseModal.vue';
import BaseButton from '@/shared/components/ui/BaseButton/BaseButton.vue';
import BaseSearchInput from '@/shared/components/ui/BaseSearchInput/BaseSearchInput.vue';
import AvisoEstoqueNegativoModal from './AvisoEstoqueNegativoModal.vue';

import { useProductSearch } from '../../composables/flows/useProductSearch';
import { useItemModal } from '../../composables/flows/useItemModal';
import { formatCurrency } from '@/shared/utils/finance';
import { getImageUrl } from '@/shared/utils/print.utils';
import type { ProductSaleRead } from '../../schemas/productSale.schema';

const props = defineProps<{
  isOpen: boolean;
  saleId: number | null;
  isOrcamento?: boolean;
  currentItems?: ProductSaleRead[];
  /** Termo com que a modal abre já buscando, vindo da busca rápida. */
  termoInicial?: string;
}>();

const emit = defineEmits<{
  close: [];
}>();

const currentItemsRef = computed(() => props.currentItems);
const searchContainerRef = ref<HTMLElement | null>(null);

const {
  searchTerm,
  products,
  isLoading,
  highlightedIndex,
  selectedProductId,
  selectedProductName,
  selectedProduct,
  canAddItem,
  isAddingItem,
  quantity,
  desconto,
  totalItem,
  handleInputChange,
  handleKeydown: navegarNaLista,
  selectProduct,
  increaseQuantity,
  decreaseQuantity,
  resetSelection,
  tentarAdicionarProduto,
  avisarResultado,
  avisoEstoqueAberto,
  avisoEstoqueDados,
  confirmarAvisoEstoque,
  cancelarAvisoEstoque,
} = useProductSearch(props.isOrcamento, currentItemsRef, searchContainerRef);

watch(
  () => props.isOpen,
  (open) => {
    if (!open) {
      resetSelection();
      return;
    }
    // Chegou pela ponte da busca rápida: já vem com o termo, não faz o
    // operador digitar de novo.
    if (props.termoInicial) searchTerm.value = props.termoInicial;
    focarBusca();
  },
);

/**
 * Põe o cursor na busca — e confere que ele ficou lá.
 *
 * O `BaseModal` abre dentro de um `<Transition>`, e o atalho que traz até aqui
 * é uma tecla que o WebView2 também escuta. Entre uma coisa e outra, houve mais
 * de um jeito de a tela abrir com o foco em lugar nenhum — e uma tela de busca
 * sem cursor obriga a mão a sair do teclado, que é justamente o que este atalho
 * existe para evitar.
 *
 * Por isso a segunda tentativa no quadro seguinte: barata, e cobre o caso em que
 * o `nextTick` chegou antes de o elemento estar focável.
 */
function focarBusca() {
  const tentar = () => {
    const input = searchContainerRef.value?.querySelector('input');
    if (!input) return false;
    input.focus();
    return document.activeElement === input;
  };

  nextTick(() => {
    if (tentar()) return;
    requestAnimationFrame(() => void tentar());
  });
}

/**
 * O teclado que esta tela nunca teve.
 *
 * Ela nasceu para o caso "3 unidades com desconto" e saiu só com mouse: sem
 * seta, sem Enter. Quem abria aqui era obrigado a largar o teclado no meio da
 * venda — e o atalho que traz até aqui (F3) não valeria nada se a tela do outro
 * lado exigisse a mão no mouse.
 *
 * Enter na LISTA seleciona (e não adiciona): aqui a quantidade é o motivo de a
 * tela existir, então pular direto para o carrinho passaria por cima dela. Com
 * o produto já selecionado, Enter adiciona.
 */
async function handleSearchKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && selectedProductId.value) {
    e.preventDefault();
    await handleAdd();
    return;
  }

  const escolhido = navegarNaLista(e);
  if (escolhido) selectProduct(escolhido.nome, escolhido.id);
}

/**
 * Do painel do item, o Tab vai direto para o "Adicionar ao Carrinho".
 *
 * Sozinho, o Tab andava pela ORDEM DO HTML: da quantidade ele caía no botão
 * "+", e do desconto ainda passava por "Produto avulso" e "Fechar" antes de
 * chegar no que o operador quer. Digitou a quantidade, a próxima ação é
 * confirmar — o resto é caminho.
 *
 * Shift+Tab continua o de sempre, e é ele que mantém o desconto alcançável:
 * voltando do botão, o campo anterior é justamente o desconto. Por isso aqui
 * só o Tab para FRENTE é desviado.
 *
 * Se o botão estiver desabilitado (desconto maior que o total, por exemplo),
 * o Tab segue o caminho normal — desviar o foco para um botão que não aceita
 * seria devolver o operador ao mouse, que é o oposto do que isto faz.
 */
function avancarParaConfirmar(e: KeyboardEvent) {
  if (e.key !== 'Tab' || e.shiftKey) return;

  const btn = document.querySelector<HTMLButtonElement>('[data-adicionar-carrinho]');
  if (!btn || btn.disabled) return;

  e.preventDefault();
  btn.focus();
}

/**
 * O Tab do último botão volta para a busca, fechando o ciclo da tela.
 *
 * Sem isto o foco SAÍA da modal: o Tab seguia para a venda que está atrás e o
 * marcador simplesmente sumia da vista. Quem estava adicionando três itens
 * seguidos perdia o lugar e voltava ao mouse para achar a busca de novo.
 *
 * Com o ciclo fechado a tela inteira cabe num dedo: busca → quantidade →
 * Adicionar → busca de novo, na ordem em que se adiciona item atrás de item.
 *
 * O "Fechar" só assume a volta quando o "Adicionar ao Carrinho" não está na
 * tela (nenhum produto selecionado) — com ele visível, o Tab do Fechar segue
 * para lá, que é o passo seguinte de verdade.
 */
function ciclarParaBusca(e: KeyboardEvent) {
  if (e.key !== 'Tab' || e.shiftKey) return;

  const confirmar = document.querySelector<HTMLButtonElement>('[data-adicionar-carrinho]');
  if (confirmar && e.currentTarget !== confirmar) return;

  e.preventDefault();
  focarBusca();
}

function getEstoqueStatus(product: { estoque: number; quantidade_minima?: number | null }) {
  if (product.estoque <= 0) return 'sem_estoque';
  if (product.quantidade_minima != null && product.estoque <= product.quantidade_minima) return 'baixo';
  return 'normal';
}

// Selecionar não é adicionar: aqui a seleção só abre o painel de quantidade.
// Produto zerado passa a poder ser selecionado — quem decide se ele entra no
// carrinho é `tentarAdicionarProduto`, com a configuração da loja na mão.
function handleProductClick(product: { nome: string; id: number }) {
  selectProduct(product.nome, product.id);
}

/**
 * Adicionar ao carrinho — pela mesma porta do leitor e da busca rápida.
 *
 * A regra de estoque que morava aqui era uma segunda escrita da mesma decisão,
 * e as duas já tinham deixado de ser idênticas. Agora esta função só junta o
 * que a tela sabe (produto, quantidade, desconto) e entrega.
 */
async function handleAdd() {
  const produto = products.value?.find((p) => p.id === selectedProductId.value) ?? selectedProduct.value;
  if (!produto) return;

  avisarResultado(
    await tentarAdicionarProduto({
      saleId: props.saleId,
      produto,
      quantidade: quantity.value,
      desconto: desconto.value,
    }),
  );
}

// Saída para item fora do catálogo. Sem isto, este modal era beco sem saída:
// o produto não existe e não há nada a fazer além de fechar. O mesmo atalho já
// existia na busca inline (ProductSearch), só faltava aqui.
const { openCreateItemModal } = useItemModal();

function handleAddAvulso() {
  // Leva o termo digitado como descrição inicial — quem buscou "cabo hdmi" e
  // não achou não deve ter que digitar de novo.
  const termo = searchTerm.value.trim();
  emit('close');
  openCreateItemModal(termo);
}
</script>

<template>
  <BaseModal :is-open="isOpen" title="Adicionar Produto" size="2xl" @close="emit('close')">
    <!-- Área de busca + lista: tudo dentro do searchContainerRef para não disparar onClickOutside ao clicar nos produtos -->
    <div ref="searchContainerRef" class="flex flex-col gap-3">
      <BaseSearchInput
        v-model="searchTerm"
        placeholder="Buscar por nome, código ou SKU..."
        @focusChange="handleInputChange"
        @keydown="handleSearchKeydown"
      />

      <!-- Lista de produtos -->
      <div
        class="rounded-xl border border-zinc-200 overflow-hidden overflow-y-auto transition-all"
        :style="selectedProductId ? 'min-height: 0; max-height: 180px' : 'min-height: 260px; max-height: 50vh'"
      >
        <!-- Carregando -->
        <div v-if="isLoading" class="flex items-center justify-center py-16">
          <div class="h-8 w-8 animate-spin rounded-full border-4 border-zinc-300 border-t-brand-primary" />
        </div>

        <!-- Estado inicial -->
        <div
          v-else-if="!searchTerm.trim()"
          class="flex flex-col items-center justify-center py-16 gap-3 text-zinc-400"
        >
          <PackageSearch :size="40" class="opacity-50" />
          <div class="text-center">
            <p class="text-sm font-semibold text-zinc-500">Digite para buscar</p>
            <p class="text-xs text-zinc-400 mt-0.5">Busque por nome, SKU ou código de barras</p>
          </div>
        </div>

        <!--
          Sem resultados: é o momento exato em que o avulso é a resposta. Em vez
          de só informar o fracasso, oferece a saída com o termo já digitado.
        -->
        <div
          v-else-if="products.length === 0"
          class="flex flex-col items-center justify-center py-14 gap-3 text-zinc-400"
        >
          <ArchiveX :size="40" class="opacity-50" />
          <div class="text-center">
            <p class="text-sm font-semibold text-zinc-500">Nenhum produto encontrado</p>
            <p class="text-xs text-zinc-400 mt-0.5">
              "{{ searchTerm }}" não está no catálogo
            </p>
          </div>
          <BaseButton variant="primary" class="gap-2 mt-1" @click="handleAddAvulso">
            <PackagePlus :size="16" />
            Adicionar como produto avulso
          </BaseButton>
        </div>

        <!-- Linhas de produto -->
        <div
          v-for="(product, index) in products"
          :key="product.id"
          :data-product-index="index"
          :class="[
            'flex items-center gap-4 px-4 py-3 border-b border-zinc-100 last:border-b-0 transition-colors select-none cursor-pointer',
            selectedProductId === product.id
              ? 'bg-brand-primary/5'
              : highlightedIndex === index
              ? 'bg-brand-primary/5 ring-1 ring-inset ring-brand-primary/40'
              : 'hover:bg-zinc-50',
            product.estoque <= 0 ? 'bg-zinc-50/70' : '',
          ]"
          @click="handleProductClick(product)"
        >
          <!-- Thumbnail -->
          <div
            class="h-12 w-12 shrink-0 rounded-lg overflow-hidden border border-zinc-200 bg-zinc-100 flex items-center justify-center"
          >
            <img
              v-if="product.imagem_url"
              :src="getImageUrl(product.imagem_url) ?? ''"
              :alt="product.nome"
              class="h-full w-full object-cover"
            />
            <span v-else class="text-base font-bold text-zinc-400">
              {{ product.nome.charAt(0).toUpperCase() }}
            </span>
          </div>

          <!-- Nome + SKU -->
          <div class="flex-1 min-w-0">
            <p
              :class="[
                'text-sm font-semibold truncate',
                selectedProductId === product.id ? 'text-brand-primary' : 'text-zinc-800',
              ]"
            >
              {{ product.nome }}
            </p>
            <p class="text-xs text-zinc-400 mt-0.5">SKU: {{ product.sku ?? '—' }}</p>
          </div>

          <!-- Badge de estoque -->
          <span
            :class="[
              'px-2 py-1 rounded-md text-[11px] font-semibold shrink-0',
              getEstoqueStatus(product) === 'sem_estoque'
                ? 'bg-red-100 text-red-600'
                : getEstoqueStatus(product) === 'baixo'
                ? 'bg-orange-100 text-orange-600'
                : 'bg-blue-50 text-blue-600',
            ]"
          >
            {{ product.estoque <= 0 ? 'Sem estoque' : `${product.estoque} em estoque` }}
          </span>

          <!-- Preço -->
          <p class="text-base font-bold text-brand-primary shrink-0 w-24 text-right">
            {{ formatCurrency(product.preco) }}
          </p>

          <!-- Indicador de selecionado -->
          <div
            :class="[
              'w-6 h-6 shrink-0 rounded-full flex items-center justify-center transition-colors',
              selectedProductId === product.id ? 'bg-brand-primary' : 'bg-zinc-100',
            ]"
          >
            <Check
              :size="12"
              :class="selectedProductId === product.id ? 'text-white' : 'text-zinc-300'"
            />
          </div>
        </div>
      </div>

      <!-- Painel de detalhes (aparece ao selecionar produto) -->
      <div v-if="selectedProductId" class="rounded-xl border border-zinc-200 bg-zinc-50 p-4">
        <!-- Cabeçalho: nome + estoque -->
        <div class="flex items-center justify-between mb-4">
          <div class="min-w-0">
            <p class="text-[11px] font-semibold uppercase tracking-wide text-zinc-400">Produto selecionado</p>
            <p class="text-sm font-semibold text-zinc-800 truncate">{{ selectedProductName }}</p>
          </div>
          <div class="text-right shrink-0 ml-4">
            <p class="text-[11px] font-semibold uppercase tracking-wide text-zinc-400">Estoque disp.</p>
            <p class="text-sm font-bold text-zinc-700">{{ selectedProduct?.estoque ?? 0 }} un.</p>
          </div>
        </div>

        <!-- Grid de campos -->
        <div class="grid grid-cols-4 gap-3">
          <!-- Valor unitário (somente leitura) -->
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-wide text-zinc-400 mb-1.5">Valor unit.</p>
            <div class="h-9 bg-white border border-zinc-200 rounded-lg flex items-center px-3">
              <span class="text-sm font-semibold text-zinc-600">{{ formatCurrency(selectedProduct?.preco ?? 0) }}</span>
            </div>
          </div>

          <!-- Quantidade -->
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-wide text-zinc-400 mb-1.5">Quantidade</p>
            <div class="flex items-center border border-zinc-200 rounded-lg overflow-hidden bg-white h-9">
              <button
                type="button"
                tabindex="-1"
                :disabled="quantity <= 1"
                class="w-8 h-full flex items-center justify-center text-zinc-400 hover:bg-zinc-100 disabled:opacity-30 transition-colors"
                @click="decreaseQuantity"
              >
                <Minus :size="13" />
              </button>
              <input
                v-model.number="quantity"
                type="number"
                min="1"
                @keydown="avancarParaConfirmar"
                class="flex-1 min-w-0 text-center text-sm font-bold text-zinc-800 bg-transparent outline-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
              />
              <button
                type="button"
                tabindex="-1"
                class="w-8 h-full flex items-center justify-center text-zinc-400 hover:bg-zinc-100 transition-colors"
                @click="increaseQuantity"
              >
                <Plus :size="13" />
              </button>
            </div>
          </div>

          <!-- Desconto -->
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-wide text-zinc-400 mb-1.5">Desconto (R$)</p>
            <div
              class="flex items-center gap-1 border rounded-lg bg-white h-9 px-3"
              :class="desconto > (selectedProduct?.preco ?? 0) * quantity ? 'border-red-400' : 'border-zinc-200'"
            >
              <span class="text-xs text-zinc-400 shrink-0">R$</span>
              <input
                v-model.number="desconto"
                type="number"
                min="0"
                step="0.01"
                @keydown="avancarParaConfirmar"
                class="flex-1 min-w-0 text-sm text-zinc-700 bg-transparent outline-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
              />
            </div>
          </div>

          <!-- Total -->
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-wide text-zinc-400 mb-1.5">Total</p>
            <div class="h-9 bg-brand-primary rounded-lg flex items-center justify-center px-3">
              <span class="text-sm font-bold text-white">{{ formatCurrency(totalItem) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Rodapé -->
    <template #footer>
      <div class="flex items-center justify-between gap-3 w-full">
        <!--
          Sempre visível: às vezes já se sabe de saída que o item não está no
          catálogo, e obrigar a buscar antes só para descobrir isso é atrito.
        -->
        <button
          type="button"
          class="flex items-center gap-1.5 text-xs font-semibold text-brand-primary hover:underline cursor-pointer"
          @click="handleAddAvulso"
        >
          <PackagePlus :size="14" />
          Produto avulso
        </button>

        <div class="flex justify-end gap-3"><BaseButton variant="secondary" class="px-5" @keydown="ciclarParaBusca" @click="emit('close')">Fechar</BaseButton>
        <BaseButton
          v-if="selectedProductId"
          variant="primary"
          data-adicionar-carrinho
          :is-loading="isAddingItem"
          @keydown="ciclarParaBusca"
          :disabled="!canAddItem"
          class="gap-2"
          @click="handleAdd"
        >
          <ShoppingCart :size="16" />
          Adicionar ao Carrinho
        </BaseButton>
        </div>
      </div>
    </template>
  </BaseModal>

  <AvisoEstoqueNegativoModal
    :is-open="avisoEstoqueAberto"
    :nome-produto="avisoEstoqueDados?.nome ?? ''"
    :estoque-atual="avisoEstoqueDados?.estoqueAtual ?? 0"
    :quantidade-desejada="avisoEstoqueDados?.quantidadeDesejada ?? 1"
    @confirmar="confirmarAvisoEstoque"
    @cancelar="cancelarAvisoEstoque"
  />
</template>
