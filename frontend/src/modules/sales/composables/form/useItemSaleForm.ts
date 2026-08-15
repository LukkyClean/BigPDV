import { type Ref, type MaybeRef, watch, computed, unref, ref, type ComputedRef } from 'vue';
import { useForm } from 'vee-validate';
import { toTypedSchema } from '@vee-validate/zod';

import { useAddItemSaleMutation, useUpdateItemSaleMutation } from '../mutates/useItemSaleMutation';
import { useAddItemOrcamentoMutation, useUpdateItemOrcamentoMutation } from '../mutates/useItemOrcamentoMutation';
import { useToast } from '@/shared/composables/useToast';
import { useGerenteAprovacao } from '@/shared/composables/useGerenteAprovacao';

import {
  ItemSaleFormSchema,
  ItemSaleForm,
  ProductSaleRead,
  ProductSaleCreate,
  ProductSaleUpdate,
} from '../../schemas/productSale.schema';

export function useItemSaleForm(
  saleId: MaybeRef<number | null>,
  selectedItem: Ref<ProductSaleRead | null>,
  onSuccess?: () => void,
  isOrcamento = false,
  requerPinAlterarPreco: MaybeRef<boolean> | ComputedRef<boolean> = false,
  descricaoInicial: MaybeRef<string> = '',
) {
  const addItemSaleMutation = useAddItemSaleMutation();
  const updateItemSaleMutation = useUpdateItemSaleMutation();
  const addItemOrcamentoMutation = useAddItemOrcamentoMutation();
  const updateItemOrcamentoMutation = useUpdateItemOrcamentoMutation();
  const toast = useToast();
  const gerentePreco = useGerenteAprovacao();

  const { handleSubmit, defineField, values, errors, setFieldValue, resetForm, isSubmitting } =
    useForm<ItemSaleForm>({
      validationSchema: toTypedSchema(ItemSaleFormSchema),
      initialValues: {
        descricao: '',
        valor_unitario: 0,
        quantidade: 1,
        desconto: 0,
        custo: 0,
      },
    });

  const [descricao] = defineField('descricao');
  const [valorUnitario] = defineField('valor_unitario');
  const [quantidade] = defineField('quantidade');
  const [desconto] = defineField('desconto');
  const [custo] = defineField('custo');

  watch(
    selectedItem,
    (item) => {
      if (!item) {
        resetForm({
          values: {
            // Abre com o que o usuário já tinha digitado na busca — ele
            // procurou, não achou, e não deve redigitar.
            descricao: unref(descricaoInicial) ?? '',
            valor_unitario: 0,
            quantidade: 1,
            desconto: 0,
            custo: 0,
          },
        });

        return;
      }

      resetForm({
        values: {
          descricao: item.nome ?? '',
          valor_unitario: item.valor_unitario ? item.valor_unitario / 100 : 0,
          quantidade: item.quantidade ?? 1,
          desconto: item.desconto ? item.desconto / 100 : 0,
          custo: item.custo_unitario ? item.custo_unitario / 100 : 0,
        },
      });
    },
    { immediate: true },
  );

  const subtotal = computed(() => {
    const formValues = values;

    return formValues.valor_unitario * formValues.quantidade;
  });

  const total = computed(() => {
    const formValues = values;

    return subtotal.value - formValues.desconto;
  });

  watch([subtotal, desconto], ([currentSubtotal, currentDesconto]) => {
    if (currentDesconto > currentSubtotal) {
      toast.warning('Desconto ajustado para o valor máximo do item');
      desconto.value = currentSubtotal;
      return;
    }

    if (currentDesconto < 0) {
      desconto.value = 0;
    }
  });

  function increaseQuantity() {
    const currentQuantity = values.quantidade;

    setFieldValue('quantidade', currentQuantity + 1);
  }

  function decreaseQuantity() {
    const currentQuantity = values.quantidade;

    setFieldValue('quantidade', Math.max(currentQuantity - 1, 1));
  }

  const avisoEstoqueOpen = ref(false);
  const pendingSubmitValues = ref<ItemSaleForm | null>(null);

  async function executarSalvar(saleIdValue: number, formValues: ItemSaleForm, codigoGerente?: string): Promise<void> {
    if (selectedItem.value) {
      const payload: ProductSaleUpdate = {
        quantidade: formValues.quantidade,
        desconto: formValues.desconto * 100,
      };

      if (selectedItem.value.tipo_produto === 'AVULSO') {
        payload.descricao_avulsa = formValues.descricao;
        payload.valor_unitario = formValues.valor_unitario * 100;
        // Custo interno só existe no avulso; no cadastrado quem manda é o livro
        // de estoque, e o backend recusa se vier.
        payload.custo_unitario = Math.round(formValues.custo * 100);
      } else if (selectedItem.value.tipo_produto === 'CADASTRADO' && unref(requerPinAlterarPreco)) {
        const novoPreco = Math.round(formValues.valor_unitario * 100);
        if (novoPreco !== selectedItem.value.valor_unitario) {
          payload.valor_unitario = novoPreco;
          if (codigoGerente) payload.codigo_gerente = codigoGerente;
        }
      }

      if (isOrcamento) {
        updateItemOrcamentoMutation.mutate(
          { orcamentoId: saleIdValue, productId: selectedItem.value.id, payload },
          { onSuccess },
        );
      } else {
        try {
          await updateItemSaleMutation.mutateAsync(
            { saleId: saleIdValue, productId: selectedItem.value.id, payload },
          );
          onSuccess?.();
        } catch (error: any) {
          const detail = error?.response?.data?.detail;
          if (detail === 'REQUER_APROVACAO_GERENTE') {
            const pin = await gerentePreco.pedirPin();
            if (pin) await executarSalvar(saleIdValue, formValues, pin);
          } else if (detail === 'PIN_GERENTE_INVALIDO') {
            toast.error('PIN do gerente inválido');
            const pin = await gerentePreco.pedirPin();
            if (pin) await executarSalvar(saleIdValue, formValues, pin);
          }
        }
      }

      return;
    }

    const payload: ProductSaleCreate = {
      tipo_produto: 'AVULSO' as const,
      descricao_avulsa: formValues.descricao,
      valor_unitario: formValues.valor_unitario * 100,
      quantidade: formValues.quantidade,
      desconto: formValues.desconto * 100,
      ...(formValues.custo > 0 && { custo_unitario: Math.round(formValues.custo * 100) }),
    };

    if (isOrcamento) {
      addItemOrcamentoMutation.mutate(
        { orcamentoId: saleIdValue, payload },
        { onSuccess },
      );
    } else {
      addItemSaleMutation.mutate(
        { saleId: saleIdValue, payload },
        { onSuccess },
      );
    }
  }

  const submit = handleSubmit((formValues) => {
    const saleIdValue = unref(saleId);

    if (!saleIdValue) return;

    if (selectedItem.value && selectedItem.value.tipo_produto !== 'AVULSO') {
      const estoque = selectedItem.value.estoque_disponivel;
      if (estoque !== null && estoque !== undefined && formValues.quantidade > estoque) {
        pendingSubmitValues.value = formValues;
        avisoEstoqueOpen.value = true;
        return;
      }
    }

    void executarSalvar(saleIdValue, formValues);
  });

  function confirmarSalvarComEstoqueNegativo() {
    const saleIdValue = unref(saleId);
    if (!saleIdValue || !pendingSubmitValues.value) return;
    void executarSalvar(saleIdValue, pendingSubmitValues.value);
    avisoEstoqueOpen.value = false;
    pendingSubmitValues.value = null;
  }

  return {
    errors,
    descricao,
    valorUnitario,
    quantidade,
    desconto,
    custo,
    subtotal,
    total,
    submit,
    increaseQuantity,
    decreaseQuantity,
    resetForm,
    isSubmitting,
    avisoEstoqueOpen,
    confirmarSalvarComEstoqueNegativo,
    gerentePreco,
  };
}
