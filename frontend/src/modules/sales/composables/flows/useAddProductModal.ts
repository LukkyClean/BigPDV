import { reactive, ref } from 'vue';

const isAddProductModalOpen = ref(false);

/**
 * O termo que a modal deve abrir já buscando.
 *
 * Existe para a ponte entre as duas telas de produto: quem estava na busca
 * rápida, achou o produto e precisa de quantidade ou desconto, chega na modal
 * com a busca já feita. Sem isto a ponte obrigava a digitar o nome de novo, e
 * ninguém usa uma ponte assim.
 */
const termoInicial = ref('');

export function useAddProductModal() {
  return reactive({
    isAddProductModalOpen,
    termoInicial,
    openAddProductModal(termo = '') {
      termoInicial.value = termo;
      isAddProductModalOpen.value = true;
    },
    closeAddProductModal() {
      isAddProductModalOpen.value = false;
      termoInicial.value = '';
    },
  });
}
