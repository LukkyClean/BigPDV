import { computed, type Component } from 'vue';
import { Car, Smartphone, ShoppingCart, Hammer, Zap, Bike, AirVent, Wrench, Shirt, Package } from 'lucide-vue-next';

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
  serigrafia: Shirt,
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

  /**
   * Rótulo do texto livre relatado pelo cliente.
   *
   * O padrão é "Defeito Relatado", palavra por palavra: é o que oficina e
   * informática imprimem e mostram hoje, e as duas estão em produção. Só muda
   * para quem declarar outro no registry — em serigrafia, "Descrição do
   * pedido", porque ninguém traz camisa quebrada.
   */
  const labelDefeito = computed(
    () => definicao.value?.rotulo_defeito ?? 'Defeito Relatado',
  );

  const placeholderDefeito = computed(
    () => definicao.value?.placeholder_defeito
      ?? 'Descreva o problema principal relatado pelo cliente...',
  );

  /**
   * Quem executa o serviço. O padrão é "Técnico" — o que oficina e informática
   * mostram hoje, e as duas estão em produção.
   */
  const labelResponsavel = computed(
    () => definicao.value?.rotulo_responsavel ?? 'Técnico',
  );

  /**
   * Rótulo que o segmento dá a uma COLUNA do objeto (`marca`, `modelo`, `cor`).
   *
   * A via impressa mostrava "Marca: BigTec / Modelo: BigTec" numa OS de
   * serigrafia — os nomes internos das colunas, que não dizem nada ao cliente.
   * O contrato já sabe que ali é "Empresa / Marca da estampa" e "Nome da arte":
   * os campos declaram `origem: 'coluna'` e `coluna: 'marca'`.
   *
   * Sem declaração, devolve o padrão — que é o que oficina e informática
   * imprimem hoje, palavra por palavra.
   */
  function labelDaColuna(coluna: string, padrao: string): string {
    const def = definicao.value;
    if (!def) return padrao;

    const todos = [
      ...(def.veiculo ?? []),
      ...(def.checkin ?? []),
      ...(def.tipos ?? []).flatMap((tipo) => tipo.campos),
    ];
    const campo = todos.find((c) => c.origem === 'coluna' && (c.coluna ?? c.nome) === coluna);
    return campo?.label ?? padrao;
  }

  return {
    definicao,
    objetoIcon,
    labelSingular,
    labelPlural,
    labelIdentificador,
    identificadorRegex,
    labelDefeito,
    placeholderDefeito,
    labelResponsavel,
    labelDaColuna,
  };
}
