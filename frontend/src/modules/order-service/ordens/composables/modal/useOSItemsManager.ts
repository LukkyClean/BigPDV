import { computed, ref, type ComputedRef } from 'vue';

import type { OSFormContext } from '../../types/context.type';
import type { OrderServiceReadDataType } from '../../schemas/orderServiceQuery.schema';
import type { OsItemCreateSchemaDataType } from '../../schemas/relationship/osItem.schema';

interface AddItemMutation {
  mutate: (
    variables: { osNumber: string; osItem: OsItemCreateSchemaDataType },
    options?: { onSuccess?: (data: OrderServiceReadDataType) => void },
  ) => void;
}

interface DeleteItemMutation {
  mutate: (
    variables: { osNumber: string; itemOsId: number },
    options?: { onSuccess?: () => void },
  ) => void;
}

interface UseOSItemsManagerParams {
  isCreateMode: ComputedRef<boolean>;
  osNumber: ComputedRef<string | null>;
  createItems: ComputedRef<OsItemCreateSchemaDataType[]>;
  currentOSData: ComputedRef<OrderServiceReadDataType | null>;
  form: OSFormContext;
  addItemMutation: AddItemMutation;
  deleteItemMutation: DeleteItemMutation;
  refreshCurrentOSData: () => Promise<void> | void;
  setCurrentOSData: (os: OrderServiceReadDataType) => void;
}

export function useOSItemsManager({
  isCreateMode,
  osNumber,
  createItems,
  currentOSData,
  form,
  addItemMutation,
  deleteItemMutation,
  refreshCurrentOSData,
  setCurrentOSData,
}: UseOSItemsManagerParams) {
  const isItemModalOpen = ref(false);
  const editingItemIndex = ref<number | null>(null);
  const editingItem = ref<OsItemCreateSchemaDataType | null>(null);
  const editingItemId = ref<number | null>(null);

  const displayItems = computed(() =>
    isCreateMode.value ? createItems.value : (currentOSData.value?.itens ?? []),
  );

  function openAddItemModal() {
    editingItemIndex.value = null;
    editingItem.value = null;
    editingItemId.value = null;
    isItemModalOpen.value = true;
  }

  function openEditItemModal(index: number) {
    const item = displayItems.value[index];
    if (!item) return;

    editingItemIndex.value = index;
    editingItemId.value = 'id' in item ? (item as { id: number }).id : null;
    editingItem.value = {
      tipo: item.tipo,
      nome: item.nome,
      unidade_medida: item.unidade_medida,
      quantidade: item.quantidade,
      valor_unitario: item.valor_unitario,
      // Aprovação/garantia PRECISAM vir junto: o modal cai no default
      // ('APROVADO' e sem garantia) quando não recebe o valor real, e ao salvar
      // esse default sobrescreveria um item reprovado ou com garantia definida.
      status_aprovacao: item.status_aprovacao,
      garantia_dias: item.garantia_dias,
      garantia_km: item.garantia_km,
    };
    isItemModalOpen.value = true;
  }

  function closeItemModal() {
    isItemModalOpen.value = false;
    editingItem.value = null;
    editingItemIndex.value = null;
    editingItemId.value = null;
  }

  function handleSaveItem(item: OsItemCreateSchemaDataType) {
    if (isCreateMode.value) {
      if (editingItemIndex.value !== null) {
        form.criar.handleUpdateItem(editingItemIndex.value, item);
      } else {
        form.criar.handleAddItem(item);
      }
      closeItemModal();
      return;
    }

    const currentOsNumber = osNumber.value;
    if (!currentOsNumber) return;

    if (editingItemId.value !== null) {
      form.item.setEditingItem(editingItemId.value, item);
      form.item.onSubmit();
      refreshCurrentOSData();
      return;
    }

    addItemMutation.mutate(
      { osNumber: currentOsNumber, osItem: item },
      {
        onSuccess: (data) => {
          setCurrentOSData(data);
          closeItemModal();
        },
      },
    );
  }

  function handleRemoveItem(index: number) {
    if (isCreateMode.value) {
      form.criar.handleRemoveItem(index);
      return;
    }

    const currentOsNumber = osNumber.value;
    const item = displayItems.value[index] as { id?: number };
    if (!currentOsNumber || !item?.id) return;

    deleteItemMutation.mutate(
      { osNumber: currentOsNumber, itemOsId: item.id },
      { onSuccess: () => { refreshCurrentOSData(); } },
    );
  }

  return {
    isItemModalOpen,
    editingItem,
    displayItems,
    openAddItemModal,
    openEditItemModal,
    closeItemModal,
    handleSaveItem,
    handleRemoveItem,
  };
}
