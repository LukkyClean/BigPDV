import { ref, type ComputedRef } from 'vue';

import type { OSReopenMode } from './useOSStatusLocks';

interface UseOSReopenStateParams {
  osNumber: ComputedRef<string | null>;
  /** clientePagou: false quando o operador confirma que o cliente NÃO pagou o valor anterior. */
  onReopenRequest: (osNumber: string, clientePagou: boolean) => void;
  onFullReopen: () => void;
}

export function useOSReopenState({
  osNumber,
  onReopenRequest,
  onFullReopen: _onFullReopen,
}: UseOSReopenStateParams) {
  const isReopenOptionsOpen = ref(false);
  const reopenMode = ref<OSReopenMode>('NONE');

  function handleReopenClick() {
    isReopenOptionsOpen.value = true;
  }

  function handleReopenCancel() {
    isReopenOptionsOpen.value = false;
    reopenMode.value = 'NONE';
  }

  function handleReopenTextOnly() {
    reopenMode.value = 'TEXT_ONLY';
    isReopenOptionsOpen.value = false;
  }

  function handleReopenFull(clientePagou: boolean = true) {
    const currentOsNumber = osNumber.value;
    if (!currentOsNumber) return;

    reopenMode.value = 'FULL';
    isReopenOptionsOpen.value = false;
    onReopenRequest(currentOsNumber, clientePagou);
  }

  function resetReopenState() {
    reopenMode.value = 'NONE';
    isReopenOptionsOpen.value = false;
  }

  return {
    isReopenOptionsOpen,
    reopenMode,
    handleReopenClick,
    handleReopenCancel,
    handleReopenTextOnly,
    handleReopenFull,
    resetReopenState,
  };
}
