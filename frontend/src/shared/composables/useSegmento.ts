import { computed } from 'vue';

import { useAuthStore } from '@/shared/stores/auth.store';

/** Segmentos de negócio válidos (espelha o backend em auth.SEGMENTOS_VALIDOS). */
export type Segmento =
  | 'assistencia_tecnica'
  | 'oficina_mecanica'
  | 'mercado'
  | 'marcenaria'
  | 'eletricista'
  | 'outros';

/**
 * Expõe o segmento de negócio da empresa logada e helpers de conveniência.
 * Lê de useAuthStore().userData.empresa.segmento (vindo de /usuarios/me).
 *
 * É a base da renderização por segmento: componentes usam `isOficinaMecanica`
 * para alternar rótulos/campos sem espalhar comparações de string pelo código.
 */
export function useSegmento() {
  const authStore = useAuthStore();

  const segmento = computed<string | null>(
    () => authStore.userData?.empresa?.segmento ?? null,
  );

  const isOficinaMecanica = computed(() => segmento.value === 'oficina_mecanica');
  const isAssistenciaTecnica = computed(() => segmento.value === 'assistencia_tecnica');

  return {
    segmento,
    isOficinaMecanica,
    isAssistenciaTecnica,
  };
}
