import { computed, unref, type MaybeRef } from 'vue';
import { refDebounced } from '@vueuse/core';
import { useQuery } from '@tanstack/vue-query';

import { verificarIdentificadorObjeto } from '../../../services/orderServiceGet.service';
import { ORDER_SERVICE_QUERY_KEY } from '../../../constants/core.constant';
import type { IdentificadorConflitoDataType } from '../../../schemas/relationship/identificadorCheck.schema';

/**
 * Só evita uma requisição por tecla — NÃO é a regra de "isto é um identificador".
 * A regra mora no backend (`identificador_pesquisavel`), que conhece o segmento e
 * a lista de placeholders. O piso aqui é de propósito mais frouxo que o de lá,
 * para nunca engolir um aviso que o servidor daria.
 */
const MIN_CARACTERES_PARA_CONSULTAR = 3;

const DEBOUNCE_MS = 500;

/**
 * Avisa quando a placa / nº de série digitada já pertence a outro cliente.
 *
 * Nunca bloqueia: a máquina pode ter sido vendida. O backend também se cala
 * quando o texto não identifica um bem ("S/N") e quando o próprio cliente já tem
 * aquele objeto — é isso que faz o aviso sair só na primeira OS após a troca de
 * dono, sem guardar estado nenhum.
 */
export function useOSIdentificadorCheck(
  identificador: MaybeRef<string | null | undefined>,
  clienteId: MaybeRef<number | null | undefined>,
  habilitado: MaybeRef<boolean> = true,
) {
  const bruto = computed(() => unref(identificador) ?? '');
  const debounced = refDebounced(bruto, DEBOUNCE_MS);

  const termo = computed(() => (debounced.value ?? '').trim());
  const clienteIdAtual = computed(() => unref(clienteId) ?? null);

  const enabled = computed(
    () => unref(habilitado) && termo.value.length >= MIN_CARACTERES_PARA_CONSULTAR,
  );

  const query = useQuery({
    queryKey: computed(() => [
      ORDER_SERVICE_QUERY_KEY,
      'identificador-check',
      termo.value,
      clienteIdAtual.value,
    ]),
    queryFn: () => verificarIdentificadorObjeto(termo.value, clienteIdAtual.value),
    enabled,
    // O dado é sobre "quem já tem este identificador": muda pouco durante o
    // preenchimento de uma OS, e reconsultar a cada foco só geraria ruído.
    staleTime: 1000 * 60,
    retry: false,
  });

  const conflitos = computed<IdentificadorConflitoDataType[]>(
    () => query.data.value?.conflitos ?? [],
  );

  return {
    conflitos,
    temConflito: computed(() => conflitos.value.length > 0),
    isChecking: query.isFetching,
  };
}
