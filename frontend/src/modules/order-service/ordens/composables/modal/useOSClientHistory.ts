import { ref } from 'vue';

import type { ObjetoFormData } from './useOSFormAdapter';
import type { OrderServiceReadDataType } from '../../schemas/orderServiceQuery.schema';

interface UseOSClientHistoryParams {
  setObjetoFormData: (value: ObjetoFormData) => void;
}

export function useOSClientHistory({ setObjetoFormData }: UseOSClientHistoryParams) {
  const isHistoricoModalOpen = ref(false);

  function openHistoricoModal() {
    isHistoricoModalOpen.value = true;
  }

  function closeHistoricoModal() {
    isHistoricoModalOpen.value = false;
  }

  function reutilizarObjeto(os: OrderServiceReadDataType) {
    const objeto = os.objeto;
    setObjetoFormData({
      objeto: objeto.tipo_equipamento ?? '',
      marca: objeto.marca ?? '',
      modelo: objeto.modelo ?? '',
      numero_serie: objeto.numero_serie ?? '',
      imei: objeto.imei ?? '',
      cor: objeto.cor ?? '',
      senha_aparelho: '',
      acessorios: '',
      defeito_relatado: '',
      condicoes_aparelho: '',
    });
    closeHistoricoModal();
  }

  return {
    isHistoricoModalOpen,
    openHistoricoModal,
    closeHistoricoModal,
    reutilizarObjeto,
  };
}
