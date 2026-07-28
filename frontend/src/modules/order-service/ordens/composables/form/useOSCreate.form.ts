import { computed, ref } from 'vue';
import { useForm, useFieldArray } from 'vee-validate';

import { orderServiceCreateValidationSchema } from '../../schemas/orderServiceMutate.schema';
import type { OsItemCreateSchemaDataType } from '../../schemas/relationship/osItem.schema';
import type { OrderServiceReadDataType } from '../../schemas/orderServiceQuery.schema';

import type { OSCreateFormContext } from '../../types/context.type';

import { useCreateOrderServiceMutation } from '../request/useOrderServiceCreate.mutate';

import { DEFAULT_OS_CREATE_VALUES, DEFAULT_OS_ITEM_VALUES } from '../../constants/core.constant';
import { useToast } from '@/shared/composables/useToast';


export function useOSCreateForm(opts?: { onSuccess?: (os: OrderServiceReadDataType) => void }): OSCreateFormContext {
  const createMutation = useCreateOrderServiceMutation();
  const toast = useToast();

  const { handleSubmit, errors, defineField, resetForm: veeReset, submitCount } = useForm({
    validationSchema: orderServiceCreateValidationSchema,
    initialValues: { ...DEFAULT_OS_CREATE_VALUES },
  });

  // Campos gerais
  const [prioridade] = defineField('prioridade');
  const [defeito_relatado] = defineField('defeito_relatado');
  const [diagnostico] = defineField('diagnostico');
  const [observacoes] = defineField('observacoes');
  const [desconto] = defineField('desconto');
  const [valor_entrada] = defineField('valor_entrada');
  const [garantia] = defineField('garantia');
  const [data_previsao] = defineField('data_previsao');
  const [senha_aparelho] = defineField('senha_aparelho');
  const [acessorios] = defineField('acessorios');
  const [condicoes_aparelho] = defineField('condicoes_aparelho');

  // Vínculos
  const [cliente_id] = defineField('cliente_id');
  const [funcionario_id] = defineField('funcionario_id');

  // Objeto (campos nested via dot-notation)
  const [objeto_tipo_equipamento] = defineField('objeto.tipo_equipamento');
  const [objeto_marca] = defineField('objeto.marca');
  const [objeto_modelo] = defineField('objeto.modelo');
  const [objeto_numero_serie] = defineField('objeto.numero_serie');
  const [objeto_imei] = defineField('objeto.imei');
  const [objeto_cor] = defineField('objeto.cor');
  const [objeto_proxima_revisao_data] = defineField('objeto.proxima_revisao_data');
  const [objeto_proxima_revisao_km] = defineField('objeto.proxima_revisao_km');
  const [objeto_dados_adicionais] = defineField('objeto.dados_adicionais');

  // Check-in dinâmico no nível da OS (km_entrada, combustível, vistoria)
  const [dados_adicionais] = defineField('dados_adicionais');

  // FieldArray de itens com generic explícito para inferência correta de tipos
  const { fields: itens, push: pushItem, remove: removeItem, update: updateItemField } =
    useFieldArray<OsItemCreateSchemaDataType>('itens');

  const handleAddItem = (item?: Partial<OsItemCreateSchemaDataType>) => {
    pushItem({ ...DEFAULT_OS_ITEM_VALUES, ...item });
  };

  const handleRemoveItem = (index: number) => {
    removeItem(index);
  };

  const handleUpdateItem = (index: number, item: OsItemCreateSchemaDataType) => {
    updateItemField(index, item);
  };

  const usar_credito_cliente = ref(false);

  const resetForm = () => {
    veeReset({ values: { ...DEFAULT_OS_CREATE_VALUES } });
    usar_credito_cliente.value = false;
  };

  const onSubmit = handleSubmit(
    (formData) => {
      createMutation.mutate({ ...formData, usar_credito_cliente: usar_credito_cliente.value }, {
        onSuccess: (data) => {
          opts?.onSuccess?.(data);
        },
        onError: (error) => {
          // Falha vinda do backend (ex.: validação de segmento). Sem isto,
          // o clique em "Criar O.S." falhava em silêncio.
          const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
          toast.error(
            typeof detail === 'string'
              ? detail
              : 'Não foi possível criar a O.S. Verifique os dados e tente novamente.',
          );
        },
      });
    },
    // Validação (Zod) reprovou: mostra o primeiro campo obrigatório pendente.
    // Agnóstico de segmento — serve oficina hoje e os próximos segmentos.
    ({ errors }) => {
      const primeiroErro = Object.values(errors).find(Boolean);
      toast.error(String(primeiroErro ?? 'Preencha os campos obrigatórios destacados.'));
    },
  );

  const isPending = computed(() => createMutation.isPending.value);

  return {
    prioridade,
    defeito_relatado,
    diagnostico,
    observacoes,
    desconto,
    valor_entrada,
    garantia,
    data_previsao,
    senha_aparelho,
    acessorios,
    condicoes_aparelho,
    cliente_id,
    funcionario_id,
    objeto_tipo_equipamento,
    objeto_marca,
    objeto_modelo,
    objeto_numero_serie,
    objeto_imei,
    objeto_cor,
    objeto_proxima_revisao_data,
    objeto_proxima_revisao_km,
    objeto_dados_adicionais,
    dados_adicionais,
    itens,
    handleAddItem,
    handleRemoveItem,
    handleUpdateItem,
    usar_credito_cliente,
    errors,
    submitCount,
    isPending,
    onSubmit,
    resetForm,
  };
}
