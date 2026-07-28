import { computed } from 'vue';
import { useForm } from 'vee-validate';
import type { Ref } from 'vue';

import { orderServiceUpdateValidationSchema } from '../../schemas/orderServiceMutate.schema';
import type { OrderServiceReadDataType } from '../../schemas/orderServiceQuery.schema';

import type { OSUpdateGeralFormContext } from '../../types/context.type';

import { useUpdateOrderServiceMutation } from '../request/useOrderServiceUpdate.mutate';


export function useOSUpdateGeralForm(opts: {
  osNumber: Ref<string | null>;
  onSuccess?: () => void;
}): OSUpdateGeralFormContext {
  const updateMutation = useUpdateOrderServiceMutation();

  const { handleSubmit, errors, defineField, setValues, resetForm: veeReset } = useForm({
    validationSchema: orderServiceUpdateValidationSchema,
  });

  const [status] = defineField('status');
  const [prioridade] = defineField('prioridade');
  const [defeito_relatado] = defineField('defeito_relatado');
  const [diagnostico] = defineField('diagnostico');
  const [solucao] = defineField('solucao');
  const [observacoes] = defineField('observacoes');
  const [desconto] = defineField('desconto');
  const [valor_entrada] = defineField('valor_entrada');
  const [taxa_entrega] = defineField('taxa_entrega');
  const [garantia] = defineField('garantia');
  const [data_previsao] = defineField('data_previsao');
  const [senha_aparelho] = defineField('senha_aparelho');
  const [acessorios] = defineField('acessorios');
  const [condicoes_aparelho] = defineField('condicoes_aparelho');
  const [funcionario_id] = defineField('funcionario_id');
  const [dados_adicionais] = defineField('dados_adicionais');

  const populateForm = (os: OrderServiceReadDataType) => {
    setValues({
      status: os.status,
      prioridade: os.prioridade,
      defeito_relatado: os.defeito_relatado,
      diagnostico: os.diagnostico ?? undefined,
      solucao: os.solucao ?? undefined,
      observacoes: os.observacoes ?? undefined,
      desconto: os.desconto ?? undefined,
      valor_entrada: os.valor_entrada ?? 0,
      taxa_entrega: os.taxa_entrega ?? 0,
      garantia: os.garantia ?? undefined,
      data_previsao: os.data_previsao ?? undefined,
      senha_aparelho: os.senha_aparelho ?? undefined,
      acessorios: os.acessorios ?? undefined,
      condicoes_aparelho: os.condicoes_aparelho ?? undefined,
      funcionario_id: os.funcionario?.id ?? undefined,
      dados_adicionais: os.dados_adicionais ?? undefined,
    });
  };

  const onSubmit = handleSubmit((formData) => {
    if (!opts.osNumber.value) return;
    updateMutation.mutate(
      { osNumber: opts.osNumber.value, updatedOS: formData },
      { onSuccess: () => opts.onSuccess?.() },
    );
  });

  const onSubmitTextOnly = () => {
    if (!opts.osNumber.value) return;
    updateMutation.mutate(
      {
        osNumber: opts.osNumber.value,
        updatedOS: {
          defeito_relatado: defeito_relatado.value ?? undefined,
          diagnostico: diagnostico.value ?? undefined,
          solucao: solucao.value ?? undefined,
          observacoes: observacoes.value ?? undefined,
        },
      },
      { onSuccess: () => opts.onSuccess?.() },
    );
  };

  const resetForm = () => {
    veeReset();
  };

  const isPending = computed(() => updateMutation.isPending.value);

  return {
    status,
    prioridade,
    defeito_relatado,
    diagnostico,
    solucao,
    observacoes,
    desconto,
    valor_entrada,
    taxa_entrega,
    garantia,
    data_previsao,
    senha_aparelho,
    acessorios,
    condicoes_aparelho,
    funcionario_id,
    dados_adicionais,
    errors,
    isPending,
    onSubmit,
    onSubmitTextOnly,
    resetForm,
    populateForm,
  };
}
