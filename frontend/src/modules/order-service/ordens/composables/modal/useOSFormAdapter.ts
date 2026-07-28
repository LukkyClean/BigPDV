import { computed, type ComputedRef } from 'vue';

import type { OSFormContext } from '../../types/context.type';
import type { OsPriorityEnumDataType, OsStatusEnumDataType } from '../../schemas/enums/osEnums.schema';

export interface ObjetoFormData {
  objeto: string;
  marca: string;
  modelo: string;
  numero_serie: string;
  imei: string;
  cor: string;
  senha_aparelho: string;
  acessorios: string;
  defeito_relatado: string;
  condicoes_aparelho: string;
}

interface UseOSFormAdapterParams {
  form: OSFormContext;
  isCreateMode: ComputedRef<boolean>;
}

export function useOSFormAdapter({ form, isCreateMode }: UseOSFormAdapterParams) {
  const objetoFormData = computed<ObjetoFormData>({
    get: () => {
      if (isCreateMode.value) {
        return {
          objeto: form.criar.objeto_tipo_equipamento.value ?? '',
          marca: form.criar.objeto_marca.value ?? '',
          modelo: form.criar.objeto_modelo.value ?? '',
          numero_serie: form.criar.objeto_numero_serie.value ?? '',
          imei: form.criar.objeto_imei.value ?? '',
          cor: form.criar.objeto_cor.value ?? '',
          senha_aparelho: form.criar.senha_aparelho.value ?? '',
          acessorios: form.criar.acessorios.value ?? '',
          defeito_relatado: form.criar.defeito_relatado.value ?? '',
          condicoes_aparelho: form.criar.condicoes_aparelho.value ?? '',
        };
      }

      return {
        objeto: form.atualizarObjeto.tipo_equipamento.value ?? '',
        marca: form.atualizarObjeto.marca.value ?? '',
        modelo: form.atualizarObjeto.modelo.value ?? '',
        numero_serie: form.atualizarObjeto.numero_serie.value ?? '',
        imei: form.atualizarObjeto.imei.value ?? '',
        cor: form.atualizarObjeto.cor.value ?? '',
        senha_aparelho: form.atualizarGeral.senha_aparelho.value ?? '',
        acessorios: form.atualizarGeral.acessorios.value ?? '',
        defeito_relatado: form.atualizarGeral.defeito_relatado.value ?? '',
        condicoes_aparelho: form.atualizarGeral.condicoes_aparelho.value ?? '',
      };
    },
    set: (value) => {
      if (isCreateMode.value) {
        form.criar.objeto_tipo_equipamento.value = value.objeto;
        form.criar.objeto_marca.value = value.marca;
        form.criar.objeto_modelo.value = value.modelo;
        form.criar.objeto_numero_serie.value = value.numero_serie;
        form.criar.objeto_imei.value = value.imei;
        form.criar.objeto_cor.value = value.cor;
        form.criar.senha_aparelho.value = value.senha_aparelho;
        form.criar.acessorios.value = value.acessorios;
        form.criar.defeito_relatado.value = value.defeito_relatado;
        form.criar.condicoes_aparelho.value = value.condicoes_aparelho;
        return;
      }

      form.atualizarObjeto.tipo_equipamento.value = value.objeto;
      form.atualizarObjeto.marca.value = value.marca;
      form.atualizarObjeto.modelo.value = value.modelo;
      form.atualizarObjeto.numero_serie.value = value.numero_serie;
      form.atualizarObjeto.imei.value = value.imei;
      form.atualizarObjeto.cor.value = value.cor;
      form.atualizarGeral.senha_aparelho.value = value.senha_aparelho;
      form.atualizarGeral.acessorios.value = value.acessorios;
      form.atualizarGeral.defeito_relatado.value = value.defeito_relatado;
      form.atualizarGeral.condicoes_aparelho.value = value.condicoes_aparelho;
    },
  });

  // dados_adicionais do OBJETO (ex: oficina → chassi, ano).
  const objetoDados = computed<Record<string, unknown>>({
    get: () => (isCreateMode.value
      ? form.criar.objeto_dados_adicionais.value
      : form.atualizarObjeto.dados_adicionais.value) ?? {},
    set: (value) => {
      if (isCreateMode.value) {
        form.criar.objeto_dados_adicionais.value = value;
        return;
      }
      form.atualizarObjeto.dados_adicionais.value = value;
    },
  });

  // dados_adicionais da OS / check-in (ex: oficina → km_entrada, combustível, vistoria).
  const osDados = computed<Record<string, unknown>>({
    get: () => (isCreateMode.value
      ? form.criar.dados_adicionais.value
      : form.atualizarGeral.dados_adicionais.value) ?? {},
    set: (value) => {
      if (isCreateMode.value) {
        form.criar.dados_adicionais.value = value;
        return;
      }
      form.atualizarGeral.dados_adicionais.value = value;
    },
  });

  const controlsStatus = computed<OsStatusEnumDataType>(() => {
    if (isCreateMode.value) return 'ABERTA';
    return (form.atualizarGeral.status.value as OsStatusEnumDataType | undefined) ?? 'ABERTA';
  });

  const controlsFuncionarioId = computed<string>(() => {
    if (isCreateMode.value) return String(form.criar.funcionario_id.value ?? '');
    return String(form.atualizarGeral.funcionario_id.value ?? '');
  });

  const controlsPrioridade = computed<OsPriorityEnumDataType>(() => {
    if (isCreateMode.value) {
      return (form.criar.prioridade.value as OsPriorityEnumDataType | undefined) ?? 'NORMAL';
    }
    return (form.atualizarGeral.prioridade.value as OsPriorityEnumDataType | undefined) ?? 'NORMAL';
  });

  const controlsDataPrevisao = computed<string>(() => {
    if (isCreateMode.value) return form.criar.data_previsao.value ?? '';
    return form.atualizarGeral.data_previsao.value ?? '';
  });

  function handleStatusUpdate(value: OsStatusEnumDataType) {
    if (!isCreateMode.value) {
      form.atualizarGeral.status.value = value;
    }
  }

  function handleFuncionarioIdUpdate(value: string) {
    const funcionarioId = Number(value) || undefined;
    if (isCreateMode.value) {
      form.criar.funcionario_id.value = funcionarioId;
      return;
    }
    form.atualizarGeral.funcionario_id.value = funcionarioId;
  }

  function handlePrioridadeUpdate(value: OsPriorityEnumDataType) {
    if (isCreateMode.value) {
      form.criar.prioridade.value = value;
      return;
    }
    form.atualizarGeral.prioridade.value = value;
  }

  function handleDataPrevisaoUpdate(value: string) {
    if (isCreateMode.value) {
      form.criar.data_previsao.value = value;
      return;
    }
    form.atualizarGeral.data_previsao.value = value;
  }

  const currentDiagnostico = computed<string>(() => {
    if (isCreateMode.value) return form.criar.diagnostico.value ?? '';
    return form.atualizarGeral.diagnostico.value ?? '';
  });

  function handleDiagnosticoUpdate(value: string) {
    if (isCreateMode.value) {
      form.criar.diagnostico.value = value;
      return;
    }
    form.atualizarGeral.diagnostico.value = value;
  }

  return {
    objetoFormData,
    objetoDados,
    osDados,
    controlsStatus,
    controlsFuncionarioId,
    controlsPrioridade,
    controlsDataPrevisao,
    handleStatusUpdate,
    handleFuncionarioIdUpdate,
    handlePrioridadeUpdate,
    handleDataPrevisaoUpdate,
    currentDiagnostico,
    handleDiagnosticoUpdate,
  };
}
