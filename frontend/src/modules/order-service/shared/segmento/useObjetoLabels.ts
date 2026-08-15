import { computed, type Component } from 'vue';
import { Car, Smartphone, ShoppingCart, Hammer, Zap, Bike, AirVent, Wrench, Package } from 'lucide-vue-next';

import { useSegmento } from '@/shared/composables/useSegmento';
import { useOSFieldDefinition } from './useOSFieldDefinition.queries';

/**
 * Ícone do objeto por segmento. Chaveado pela string do segmento (não só pelos
 * atuais) para novos segmentos "só funcionarem" ao serem adicionados no backend.
 * Fallback genérico: Package. Futuramente pode vir do contrato (definicao.icone).
 */
const ICONES_SEGMENTO: Record<string, Component> = {
  oficina_mecanica: Car,
  assistencia_tecnica: Smartphone,
  mercado: ShoppingCart,
  marcenaria: Hammer,
  eletricista: Zap,
  moto: Bike,
  ar_condicionado: AirVent,
  serralheria: Wrench,
};

/**
 * Rótulos dinâmicos do "objeto de serviço" por segmento, dirigidos pelo contrato
 * do backend (GET /ordens-servico/definicao-campos).
 *
 * O usuário nunca vê a palavra interna "objeto": em oficina vê "Veículo/Placa",
 * em informática vê "Equipamento/Nº de Série". Novos segmentos passam a exibir
 * seus próprios rótulos sem alterar o frontend — basta o backend definir.
 *
 * Enquanto o contrato carrega (ou para segmentos sem definição dedicada), usa
 * um fallback por segmento para não piscar rótulo errado.
 */
export function useObjetoLabels() {
  const { data } = useOSFieldDefinition();
  const { isOficinaMecanica, segmento } = useSegmento();

  const definicao = computed(() => data.value?.definicao ?? null);

  /** Ícone do objeto conforme o segmento (fallback genérico). */
  const objetoIcon = computed<Component>(
    () => ICONES_SEGMENTO[segmento.value ?? ''] ?? Package,
  );

  const labelSingular = computed(
    () => definicao.value?.rotulo_objeto_singular
      ?? (isOficinaMecanica.value ? 'Veículo' : 'Equipamento'),
  );

  const labelPlural = computed(
    () => definicao.value?.rotulo_objeto_plural
      ?? (isOficinaMecanica.value ? 'Veículos' : 'Equipamentos'),
  );

  const labelIdentificador = computed(
    () => definicao.value?.identificador?.label
      ?? (isOficinaMecanica.value ? 'Placa' : 'Nº de Série'),
  );

  /** Regex de validação do identificador (ex: placa), quando o segmento define. */
  const identificadorRegex = computed(() => definicao.value?.identificador?.regex ?? null);

  return {
    definicao,
    objetoIcon,
    labelSingular,
    labelPlural,
    labelIdentificador,
    identificadorRegex,
  };
}
