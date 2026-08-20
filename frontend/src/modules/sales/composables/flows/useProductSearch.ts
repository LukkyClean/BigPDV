import { computed, nextTick, onScopeDispose, ref, watch, type Ref } from 'vue';
import { onClickOutside } from '@vueuse/core';
import { storeToRefs } from 'pinia';

import { useProductQuery } from '../queries/useProductQuery';
import { useAddItemSaleMutation, useUpdateItemSaleMutation } from '../mutates/useItemSaleMutation';
import { useAddItemOrcamentoMutation } from '../mutates/useItemOrcamentoMutation';
import { useConfiguracoesStore } from '@/shared/stores/configuracoes.store';
import { useToast } from '@/shared/composables/useToast';
import { productService } from '../../api.service';
import { resolverPorCodigoExato } from '../../leitorCodigoBarras.util';

import type { ProductSaleCreate, ProductSaleRead, ProductSaleListItem } from '../../schemas/productSale.schema';

/** Quanto tempo a busca espera o dedo parar, para quem digita nome. */
const ESPERA_BUSCA_MS = 300;

/**
 * O desfecho de uma tentativa de pôr produto no carrinho.
 *
 * Existe para que `false` pare de carregar cinco significados diferentes. Antes,
 * "não encontrei", "achei dois", "a rede caiu" e "o operador desistiu" voltavam
 * todos como a mesma coisa — e quem chamou não tinha como dizer nada ao
 * operador, porque não sabia o que tinha acontecido.
 *
 * `out_of_stock` não está na lista de propósito: estoque insuficiente não é um
 * desfecho, é uma bifurcação que espera decisão humana e termina em `added` ou
 * `cancelled`.
 */
export type ResultadoAdicao =
  | { tipo: 'added' }
  | { tipo: 'not_found'; termo: string; candidatos: number }
  | { tipo: 'ambiguous'; termo: string; quantos: number }
  | { tipo: 'blocked'; nome: string }
  | { tipo: 'cancelled' }
  | { tipo: 'error' };

export function useProductSearch(
  isOrcamento = false,
  currentItems?: Ref<ProductSaleRead[] | undefined>,
  externalContainerRef?: Ref<HTMLElement | null>,
) {
  const inputOnFocus = ref(false);

  function handleInputChange(isSearching: boolean) {
    inputOnFocus.value = isSearching;
  }

  const searchTerm = ref('');

  /**
   * O termo que a busca realmente consulta, atrasado em 300 ms.
   *
   * É um debounce escrito à mão, e não o `refDebounced` do VueUse, por causa do
   * leitor de código de barras: quando o atalho do leitor não morde, a gente
   * precisa PUBLICAR o termo na hora (`aplicarBuscaAgora`) em vez de esperar o
   * relógio. Sem isso o operador aperta Enter e a lista só nasce 300 ms depois,
   * quando o Enter já foi embora — que é o bug que fazia a bipada terminar em
   * silêncio.
   */
  const debouncedSearchTerm = ref('');
  let temporizadorBusca: ReturnType<typeof setTimeout> | null = null;

  watch(searchTerm, (termo) => {
    if (temporizadorBusca) clearTimeout(temporizadorBusca);
    temporizadorBusca = setTimeout(() => {
      debouncedSearchTerm.value = termo;
      temporizadorBusca = null;
    }, ESPERA_BUSCA_MS);
  });

  /** Publica o termo digitado imediatamente, sem esperar o debounce. */
  function aplicarBuscaAgora() {
    if (temporizadorBusca) {
      clearTimeout(temporizadorBusca);
      temporizadorBusca = null;
    }
    debouncedSearchTerm.value = searchTerm.value;
  }

  onScopeDispose(() => {
    if (temporizadorBusca) clearTimeout(temporizadorBusca);
  });

  const selectedProductId = ref<number | null>(null);
  const selectedProductName = ref<string | null>(null);

  const quantity = ref(1);
  const desconto = ref(0);
  const selectedProduct = ref<ProductSaleListItem[number] | null>(null);

  /**
   * O item destacado na lista. Nasce em 0 — o primeiro resultado.
   *
   * Nascer em -1 fazia o Enter não ter alvo: quem digitava o nome e apertava
   * Enter não conseguia nada, e era obrigado a passar pela seta ou pelo mouse.
   * E o topo da lista não é um lugar arbitrário: o backend já manda para lá o
   * produto cujo código bate exatamente (`_CAMPOS_EXATOS` em `crud/produto.py`),
   * então destacar o primeiro é herdar um ranking que já está calculado.
   */
  const highlightedIndex = ref(0);

  const productQuery = useProductQuery(debouncedSearchTerm);
  const addItemSaleMutation = useAddItemSaleMutation();
  const addItemOrcamentoMutation = useAddItemOrcamentoMutation();
  const updateItemSaleMutation = useUpdateItemSaleMutation();

  const { permitirVendaEstoqueZerado } = storeToRefs(useConfiguracoesStore());
  const toast = useToast();

  const searchContainerRef: Ref<HTMLElement | null> = externalContainerRef ?? ref<HTMLElement | null>(null);

  const isSearching = computed(() => {
    return (
      searchTerm.value.trim().length > 1 &&
      debouncedSearchTerm.value.trim().length > 1 &&
      selectedProductId.value === null
    );
  });

  const canAddItem = computed(() => {
    return !!selectedProductId.value && quantity.value > 0;
  });

  const totalItem = computed(() => {
    if (!selectedProduct.value) return 0;
    const subtotal = selectedProduct.value.preco * quantity.value;
    return Math.max(0, subtotal - desconto.value);
  });

  // Ordenar: produtos sem estoque vão para o final
  const sortedProducts = computed(() => {
    if (!productQuery.data.value) return [];
    return [...productQuery.data.value].sort((a, b) => {
      const aOut = a.estoque <= 0 ? 1 : 0;
      const bOut = b.estoque <= 0 ? 1 : 0;
      return aOut - bOut;
    });
  });

  function selectProduct(productName: string, productId: number) {
    inputOnFocus.value = false;
    searchTerm.value = productName;
    selectedProductName.value = productName;
    selectedProductId.value = productId;
    quantity.value = 1;
    desconto.value = 0;
    highlightedIndex.value = 0;
    selectedProduct.value = sortedProducts.value.find((p) => p.id === productId) ?? null;
  }

  function increaseQuantity() {
    quantity.value += 1;
  }

  function decreaseQuantity() {
    if (quantity.value > 1) {
      quantity.value -= 1;
    }
  }

  function resetSelection() {
    searchTerm.value = '';
    aplicarBuscaAgora();
    selectedProductName.value = null;
    selectedProductId.value = null;
    selectedProduct.value = null;
    quantity.value = 1;
    desconto.value = 0;
    inputOnFocus.value = false;
    highlightedIndex.value = 0;
  }

  function focusSearchInput() {
    nextTick(() => {
      const input = searchContainerRef.value?.querySelector('input');
      input?.focus();
    });
  }

  // ==========================================================================
  // O aviso de estoque, e por que ele é uma PROMESSA
  // ==========================================================================
  //
  // O modal de "vender mesmo assim" interrompe a decisão no meio: quem chamou
  // precisa saber se a venda entrou ou não, e isso só se sabe depois que o
  // operador responde. Enquanto o aviso era disparado e esquecido, o chamador
  // seguia em frente achando que tinha terminado — e era por isso que o leitor
  // e a lista acabavam contando histórias diferentes sobre o mesmo produto.
  //
  // Aqui ele vira uma pergunta que se espera: a função guarda o `resolve` e só
  // continua quando o operador clica.

  const avisoEstoqueAberto = ref(false);
  const avisoEstoqueDados = ref<{
    nome: string;
    estoqueAtual: number;
    quantidadeDesejada: number;
  } | null>(null);

  let responderAviso: ((continuar: boolean) => void) | null = null;

  function perguntarSobreEstoque(dados: {
    nome: string;
    estoqueAtual: number;
    quantidadeDesejada: number;
  }): Promise<boolean> {
    avisoEstoqueDados.value = dados;
    avisoEstoqueAberto.value = true;
    return new Promise<boolean>((resolve) => {
      responderAviso = resolve;
    });
  }

  function confirmarAvisoEstoque() {
    avisoEstoqueAberto.value = false;
    responderAviso?.(true);
    responderAviso = null;
  }

  function cancelarAvisoEstoque() {
    avisoEstoqueAberto.value = false;
    responderAviso?.(false);
    responderAviso = null;
  }

  // Fechar a tela com o aviso aberto não pode deixar a promessa pendurada.
  onScopeDispose(() => responderAviso?.(false));

  // ==========================================================================
  // A execução da adição
  // ==========================================================================

  /**
   * Põe o produto no carrinho de verdade. Sem regra de estoque, sem pergunta:
   * quem chega aqui já decidiu.
   *
   * Se o produto já está na venda, soma na linha existente em vez de criar uma
   * segunda — é o que faz bipar a mesma garrafa três vezes virar "3 un.".
   */
  async function executarAdicao(
    saleId: number,
    produtoId: number,
    quantidade: number,
    descontoItem: number,
  ): Promise<boolean> {
    const existingItem = currentItems?.value?.find((item) => item.produto_id === produtoId);

    try {
      if (existingItem && !isOrcamento) {
        await updateItemSaleMutation.mutateAsync({
          saleId,
          productId: existingItem.id,
          payload: {
            quantidade: existingItem.quantidade + quantidade,
            ...(descontoItem > 0 && { desconto: descontoItem }),
          },
        });
      } else {
        const payload: ProductSaleCreate = {
          tipo_produto: 'CADASTRADO',
          quantidade,
          produto_id: produtoId,
          ...(descontoItem > 0 && { desconto: descontoItem }),
        };

        if (isOrcamento) {
          await addItemOrcamentoMutation.mutateAsync({ orcamentoId: saleId, payload });
        } else {
          await addItemSaleMutation.mutateAsync({ saleId, payload });
        }
      }

      resetSelection();
      focusSearchInput();
      return true;
    } catch {
      // As mutations já mostram o erro em toast. Aqui só interessa não seguir
      // adiante como se a venda tivesse entrado.
      return false;
    }
  }

  /**
   * A porta única para pôr produto no carrinho.
   *
   * O leitor, o clique e o teclado chegam todos aqui. Antes cada um tinha a sua
   * própria regra de estoque, o seu próprio jeito de desistir e o seu próprio
   * silêncio — e foi assim que o mesmo produto passou a ter três comportamentos
   * dependendo de como você o escolheu.
   *
   * Entra ou um `produto` já resolvido (clique, teclado) ou um `termo` para
   * resolver (leitor). Sai sempre um `ResultadoAdicao`.
   */
  async function tentarAdicionarProduto(entrada: {
    saleId: number | null;
    produto?: ProductSaleListItem[number];
    termo?: string;
    quantidade?: number;
    desconto?: number;
  }): Promise<ResultadoAdicao> {
    const { saleId } = entrada;
    if (!saleId) return { tipo: 'error' };

    let produto = entrada.produto;

    // ── Resolver o código, quando veio termo em vez de produto ──────────────
    if (!produto && entrada.termo) {
      const termo = entrada.termo.trim();
      let encontrados: ProductSaleListItem;
      try {
        encontrados = await productService.searchProducts(termo);
      } catch {
        // Antes isto era `catch { return false }`: a rede caía e o operador via
        // exatamente nada. Erro técnico virava "não aconteceu nada", que é o
        // pior tipo de silêncio porque é intermitente.
        toast.error('Não deu para consultar o produto', 'Verifique a conexão e tente de novo.');
        return { tipo: 'error' };
      }

      const resolvido = resolverPorCodigoExato(termo, encontrados);
      if (resolvido.tipo === 'nenhum') {
        // `candidatos` separa duas situações que pareciam a mesma: o catálogo
        // não tem nada (aí a mensagem é a resposta) e o catálogo tem parecidos
        // mas nenhum com aquele código exato (aí a LISTA é a resposta, e uma
        // mensagem de "não encontrado" por cima dela seria mentira).
        return { tipo: 'not_found', termo, candidatos: encontrados.length };
      }
      if (resolvido.tipo === 'ambiguo') {
        return { tipo: 'ambiguous', termo, quantos: resolvido.quantos };
      }
      produto = resolvido.produto;
    }

    if (!produto) return { tipo: 'error' };

    // ── Estoque: a regra é a da empresa, lida da configuração ───────────────
    //
    // O limiar é o mesmo do backend (`services/venda.py`): compara a quantidade
    // TOTAL que o item vai ficar tendo contra o estoque, não a quantidade que
    // está sendo somada agora. Divergir disso fazia a tela prometer o que o
    // servidor ia recusar.
    const quantidade = entrada.quantidade ?? 1;
    const descontoItem = entrada.desconto ?? 0;
    const jaNaVenda = currentItems?.value?.find((item) => item.produto_id === produto!.id);
    const quantidadeTotal = (jaNaVenda?.quantidade ?? 0) + quantidade;

    if (quantidadeTotal > produto.estoque) {
      // ORÇAMENTO É DIFERENTE, e é o backend que decide isso.
      //
      // `services/venda.py` consulta `permitir_venda_estoque_zerado`;
      // `services/orcamento.py` (:106 e :151) NÃO consulta — recusa sempre. Se a
      // tela aplicasse a mesma regra nos dois, o orçamento voltaria a abrir
      // "vender mesmo assim" para uma coisa que o servidor recusa depois. Cada
      // fluxo espelha o seu backend, não o outro.
      if (isOrcamento) {
        toast.warning(
          `Estoque insuficiente para ${produto.nome}`,
          `Restam ${produto.estoque} un., e orçamento não aceita quantidade acima do estoque.`,
        );
        return { tipo: 'blocked', nome: produto.nome };
      }

      if (!permitirVendaEstoqueZerado.value) {
        // A loja desligou a venda com estoque zerado. Recusar calado seria o
        // silêncio de sempre; deixar passar seria prometer o que `venda.py`
        // vai negar.
        toast.warning(
          `Estoque insuficiente para ${produto.nome}`,
          `Restam ${produto.estoque} un. e esta loja não permite vender com estoque zerado.`,
        );
        return { tipo: 'blocked', nome: produto.nome };
      }

      const continuar = await perguntarSobreEstoque({
        nome: produto.nome,
        estoqueAtual: produto.estoque,
        quantidadeDesejada: quantidadeTotal,
      });
      if (!continuar) return { tipo: 'cancelled' };
    }

    const ok = await executarAdicao(saleId, produto.id, quantidade, descontoItem);
    return ok ? { tipo: 'added' } : { tipo: 'error' };
  }

  /**
   * Avisa o operador sobre um desfecho que não pôs nada no carrinho.
   *
   * Fica junto do resultado de propósito: quem escrever a sétima porta de
   * entrada amanhã encontra a mensagem pronta e não vai reinventar o silêncio.
   * `added`, `cancelled` e `blocked` não passam por aqui — o primeiro já é
   * anunciado pela mutation, e os outros dois foram decisão de alguém.
   */
  function avisarResultado(resultado: ResultadoAdicao) {
    if (resultado.tipo === 'not_found') {
      // Com candidatos na tela, a lista já é a resposta — avisar "não
      // encontrado" por cima de três produtos visíveis seria contradizer o que
      // o operador está vendo.
      if (resultado.candidatos > 0) return;
      toast.warning(
        'Produto não encontrado',
        `Nada no catálogo com o código ${resultado.termo}.`,
      );
      return;
    }
    if (resultado.tipo === 'ambiguous') {
      toast.warning(
        `${resultado.quantos} produtos com esse código`,
        'Escolha na lista qual deles é.',
      );
    }
  }

  // ==========================================================================
  // Navegação por teclado
  // ==========================================================================

  /**
   * Move o destaque e devolve o item escolhido no Enter.
   *
   * Só cuida da NAVEGAÇÃO: quem decide o que fazer com o produto escolhido é a
   * tela, chamando `tentarAdicionarProduto`. Antes o Enter também aplicava
   * regra de estoque aqui dentro, e era uma quarta regra concorrendo com as
   * outras três.
   */
  function handleKeydown(e: KeyboardEvent): ProductSaleListItem[number] | null {
    if (!isSearching.value) return null;

    const products = sortedProducts.value;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        if (highlightedIndex.value < products.length - 1) {
          highlightedIndex.value++;
          scrollToHighlighted();
        }
        return null;

      case 'ArrowUp':
        e.preventDefault();
        if (highlightedIndex.value > 0) {
          highlightedIndex.value--;
          scrollToHighlighted();
        }
        return null;

      case 'Enter': {
        e.preventDefault();
        const escolhido = products[highlightedIndex.value];
        return escolhido ?? null;
      }

      case 'Escape':
        e.preventDefault();
        resetSelection();
        return null;
    }

    return null;
  }

  function scrollToHighlighted() {
    nextTick(() => {
      const el = document.querySelector(`[data-product-index="${highlightedIndex.value}"]`);
      el?.scrollIntoView({ block: 'nearest' });
    });
  }

  onClickOutside(searchContainerRef, () => {
    if (isSearching.value) {
      resetSelection();
    }
  });

  /**
   * Lista nova, destaque de volta ao primeiro.
   *
   * Voltava para -1, e aí bastava a lista se refazer — inclusive pelo polling de
   * 10 s, quando o outro caixa vendia uma unidade — para o destaque sumir da mão
   * do operador no meio da digitação.
   */
  watch(sortedProducts, () => {
    highlightedIndex.value = 0;
  });

  watch(searchTerm, (term) => {
    if (!selectedProductId.value) return;

    if (term !== selectedProductName.value) {
      selectedProductId.value = null;
      selectedProductName.value = null;
      selectedProduct.value = null;
      quantity.value = 1;
      desconto.value = 0;
    }
  });

  return {
    searchTerm,
    aplicarBuscaAgora,

    products: sortedProducts,
    isLoading: productQuery.isLoading,

    selectedProductId,
    selectedProductName,
    selectedProduct,
    quantity,
    desconto,
    totalItem,
    searchContainerRef,
    highlightedIndex,

    isSearching,
    canAddItem,
    isAddingItem: computed(() =>
      isOrcamento
        ? addItemOrcamentoMutation.isPending.value
        : addItemSaleMutation.isPending.value || updateItemSaleMutation.isPending.value,
    ),

    avisoEstoqueAberto,
    avisoEstoqueDados,
    confirmarAvisoEstoque,
    cancelarAvisoEstoque,

    handleInputChange,
    handleKeydown,
    selectProduct,
    increaseQuantity,
    decreaseQuantity,
    resetSelection,
    tentarAdicionarProduto,
    avisarResultado,
  };
}
