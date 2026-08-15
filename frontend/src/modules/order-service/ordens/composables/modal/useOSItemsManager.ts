import { computed, ref, type ComputedRef } from 'vue';

import type { OSFormContext } from '../../types/context.type';
import type { OrderServiceReadDataType } from '../../schemas/orderServiceQuery.schema';
import type { OsItemCreateSchemaDataType, OsItemReadSchemaDataType } from '../../schemas/relationship/osItem.schema';

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

/**
 * O vínculo com o catálogo tem dois nomes conforme a origem do item: `item_id`
 * enquanto a OS está sendo criada (payload de escrita) e `produto_id`/`servico_id`
 * depois de salva (resposta de leitura). É o mesmo dado — o backend converte um
 * no outro. Sem esta ponte, editar um item de OS salva perderia o vínculo na tela.
 */
function vinculoCatalogo(item: OsItemCreateSchemaDataType | OsItemReadSchemaDataType): number | undefined {
  const i = item as Partial<OsItemCreateSchemaDataType & OsItemReadSchemaDataType>;
  return i.item_id ?? i.produto_id ?? i.servico_id ?? undefined;
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
      // Custo interno: sem ele o campo reabre zerado e, numa OS ainda em
      // criação, salvar grava custo 0 — o lucro do relatório sai inflado.
      custo_unitario: item.custo_unitario,
      // Vínculo com o catálogo: sem ele, editar a peça antes de salvar a OS a
      // transforma num item de texto solto — não baixa do estoque e não puxa o
      // custo congelado do livro (o backend deriva produto_id/servico_id daqui).
      item_id: vinculoCatalogo(item),
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
      // `onSubmit` é assíncrono e só DISPARA a mutation. Recarregar aqui trazia
      // a OS antiga de volta e a resposta do PATCH nunca chegava à tela: o item
      // gravava reprovado no banco e a tela seguia mostrando "Aprovado" com o
      // subtotal cheio, até alguém fechar e reabrir a OS.
      // Quem recarrega agora é o `onSuccess` da mutation (onItemSuccess), como
      // já acontecia ao remover um item.
      form.item.onSubmit();
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
