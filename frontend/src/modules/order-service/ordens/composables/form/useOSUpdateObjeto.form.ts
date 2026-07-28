import { computed } from 'vue';
import { useForm } from 'vee-validate';
import { toTypedSchema } from '@vee-validate/zod';
import type { Ref } from 'vue';

import { OsObjetoUpdateSchema } from '../../schemas/relationship/osObjeto.schema';
import type { OsObjetoUpdateSchemaDataType } from '../../schemas/relationship/osObjeto.schema';

import type { OSUpdateObjetoFormContext } from '../../types/context.type';

import { useUpdateObjetoOSMutation } from '../request/useOrderServiceUpdate.mutate';


export function useOSUpdateObjetoForm(opts: {
  osNumber: Ref<string | null>;
  onSuccess?: () => void;
}): OSUpdateObjetoFormContext {
  const objetoMutation = useUpdateObjetoOSMutation();

  const { handleSubmit, errors, defineField, setValues, resetForm: veeReset } = useForm({
    validationSchema: toTypedSchema(OsObjetoUpdateSchema),
  });

  const [tipo_equipamento] = defineField('tipo_equipamento');
  const [marca] = defineField('marca');
  const [modelo] = defineField('modelo');
  const [numero_serie] = defineField('numero_serie');
  const [imei] = defineField('imei');
  const [cor] = defineField('cor');
  const [cliente_id] = defineField('cliente_id');
  const [proxima_revisao_data] = defineField('proxima_revisao_data');
  const [proxima_revisao_km] = defineField('proxima_revisao_km');
  const [dados_adicionais] = defineField('dados_adicionais');

  const populateForm = (objeto: OsObjetoUpdateSchemaDataType) => {
    setValues({
      tipo_equipamento: objeto.tipo_equipamento,
      marca: objeto.marca,
      modelo: objeto.modelo,
      numero_serie: objeto.numero_serie,
      imei: objeto.imei,
      cor: objeto.cor,
      cliente_id: objeto.cliente_id,
      proxima_revisao_data: objeto.proxima_revisao_data,
      proxima_revisao_km: objeto.proxima_revisao_km,
      dados_adicionais: objeto.dados_adicionais,
    });
  };

  const onSubmit = handleSubmit((formData) => {
    if (!opts.osNumber.value) return;
    objetoMutation.mutate(
      { osNumber: opts.osNumber.value, updatedObjeto: formData },
      { onSuccess: () => opts.onSuccess?.() },
    );
  });

  const resetForm = () => {
    veeReset();
  };

  const isPending = computed(() => objetoMutation.isPending.value);

  return {
    tipo_equipamento,
    marca,
    modelo,
    numero_serie,
    imei,
    cor,
    cliente_id,
    proxima_revisao_data,
    proxima_revisao_km,
    dados_adicionais,
    errors,
    isPending,
    onSubmit,
    resetForm,
    populateForm,
  };
}
