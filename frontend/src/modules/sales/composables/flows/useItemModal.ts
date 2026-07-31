import { ref, computed } from 'vue';

import { ProductSaleRead } from '../../schemas/productSale.schema';

type ModalMode = 'create' | 'edit';

const itemModalIsOpen = ref(false);
const itemModalMode = ref<ModalMode>('edit');
const selectedItem = ref<ProductSaleRead | null>(null);
// Descrição com que o modal de avulso abre. Vem do termo que o usuário já tinha
// digitado na busca: ele procurou "cabo hdmi", não achou, e não deve ter que
// digitar de novo.
const descricaoInicial = ref('');

export function useItemModal() {
  const isCreateMode = computed(() => itemModalMode.value === 'create');

  const isEditMode = computed(() => itemModalMode.value === 'edit');

  function closeItemModal() {
    itemModalIsOpen.value = false;
    itemModalMode.value = 'edit';
    descricaoInicial.value = '';
  }

  function openCreateItemModal(descricao = '') {
    itemModalIsOpen.value = true;
    itemModalMode.value = 'create';
    selectedItem.value = null;
    descricaoInicial.value = descricao.trim();
  }

  function openEditItemModal(item: ProductSaleRead) {
    selectedItem.value = item;
    itemModalIsOpen.value = true;
    itemModalMode.value = 'edit';
    console.log('openEditItemModal', item);
  }

  return {
    itemModalIsOpen,
    isCreateMode,
    isEditMode,
    selectedItem,
    descricaoInicial,
    closeItemModal,
    openCreateItemModal,
    openEditItemModal,
  };
}
