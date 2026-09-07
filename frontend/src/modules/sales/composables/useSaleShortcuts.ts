import { type Ref } from 'vue';
import { useMagicKeys, whenever, useEventListener } from '@vueuse/core';

interface SaleShortcutsContext {
  saleModalIsOpen: Ref<boolean>;
  isEditMode: Ref<boolean>;
  finishModalIsOpen: Ref<boolean>;
  paymentDetailsIsOpen: Ref<boolean>;
  itemModalIsOpen: Ref<boolean>;
  addProductModalIsOpen: Ref<boolean>;
  onCreateSale: () => void;
  onOpenFinishModal: () => void;
  onOpenItemModal: () => void;
  onOpenAddProductModal: () => void;
  onFocusPaymentGrid: () => void;
  /** Leva o cursor ao campo de CPF/CNPJ do cupom (F7). */
  onFocusDocumentoFiscal: () => void;
  onCancelSale: () => void;
  onCloseSaleModal: () => void;
  onCloseFinishModal: () => void;
  onClosePaymentDetails: () => void;
  onCloseItemModal: () => void;
  onCloseAddProductModal: () => void;
  onFocusSearch: () => void;
  onFocusSaleInputs: (field: 'entrega' | 'desconto') => void;
}

export function useSaleShortcuts(context: SaleShortcutsContext) {
  const keys = useMagicKeys();


  // Prevenir Ctrl+F padrão do browser quando o modal está aberto
  useEventListener(document, 'keydown', (e: KeyboardEvent) => {
    if (e.ctrlKey && e.key === 'f' && context.saleModalIsOpen.value && context.isEditMode.value) {
      e.preventDefault();
    }
  });

  // F3 é "localizar próximo" no Chromium, e o app roda dentro de um WebView2.
  //
  // Sem esta linha, apertar F3 abre a barra de busca DO NAVEGADOR por cima da
  // venda — e ela leva o foco junto, então o cursor não chega na busca de
  // produto e o que o operador digita vai parar na barra errada. O atalho abria
  // a tela certa e o teclado ia para o lugar errado.
  useEventListener(document, 'keydown', (e: KeyboardEvent) => {
    if (e.key === 'F3' && context.saleModalIsOpen.value && context.isEditMode.value) {
      e.preventDefault();
    }
  });

  // F2 — Criar nova venda (apenas quando o modal de venda NÃO está aberto)
  whenever(keys.F2, () => {
    if (!context.saleModalIsOpen.value) {
      context.onCreateSale();
    }
  });

  // F3 — Abrir a tela de quantidade e desconto.
  //
  // A busca rápida da venda sempre soma 1, que é o ritmo do balcão. Quando o
  // caso é "3 unidades com desconto", a tela é outra — e sem atalho ela só se
  // alcançava com o mouse, no meio de um fluxo que o resto do módulo já fazia
  // pelo teclado.
  whenever(keys.F3, () => {
    if (
      context.saleModalIsOpen.value &&
      context.isEditMode.value &&
      !context.finishModalIsOpen.value &&
      !context.itemModalIsOpen.value &&
      !context.addProductModalIsOpen.value
    ) {
      context.onOpenAddProductModal();
    }
  });

  // F4 — Abrir modal de produto avulso (dentro do SaleModal em modo edição)
  whenever(keys.F4, () => {
    if (
      context.saleModalIsOpen.value &&
      context.isEditMode.value &&
      !context.finishModalIsOpen.value &&
      !context.addProductModalIsOpen.value
    ) {
      context.onOpenItemModal();
    }
  });

  // F6 — Focar no grid de pagamentos (dentro do FinishSaleModal)
  whenever(keys.F6, () => {
    if (context.finishModalIsOpen.value) {
      context.onFocusPaymentGrid();
    }
  });

  // F7 — Focar o CPF/CNPJ do cupom (dentro do FinishSaleModal)
  //
  // Vizinho do F6 de propósito: "Deseja CPF na nota?" vem logo depois de
  // informar os pagamentos, e é a pergunta que o operador faz de cabeça com o
  // cliente na frente — procurar o campo com o mouse ali custa a fila.
  whenever(keys.F7, () => {
    if (context.finishModalIsOpen.value) {
      context.onFocusDocumentoFiscal();
    }
  });

  // Ctrl+F — Focar busca de produtos
  whenever(keys.Ctrl_F, () => {
    if (context.saleModalIsOpen.value && context.isEditMode.value && !context.finishModalIsOpen.value && !context.itemModalIsOpen.value && !context.addProductModalIsOpen.value) {
      context.onFocusSearch();
    }
  });

  // Ctrl+E — Focar input de entrega / Ctrl+D — Focar input de desconto
  useEventListener(document, 'keydown', (e: KeyboardEvent) => {
    if (e.ctrlKey && (e.key === 'e' || e.key === 'd') && context.saleModalIsOpen.value && context.isEditMode.value) {
      e.preventDefault();
    }
  });
  whenever(keys.Ctrl_E, () => {
    if (context.saleModalIsOpen.value && context.isEditMode.value && !context.finishModalIsOpen.value && !context.itemModalIsOpen.value && !context.addProductModalIsOpen.value) {
      context.onFocusSaleInputs('entrega');
    }
  });
  whenever(keys.Ctrl_D, () => {
    if (context.saleModalIsOpen.value && context.isEditMode.value && !context.finishModalIsOpen.value && !context.itemModalIsOpen.value && !context.addProductModalIsOpen.value) {
      context.onFocusSaleInputs('desconto');
    }
  });

  // Ctrl+Enter — Abrir modal de finalização
  whenever(keys.Ctrl_Enter, () => {
    if (context.saleModalIsOpen.value && context.isEditMode.value && !context.finishModalIsOpen.value && !context.itemModalIsOpen.value && !context.addProductModalIsOpen.value) {
      context.onOpenFinishModal();
    }
  });

  // Ctrl+Backspace — Cancelar venda
  whenever(keys.Ctrl_Backspace, () => {
    if (context.saleModalIsOpen.value && context.isEditMode.value && !context.finishModalIsOpen.value && !context.itemModalIsOpen.value && !context.addProductModalIsOpen.value) {
      context.onCancelSale();
    }
  });

  // Escape — Fechar modal atual (respeita hierarquia)
  whenever(keys.Escape, () => {
    // O sub-modal de pagamento e o degrau MAIS ALTO: ele abre por cima da
    // Finalizar Venda. Faltando aqui, o Esc caia no degrau de baixo e fechava a
    // venda inteira -- levando os pagamentos ja lancados junto, porque
    // `closeFinishModal` chama `resetPayments()`.
    if (context.paymentDetailsIsOpen.value) {
      context.onClosePaymentDetails();
      return;
    }
    if (context.finishModalIsOpen.value) {
      context.onCloseFinishModal();
      return;
    }
    if (context.itemModalIsOpen.value) {
      context.onCloseItemModal();
      return;
    }
    if (context.addProductModalIsOpen.value) {
      context.onCloseAddProductModal();
      return;
    }
    if (context.saleModalIsOpen.value) {
      context.onCloseSaleModal();
    }
  });
}
