import { computed, ref } from 'vue';
import { useForm } from 'vee-validate';
import { toTypedSchema } from '@vee-validate/zod';
import type { Ref } from 'vue';

import { OsItemCreateSchema } from '../../schemas/relationship/osItem.schema';
import type { OsItemUpdateSchemaDataType } from '../../schemas/relationship/osItem.schema';

import type { OSItemFormContext } from '../../types/context.type';

import {
  useCreateItemOSMutation,
} from '../request/useOrderServiceCreate.mutate';
import {
  useUpdateItemOSMutation,
} from '../request/useOrderServiceUpdate.mutate';

import { DEFAULT_OS_ITEM_VALUES } from '../../constants/core.constant';


export function useOSItemForm(opts: {
  osNumber: Ref<string | null>;
  onSuccess?: () => void;
}): OSItemFormContext {
  const createMutation = useCreateItemOSMutation();
  const updateMutation = useUpdateItemOSMutation();

  const editingItemId = ref<number | null>(null);
  const isEditMode = computed(() => editingItemId.value !== null);

  const { handleSubmit, errors, defineField, setValues, resetForm: veeReset } = useForm({
    validationSchema: toTypedSchema(OsItemCreateSchema),
    initialValues: { ...DEFAULT_OS_ITEM_VALUES },
  });

  const [tipo] = defineField('tipo');
  const [nome] = defineField('nome');
  const [unidade_medida] = defineField('unidade_medida');
  const [quantidade] = defineField('quantidade');
  const [valor_unitario] = defineField('valor_unitario');

  const setEditingItem = (itemId: number, itemData: OsItemUpdateSchemaDataType) => {
    editingItemId.value = itemId;
    setValues({
      nome: itemData.nome ?? '',
      unidade_medida: itemData.unidade_medida ?? 'UN',
      quantidade: itemData.quantidade ?? 1,
      valor_unitario: itemData.valor_unitario ?? 0,
      status_aprovacao: itemData.status_aprovacao,
      garantia_dias: itemData.garantia_dias,
      garantia_km: itemData.garantia_km,
    });
  };

  const resetForm = () => {
    editingItemId.value = null;
    veeReset({ values: { ...DEFAULT_OS_ITEM_VALUES } });
  };

  const onSubmit = handleSubmit((formData) => {
    if (!opts.osNumber.value) return;

    if (isEditMode.value && editingItemId.value !== null) {
      // Modo edição: envia apenas os campos aceitos pelo endpoint de update
      // (OSItemUpdate no backend). Aprovação e garantia entram aqui porque são
      // exatamente o que muda DEPOIS que a OS foi aberta — o cliente aprova o
      // orçamento por telefone e o item precisa sair de PENDENTE. Sem eles, a
      // mudança não saía do navegador e o item reabria no estado antigo.
      const updateData: OsItemUpdateSchemaDataType = {
        nome: formData.nome,
        unidade_medida: formData.unidade_medida,
        quantidade: formData.quantidade,
        valor_unitario: formData.valor_unitario,
        status_aprovacao: formData.status_aprovacao,
        garantia_dias: formData.garantia_dias,
        garantia_km: formData.garantia_km,
      };
      updateMutation.mutate(
        {
          osNumber: opts.osNumber.value,
          osItemId: editingItemId.value,
          updatedItem: updateData,
        },
        {
          onSuccess: () => {
            resetForm();
            opts.onSuccess?.();
          },
        },
      );
    } else {
      // Modo criação: envia o payload completo
      createMutation.mutate(
        { osNumber: opts.osNumber.value, osItem: formData },
        {
          onSuccess: () => {
            resetForm();
            opts.onSuccess?.();
          },
        },
      );
    }
  });

  const isPending = computed(
    () => createMutation.isPending.value || updateMutation.isPending.value,
  );

  return {
    tipo,
    nome,
    unidade_medida,
    quantidade,
    valor_unitario,
    editingItemId,
    isEditMode,
    errors,
    isPending,
    onSubmit,
    setEditingItem,
    resetForm,
  };
}
