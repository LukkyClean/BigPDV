import { computed } from 'vue';

import { useSegmento } from '@/shared/composables/useSegmento';
import { useOSFieldDefinition } from './useOSFieldDefinition.queries';
import type { SegmentCapability } from './segmentDefinition.type';

/**
 * Capacidades do segmento — o que ele FAZ, dirigido pelo contrato do backend
 * (GET /ordens-servico/definicao-campos → definicao.capacidades).
 *
 * Existe para a UI parar de perguntar "quem é o cliente?" (`isOficinaMecanica`)
 * e passar a perguntar "o que este segmento faz?". A diferença é o custo do
 * próximo segmento: com `if segmento`, ligar a vistoria em `oficina_moto` exige
 * caçar e editar cada `v-if` do módulo; com capacidades, é uma linha no registry
 * (`app/core/segmentos.py`) e o frontend obedece sozinho.
 *
 * Nenhuma destas capacidades é exclusiva de oficina: aprovação de orçamento e
 * garantia servem qualquer negócio de serviço. Hoje só a oficina as declara
 * porque foi para ela que foram construídas.
 */

/**
 * Fallback usado ENQUANTO o contrato não chegou (a query é assíncrona e a
 * primeira abertura do formulário acontece antes da resposta).
 *
 * Sem isto a aba de Vistoria sumiria e apareceria com um pisca. É o mesmo
 * padrão de `useObjetoLabels`, e pela mesma razão: não piscar a UI errada.
 *
 * Repare que o `if segmento` não sumiu do projeto — ele foi CENTRALIZADO aqui,
 * em um lugar, como fallback de carregamento. Os componentes não o conhecem
 * mais. Quando o contrato chega, ele manda; este mapa nunca decide sozinho.
 */
const FALLBACK_POR_SEGMENTO: Record<string, SegmentCapability[]> = {
  oficina_mecanica: ['vistoria', 'revisoes', 'aprovacao_itens', 'garantia_itens'],
  assistencia_tecnica: [],
};

/**
 * Fallback dos CAMPOS enquanto o contrato não chegou — mesma razão do fallback
 * de capacidades. Lista só os campos que a tela pergunta por nome; o contrato
 * é quem manda assim que responde.
 */
const CAMPOS_FALLBACK_POR_SEGMENTO: Record<string, string[]> = {
  oficina_mecanica: [
    'placa', 'marca', 'modelo', 'cor', 'ano', 'chassi',
    'km_entrada', 'combustivel_nivel', 'combustivel_tipo', 'pneus_estado', 'estepe_estado',
  ],
  assistencia_tecnica: ['imei', 'senha_aparelho', 'acessorios', 'condicoes_aparelho'],
};

export function useCapacidades() {
  const { data, isPending } = useOSFieldDefinition();
  const { segmento } = useSegmento();

  const capacidades = computed<SegmentCapability[]>(() => {
    // Contrato ainda carregando: usa o fallback para não piscar.
    if (isPending.value) return FALLBACK_POR_SEGMENTO[segmento.value ?? ''] ?? [];
    // Contrato é a fonte da verdade. Segmento sem definição = nenhuma capacidade
    // (fluxo genérico de OS), que é o padrão seguro para um segmento novo.
    return data.value?.definicao?.capacidades ?? [];
  });

  /** True se o segmento declara a capacidade. */
  function tem(capacidade: SegmentCapability): boolean {
    return capacidades.value.includes(capacidade);
  }

  /**
   * Nomes de todos os campos que o segmento declara (veículo + check-in).
   * É o que permite a tela perguntar "este segmento usa IMEI?" em vez de
   * "este segmento NÃO é oficina?" — a negação fazia qualquer segmento novo
   * herdar a tela de informática (IMEI, senha, condições) sem ninguém pedir.
   */
  const campos = computed<string[]>(() => {
    if (isPending.value) return CAMPOS_FALLBACK_POR_SEGMENTO[segmento.value ?? ''] ?? [];
    const d = data.value?.definicao;
    if (!d) return [];
    return [...(d.veiculo ?? []), ...(d.checkin ?? [])].map((c) => c.nome);
  });

  /** True se o segmento declara o campo (pelo nome do registry). */
  function temCampo(nome: string): boolean {
    return campos.value.includes(nome);
  }

  return {
    capacidades,
    tem,
    campos,
    temCampo,
    temVistoria: computed(() => tem('vistoria')),
    temRevisoes: computed(() => tem('revisoes')),
    temAprovacaoItens: computed(() => tem('aprovacao_itens')),
    temGarantiaItens: computed(() => tem('garantia_itens')),
  };
}
