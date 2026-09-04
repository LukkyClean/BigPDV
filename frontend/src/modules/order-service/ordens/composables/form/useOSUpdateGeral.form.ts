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

  const { handleSubmit, errors, defineField, setValues, values, resetForm: veeReset } = useForm({
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
  const [forma_pagamento_entrada_id] = defineField('forma_pagamento_entrada_id');
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
      // Vem do objeto aninhado (o Read expõe a forma, não o id cru).
      forma_pagamento_entrada_id: os.forma_pagamento_entrada?.id ?? undefined,
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

  /**
   * Grava os campos gerais e RESOLVE quando o servidor responde.
   *
   * Existe para a finalização. `onSubmit` é fire-and-forget (o botão Salvar não
   * espera nada) e ainda dispara o `onSuccess`, que FECHA o modal da OS — os
   * dois comportamentos erram no caminho de finalizar.
   *
   * O modal de finalização lê `ordemServico.valor_entrada` do servidor, e não o
   * que está digitado na tela. Sem gravar antes, quem preenchia o adiantamento e
   * clicava direto em Finalizar via R$ 0,00 e precisava adivinhar que tinha de
   * salvar primeiro.
   */
  async function salvarPendentes(): Promise<void> {
    const numero = opts.osNumber.value;
    if (!numero) return;
    await updateMutation.mutateAsync({
      osNumber: numero,
      updatedOS: { ...values },
    });
  }

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
    forma_pagamento_entrada_id,
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
    salvarPendentes,
    resetForm,
    populateForm,
  };
}
