import { ref, watch, type ComputedRef, type Ref } from 'vue';

import { getClientObjetos } from '@/modules/customers/services/customerGet.service';
import type { ObjetoHistorico } from '@/modules/customers/types/clientes.types';

interface UseOSObjetoHistoryParams {
  selectedCliente: ComputedRef<{ id?: number } | null | undefined>;
  ordemServicoCliente: ComputedRef<{ id?: number } | null | undefined>;
  isCreateMode: ComputedRef<boolean>;
  isFormOpen: ComputedRef<boolean>;
  /** Já existe OS carregada/criada no form — evita reabrir a seleção pós-criação. */
  temOSCarregada: ComputedRef<boolean>;
  createObjetoTipo: Ref<string | null | undefined>;
  createObjetoMarca: Ref<string | null | undefined>;
  createObjetoModelo: Ref<string | null | undefined>;
  createObjetoNumeroSerie: Ref<string | null | undefined>;
  createObjetoCor: Ref<string | null | undefined>;
  createObjetoDadosAdicionais: Ref<Record<string, unknown> | null | undefined>;
}

export function useOSObjetoHistory({
  selectedCliente,
  ordemServicoCliente,
  isCreateMode,
  isFormOpen,
  temOSCarregada,
  createObjetoTipo,
  createObjetoMarca,
  createObjetoModelo,
  createObjetoNumeroSerie,
  createObjetoCor,
  createObjetoDadosAdicionais,
}: UseOSObjetoHistoryParams) {
  const objetosHistorico = ref<ObjetoHistorico[]>([]);
  const selectedHistorico = ref<string>('');
  const isObjetoSelectModalOpen = ref(false);
  const wasObjetoSelectShown = ref(false);
  const lastShownClientId = ref<number | null>(null);

  async function fetchObjetosHistorico() {
    const clienteId = selectedCliente.value?.id ?? ordemServicoCliente.value?.id;
    if (!clienteId) {
      objetosHistorico.value = [];
      return;
    }

    try {
      const history = await getClientObjetos(clienteId);
      objetosHistorico.value = history;

      if (
        history.length > 0 &&
        isCreateMode.value &&
        isFormOpen.value &&
        !temOSCarregada.value &&
        !createObjetoTipo.value &&
        !wasObjetoSelectShown.value
      ) {
        isObjetoSelectModalOpen.value = true;
        wasObjetoSelectShown.value = true;
        lastShownClientId.value = clienteId ?? null;
      }
    } catch {
      // histórico de objetos é opcional
    }
  }

  function handleObjetoSelected(objeto: ObjetoHistorico) {
    if (isCreateMode.value) {
      createObjetoTipo.value = objeto.objeto;
      createObjetoMarca.value = objeto.marca || '';
      createObjetoModelo.value = objeto.modelo || '';
      createObjetoNumeroSerie.value = objeto.numero_serie || '';
      // Reaproveita cor e campos dinâmicos do segmento (ex.: chassi, ano).
      createObjetoCor.value = objeto.cor || '';
      createObjetoDadosAdicionais.value = { ...(objeto.dados_adicionais ?? {}) };
    }

    const selectedIndex = objetosHistorico.value.findIndex(
      (item) =>
        item.numero_serie === objeto.numero_serie &&
        item.objeto === objeto.objeto,
    );

    if (selectedIndex !== -1) {
      selectedHistorico.value = String(selectedIndex);
    }

    isObjetoSelectModalOpen.value = false;
  }

  function applyObjetoHistorico() {
    if (!selectedHistorico.value) return;

    const objeto = objetosHistorico.value[parseInt(selectedHistorico.value, 10)];
    if (objeto) {
      handleObjetoSelected(objeto);
    }
  }

  function resetObjetoSelectState() {
    wasObjetoSelectShown.value = false;
    isObjetoSelectModalOpen.value = false;
  }

  watch(
    () => [selectedCliente.value?.id, ordemServicoCliente.value?.id],
    ([newClientId]) => {
      const clientId = newClientId as number | undefined;
      if (clientId && clientId !== lastShownClientId.value) {
        wasObjetoSelectShown.value = false;
      }
      fetchObjetosHistorico();
    },
    { immediate: true },
  );

  return {
    objetosHistorico,
    selectedHistorico,
    isObjetoSelectModalOpen,
    handleObjetoSelected,
    applyObjetoHistorico,
    resetObjetoSelectState,
  };
}
