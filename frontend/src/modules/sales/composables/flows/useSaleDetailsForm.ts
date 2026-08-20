import { reactive, watch, computed, unref, type MaybeRef } from 'vue';
import { useDebounceFn } from '@vueuse/core';

import { useUpdateSaleMutation } from '../mutates/useUpdateSaleMutation';
import { useToast } from '@/shared/composables/useToast';
import { useGerenteAprovacao } from '@/shared/composables/useGerenteAprovacao';
import type { SaleRead, SaleUpdate } from '../../schemas/sale.schema';
import { focarBuscaDeProduto } from '../../focarBusca.util';

export function useSaleDetailsForm(sale: MaybeRef<SaleRead | undefined>) {
  const updateSaleMutation = useUpdateSaleMutation();
  const toast = useToast();
  const gerenteDesconto = useGerenteAprovacao();

  const form: SaleUpdate = reactive({
    desconto: 0,
    entrega: 0,
    observacao: '',
    observacao_interna: '',
  });

  const saleId = computed(() => unref(sale)?.id);

  let isHydrating = false;
  let lastHydratedId: number | null = null;

  function hydrateForm(currentSale: SaleRead, forceTextFields = false) {
    isHydrating = true;

    form.desconto = currentSale.descontos ? currentSale.descontos / 100 : 0;
    form.entrega = currentSale.entrega ? currentSale.entrega / 100 : 0;

    if (forceTextFields) {
      form.observacao = currentSale.observacao ?? '';
      form.observacao_interna = currentSale.observacao_interna ?? '';
    }

    queueMicrotask(() => {
      isHydrating = false;
    });
  }

  watch(
    () => unref(sale),
    (currentSale) => {
      if (!currentSale) return;
      const isNewSale = currentSale.id !== lastHydratedId;
      hydrateForm(currentSale, isNewSale);
      lastHydratedId = currentSale.id;
    },
    { immediate: true },
  );

  async function saveNow(codigoGerente?: string): Promise<void> {
    if (!saleId.value) return;

    const currentSale = unref(sale);
    const subtotal = currentSale?.subtotal ?? 0;

    const descontoAtual = form.desconto ?? 0;
    if (Math.round(descontoAtual * 100) > subtotal) {
      form.desconto = subtotal / 100;
      toast.warning('Desconto ajustado para o valor máximo permitido');
    }

    const payload: SaleUpdate = { ...form, ...(codigoGerente ? { codigo_gerente: codigoGerente } : {}) };

    try {
      await updateSaleMutation.mutateAsync({ payload, saleId: saleId.value });
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      if (detail === 'REQUER_APROVACAO_GERENTE') {
        const pin = await gerenteDesconto.pedirPin();
        if (pin) await saveNow(pin);
        // Aprovado ou cancelado, a interrupção acabou: o cursor volta para a
        // venda. Sem isto o foco fica no vazio deixado pelo modal e a bipada
        // seguinte não chega em lugar nenhum.
        focarBuscaDeProduto();
      } else if (detail === 'PIN_GERENTE_INVALIDO') {
        toast.error('PIN inválido. Tente novamente.');
        const pin = await gerenteDesconto.pedirPin();
        if (pin) await saveNow(pin);
        focarBuscaDeProduto();
      } else {
        const sale_ = unref(sale);
        if (sale_) hydrateForm(sale_, false);
      }
    }
  }

  const debouncedSave = useDebounceFn(() => {
    if (isHydrating) return;
    void saveNow();
  }, 700);

  watch(
    () => [form.observacao, form.observacao_interna],
    () => {
      if (isHydrating) return;
      debouncedSave();
    }
  )

  return {
    form,
    isSaving: updateSaleMutation.isPending,
    saveNow: (codigoGerente?: string) => void saveNow(codigoGerente),
    gerenteDesconto,
  }
}
