/**
 * @fileoverview Cargo form composable with provide/inject pattern
 * @description Manages form state, validation, and submission for cargos
 */

import {
  ref,
  watch,
  computed,
  provide,
  inject,
  type InjectionKey,
  type Ref,
  type ComputedRef,
} from 'vue';
import { useForm } from 'vee-validate';

import { positionValidationSchema } from '../schemas/position.schema';
import {
  applyEndpointPermissions,
  buildPermissionDefaults,
  PERMISSION_KEYS,
} from '../constants/positions.constants';
import type {
  CargoCreate,
  CargoRead,
  CargoUpdate,
  PositionFormData,
} from '../types/positions.types';
import { useCreatePositionMutation, useUpdatePositionMutation } from './usePositionsQuery';
import { usePositionModal } from './usePositionModal';

function getDefaultFormValues(): PositionFormData {
  return {
    nome: '',
    permissoes: buildPermissionDefaults(),
    comissao_venda_percentual: null,
    comissao_servico_percentual: null,
    meta_mensal: null,
    comissao_modo: null,
  };
}

function normalizePermissions(permissoes?: Record<string, boolean>) {
  return {
    ...buildPermissionDefaults(),
    ...(permissoes || {}),
  };
}

export interface PositionFormContext {
  nome: Ref<string>;
  permissoes: Ref<Record<string, boolean>>;
  comissaoVenda: Ref<number | null | undefined>;
  comissaoServico: Ref<number | null | undefined>;
  metaMensal: Ref<number | null | undefined>;
  comissaoModo: Ref<'direto' | 'meta' | null | undefined>;

  errors: Ref<Record<string, string | undefined>>;
  submitCount: Ref<number>;
  values: PositionFormData;
  apiError: Ref<string | null>;
  isPending: ComputedRef<boolean>;

  setPermission: (key: string, value: boolean) => void;
  togglePermission: (key: string) => void;
  setAllPermissions: (value: boolean) => void;

  onSubmit: (e?: Event) => void;
  resetForm: () => void;
}

export const POSITION_FORM_KEY: InjectionKey<PositionFormContext> = Symbol('position-form');

export function usePositionFormProvider() {
  const { selectedPosition, isCreateMode, closeModal } = usePositionModal();

  const {
    handleSubmit,
    errors,
    defineField,
    setValues,
    resetForm,
    submitCount,
    values,
    setErrors,
    setFieldValue,
  } = useForm<PositionFormData>({
    validationSchema: positionValidationSchema,
    initialValues: getDefaultFormValues(),
  });

  const createMutation = useCreatePositionMutation(setErrors);
  const updateMutation = useUpdatePositionMutation(setErrors);

  const [nome] = defineField('nome');
  const [permissoes] = defineField('permissoes');
  const [comissaoVenda] = defineField('comissao_venda_percentual');
  const [comissaoServico] = defineField('comissao_servico_percentual');
  const [metaMensal] = defineField('meta_mensal');
  const [comissaoModo] = defineField('comissao_modo');

  const apiError = ref<string | null>(null);

  function populateForm(position: CargoRead) {
    setValues({
      nome: position.nome,
      permissoes: normalizePermissions(position.permissoes),
      comissao_venda_percentual: position.comissao_venda_percentual ?? null,
      comissao_servico_percentual: position.comissao_servico_percentual ?? null,
      meta_mensal: position.meta_mensal ?? null,
      comissao_modo: position.comissao_modo ?? null,
    });
  }

  watch(
    selectedPosition,
    (position) => {
      if (position) {
        populateForm(position);
      } else {
        resetForm({ values: getDefaultFormValues() });
      }
    },
    { immediate: true },
  );

  function setPermission(key: string, value: boolean) {
    setFieldValue('permissoes', {
      ...normalizePermissions(permissoes.value),
      [key]: value,
    });
  }

  function togglePermission(key: string) {
    const currentValue = !!permissoes.value?.[key];
    setPermission(key, !currentValue);
  }

  function setAllPermissions(value: boolean) {
    const updated = { ...normalizePermissions(permissoes.value) };
    PERMISSION_KEYS.forEach((key) => {
      updated[key] = value;
    });
    setFieldValue('permissoes', updated);
  }

  const onSubmit = handleSubmit(
    async (formData) => {
      apiError.value = null;

      const payload: CargoCreate = {
        nome: formData.nome,
        permissoes: applyEndpointPermissions(formData.permissoes),
        comissao_venda_percentual: formData.comissao_venda_percentual,
        comissao_servico_percentual: formData.comissao_servico_percentual,
        meta_mensal: formData.meta_mensal,
        comissao_modo: formData.comissao_modo,
      };

      if (isCreateMode.value) {
        createMutation.mutate(payload, {
          onSuccess: () => {
            closeModal();
            resetForm({ values: getDefaultFormValues() });
          },
        });
      } else if (selectedPosition.value) {
        const updateData: CargoUpdate = {
          nome: formData.nome,
          permissoes: applyEndpointPermissions(formData.permissoes),
          comissao_venda_percentual: formData.comissao_venda_percentual,
          comissao_servico_percentual: formData.comissao_servico_percentual,
          meta_mensal: formData.meta_mensal,
          comissao_modo: formData.comissao_modo,
        };

        updateMutation.mutate(
          { id: selectedPosition.value.id, data: updateData },
          {
            onSuccess: () => {
              closeModal();
              resetForm({ values: getDefaultFormValues() });
            },
          },
        );
      }
    },
    (validationErrors) => {
      console.log('[DEBUG] Validation errors:', validationErrors);
    },
  );

  const isPending = computed(
    () => createMutation.isPending.value || updateMutation.isPending.value,
  );

  const context: PositionFormContext = {
    nome,
    permissoes,
    comissaoVenda,
    comissaoServico,
    metaMensal,
    comissaoModo,
    errors,
    submitCount,
    values,
    apiError,
    isPending,
    setPermission,
    togglePermission,
    setAllPermissions,
    onSubmit,
    resetForm: () => resetForm({ values: getDefaultFormValues() }),
  };

  provide(POSITION_FORM_KEY, context);

  return context;
}

export function usePositionForm(): PositionFormContext {
  const context = inject(POSITION_FORM_KEY);

  if (!context) {
    throw new Error(
      'usePositionForm must be used within a component that has called usePositionFormProvider',
    );
  }

  return context;
}
