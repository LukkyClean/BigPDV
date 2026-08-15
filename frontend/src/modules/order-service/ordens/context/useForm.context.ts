import { computed, inject, provide } from 'vue';
import type { ComputedRef, InjectionKey, Ref } from 'vue';

import type { OSFormContext } from '../types/context.type';
import type { OrderServiceReadDataType } from '../schemas/orderServiceQuery.schema';
import { useOSCreateForm } from '../composables/form/useOSCreate.form';
import { useOSUpdateGeralForm } from '../composables/form/useOSUpdateGeral.form';
import { useOSUpdateObjetoForm } from '../composables/form/useOSUpdateObjeto.form';
import { useOSItemForm } from '../composables/form/useOSItem.form';
import { useOSFinalizarForm } from '../composables/form/useOSFinalizar.form';
import { useOSCancelarForm } from '../composables/form/useOSCancelar.form';

export const OS_FORM_CONTEXT_KEY: InjectionKey<OSFormContext> = Symbol('os-form-context');

export function useOSFormProvider(opts: {
  osNumber: Ref<string | null>;
  isCreateMode: ComputedRef<boolean>;
  onCreateSuccess?: (os: OrderServiceReadDataType) => void;
  onUpdateSuccess?: () => void;
  onItemSuccess?: () => void;
  onFinalizarSuccess?: () => void;
  onCancelarSuccess?: () => void;
}): OSFormContext {

  const criar = useOSCreateForm({ onSuccess: opts.onCreateSuccess });


  const atualizarGeral = useOSUpdateGeralForm({
    osNumber: opts.osNumber,
    onSuccess: opts.onUpdateSuccess,
  });


  const atualizarObjeto = useOSUpdateObjetoForm({
    osNumber: opts.osNumber,
    // sem onSuccess: objeto auto-save não fecha o modal
  });


  const item = useOSItemForm({
    osNumber: opts.osNumber,
    onSuccess: opts.onItemSuccess,
  });

  const finalizar = useOSFinalizarForm({
    osNumber: opts.osNumber,
    onSuccess: opts.onFinalizarSuccess,
  });

  
  const cancelar = useOSCancelarForm({
    osNumber: opts.osNumber,
    onSuccess: opts.onCancelarSuccess,
  });

  const context: OSFormContext = {
    currentOsNumber: opts.osNumber,
    isCreateMode: opts.isCreateMode,
    criar,
    atualizarGeral,
    atualizarObjeto,
    item,
    finalizar,
    cancelar,
  };

  provide(OS_FORM_CONTEXT_KEY, context);

  return context;
}

export function useOSForm(): OSFormContext {
  const context = inject(OS_FORM_CONTEXT_KEY);

  if (!context) {
    throw new Error(
      '[useOSForm] Contexto não encontrado. ' +
        'Certifique-se de que useOSFormProvider foi chamado em um componente ancestral.',
    );
  }

  return context;
}


export function useOSFormPendingState(context: OSFormContext): ComputedRef<boolean> {
  return computed(
    () =>
      context.criar.isPending.value ||
      context.atualizarGeral.isPending.value ||
      context.atualizarObjeto.isPending.value ||
      context.item.isPending.value ||
      context.finalizar.isPending.value ||
      context.cancelar.isPending.value,
  );
}
