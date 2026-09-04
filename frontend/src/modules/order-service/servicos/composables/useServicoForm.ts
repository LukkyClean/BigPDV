import {
  computed,
  inject,
  provide,
  ref,
  watch,
  type ComputedRef,
  type InjectionKey,
  type Ref,
} from 'vue';
import { useForm } from 'vee-validate';
import type { ServiceCreateZod, ServiceUpdateZod } from '../schemas/servicos.schema';
import { ServicoFormData } from '../types/servicos.types';
import { servicoFormValidationSchema } from '../schemas/servicos.schema';
import { toCents } from '../utils/servicos.utils';
import { useCreateServicoMutation, useUpdateServicoMutation } from './useServicosMutations';
import { useServicoModal } from './useServicoModal';
import { recursoDisponivel } from '@/shared/config/planos';
import { getServicoFiscal } from '../services/servicos.service';

const DEFAULT_FORM_VALUES: ServicoFormData = {
  descricao: '',
  valor: 0,
  fiscal_codigo_servico_lc116: '',
  fiscal_cnae: '',
  fiscal_aliquota_iss_display: '',
  fiscal_codigo_tributacao_municipio: '',
  fiscal_cfop_padrao: '',
  fiscal_cst_icms: '',
  fiscal_csosn: '',
  fiscal_unidade_tributavel: '',
  fiscal_c_class_trib: '',
  fiscal_cst_ibs_cbs: '',
  fiscal_aliquota_ibs_display: '',
  fiscal_aliquota_cbs_display: '',
  fiscal_c_benef: '',
};

export interface ServicoFormContext {
  descricao: Ref<string>;
  valor: Ref<number>;
  // Dados fiscais
  fiscal_codigo_servico_lc116: Ref<string>;
  fiscal_cnae: Ref<string>;
  fiscal_aliquota_iss_display: Ref<string>;
  fiscal_codigo_tributacao_municipio: Ref<string>;
  fiscal_cfop_padrao: Ref<string>;
  fiscal_cst_icms: Ref<string>;
  fiscal_csosn: Ref<string>;
  fiscal_unidade_tributavel: Ref<string>;
  fiscal_c_class_trib: Ref<string>;
  fiscal_cst_ibs_cbs: Ref<string>;
  fiscal_aliquota_ibs_display: Ref<string>;
  fiscal_aliquota_cbs_display: Ref<string>;
  fiscal_c_benef: Ref<string>;
  nfeDisponivel: boolean;
  submitCount: Ref<number>;
  errors: Ref<Record<string, string | undefined>>;
  apiError: Ref<string | null>;
  isPending: ComputedRef<boolean>;
  onSubmit: (e?: Event) => void;
  resetForm: () => void;
}

export const SERVICO_FORM_KEY: InjectionKey<ServicoFormContext> = Symbol('servico-form');

export function useServicoFormProvider() {
  const { selectedServico, isCreateMode, closeModal } = useServicoModal();
  const { handleSubmit, defineField, setValues, resetForm, submitCount, errors, setErrors } =

    useForm<ServicoFormData>({
      validationSchema: servicoFormValidationSchema,
      initialValues: { ...DEFAULT_FORM_VALUES },
    });

  const createMutation = useCreateServicoMutation(setErrors);
  const updateMutation = useUpdateServicoMutation(setErrors);

  const apiError = ref<string | null>(null);
  const nfeDisponivel = recursoDisponivel('nfe');

  const [descricao] = defineField('descricao');
  const [valor] = defineField('valor');

  // Campos fiscais
  const [fiscal_codigo_servico_lc116] = defineField('fiscal_codigo_servico_lc116');
  const [fiscal_cnae] = defineField('fiscal_cnae');
  const [fiscal_aliquota_iss_display] = defineField('fiscal_aliquota_iss_display');
  const [fiscal_codigo_tributacao_municipio] = defineField('fiscal_codigo_tributacao_municipio');
  const [fiscal_cfop_padrao] = defineField('fiscal_cfop_padrao');
  const [fiscal_cst_icms] = defineField('fiscal_cst_icms');
  const [fiscal_csosn] = defineField('fiscal_csosn');
  const [fiscal_unidade_tributavel] = defineField('fiscal_unidade_tributavel');
  const [fiscal_c_class_trib] = defineField('fiscal_c_class_trib');
  const [fiscal_cst_ibs_cbs] = defineField('fiscal_cst_ibs_cbs');
  const [fiscal_aliquota_ibs_display] = defineField('fiscal_aliquota_ibs_display');
  const [fiscal_aliquota_cbs_display] = defineField('fiscal_aliquota_cbs_display');
  const [fiscal_c_benef] = defineField('fiscal_c_benef');

  async function populateForm() {
    if (!selectedServico.value) {
      resetForm({ values: { ...DEFAULT_FORM_VALUES } });
      return;
    }

    setValues({
      descricao: selectedServico.value.descricao,
      valor: selectedServico.value.valor / 100,
    });

    // Carrega dados fiscais (se módulo ativo)
    if (nfeDisponivel) {
      try {
        const fiscal = await getServicoFiscal(selectedServico.value.id);
        if (fiscal) {
          setValues({
            fiscal_codigo_servico_lc116: fiscal.codigo_servico_lc116
              ? fiscal.codigo_servico_lc116.replace(/^(\d{2})(\d{2})$/, '$1.$2')
              : '',
            fiscal_cnae: fiscal.cnae
              ? fiscal.cnae.replace(/^(\d{4})(\d)(\d{2})$/, '$1-$2/$3')
              : '',
            fiscal_aliquota_iss_display: fiscal.aliquota_iss != null ? String(Math.round(fiscal.aliquota_iss / 100)) : '',
            fiscal_codigo_tributacao_municipio: fiscal.codigo_tributacao_municipio ?? '',
            fiscal_cfop_padrao: fiscal.cfop_padrao ?? '',
            fiscal_cst_icms: fiscal.cst_icms ?? '',
            fiscal_csosn: fiscal.csosn ?? '',
            fiscal_unidade_tributavel: fiscal.unidade_tributavel ?? '',
            fiscal_c_class_trib: fiscal.c_class_trib ?? '',
            fiscal_cst_ibs_cbs: fiscal.cst_ibs_cbs ?? '',
            fiscal_aliquota_ibs_display: fiscal.aliquota_ibs != null ? String(Math.round(fiscal.aliquota_ibs / 100)) : '',
            fiscal_aliquota_cbs_display: fiscal.aliquota_cbs != null ? String(Math.round(fiscal.aliquota_cbs / 100)) : '',
            fiscal_c_benef: fiscal.c_benef ?? '',
          } as any, false);
        }
      } catch {
        // Falha ao carregar fiscal não deve bloquear a edição
      }
    }
  }

  watch(selectedServico, populateForm, { immediate: true });

  function transformToCreateRequest(formData: ServicoFormData): ServiceCreateZod {
    return {
      descricao: formData.descricao.trim(),
      valor: toCents(formData.valor) || 0,
    };
  }

  function transformToUpdateRequest(formData: ServicoFormData): ServiceUpdateZod {
    return {
      descricao: formData.descricao.trim(),
      valor: toCents(formData.valor),
    };
  }

  const onSubmit = handleSubmit(async (formData) => {
    apiError.value = null;

    if (isCreateMode.value) {
      const request = transformToCreateRequest(formData);
      createMutation.mutate(request, {
        onSuccess: () => {
          closeModal();
          resetForm({ values: { ...DEFAULT_FORM_VALUES } });
        },
        onError: () => {
          apiError.value = 'Erro ao cadastrar serviço';
        },
      });
      return;
    }

    if (selectedServico.value) {
      const request: Record<string, unknown> = { ...transformToUpdateRequest(formData) };

      // Inclui dados fiscais no payload (o service chama o endpoint separado)
      if (nfeDisponivel) {
        const stripSeparadores = (v: string) => v.replace(/[.\-\/]/g, '');
        request.fiscal = {
          codigo_servico_lc116: formData.fiscal_codigo_servico_lc116
            ? stripSeparadores(formData.fiscal_codigo_servico_lc116)
            : null,
          cnae: formData.fiscal_cnae
            ? stripSeparadores(formData.fiscal_cnae)
            : null,
          aliquota_iss: formData.fiscal_aliquota_iss_display
            ? Math.round(Number(formData.fiscal_aliquota_iss_display) * 100)
            : null,
          codigo_tributacao_municipio: formData.fiscal_codigo_tributacao_municipio || null,
          cfop_padrao: formData.fiscal_cfop_padrao || null,
          cst_icms: formData.fiscal_cst_icms || null,
          csosn: formData.fiscal_csosn || null,
          unidade_tributavel: formData.fiscal_unidade_tributavel || null,
          c_class_trib: formData.fiscal_c_class_trib || null,
          cst_ibs_cbs: formData.fiscal_cst_ibs_cbs || null,
          aliquota_ibs: formData.fiscal_aliquota_ibs_display
            ? Math.round(Number(formData.fiscal_aliquota_ibs_display) * 100)
            : null,
          aliquota_cbs: formData.fiscal_aliquota_cbs_display
            ? Math.round(Number(formData.fiscal_aliquota_cbs_display) * 100)
            : null,
          c_benef: formData.fiscal_c_benef || null,
        };
      }

      updateMutation.mutate(
        { id: selectedServico.value.id, data: request as any },
        {
          onSuccess: () => {
            closeModal();
            resetForm({ values: { ...DEFAULT_FORM_VALUES } });
          },
          onError: () => {
            apiError.value = 'Erro ao atualizar serviço';
          },
        },
      );
    }
  });

  const isPending = computed(
    () => createMutation.isPending.value || updateMutation.isPending.value,
  );

  const context: ServicoFormContext = {
    descricao,
    valor,
    fiscal_codigo_servico_lc116,
    fiscal_cnae,
    fiscal_aliquota_iss_display,
    fiscal_codigo_tributacao_municipio,
    fiscal_cfop_padrao,
    fiscal_cst_icms,
    fiscal_csosn,
    fiscal_unidade_tributavel,
    fiscal_c_class_trib,
    fiscal_cst_ibs_cbs,
    fiscal_aliquota_ibs_display,
    fiscal_aliquota_cbs_display,
    fiscal_c_benef,
    nfeDisponivel,
    submitCount,
    errors,
    apiError,
    isPending,
    onSubmit,
    resetForm: () => resetForm({ values: { ...DEFAULT_FORM_VALUES } }),
  };

  provide(SERVICO_FORM_KEY, context);

  return context;
}

export function useServicoForm(): ServicoFormContext {
  const context = inject(SERVICO_FORM_KEY);

  if (!context) {
    throw new Error(
      'useServicoForm must be used within a component that has called useServicoFormProvider',
    );
  }

  return context;
}
