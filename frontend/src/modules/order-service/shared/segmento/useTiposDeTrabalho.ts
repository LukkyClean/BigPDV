import { computed } from 'vue';

import { useOSFieldDefinition } from './useOSFieldDefinition.queries';
import type { SegmentField, SegmentWorkType } from './segmentDefinition.type';

/**
 * Tipos de trabalho do segmento — "o que é esta OS?", quando o segmento tem
 * mais de um processo.
 *
 * Existe separado de `useCapacidades` de propósito: aquele responde o que o
 * SEGMENTO faz, este responde o que ESTA OS é. Juntar os dois faria um
 * composable com duas responsabilidades e dois motivos para mudar.
 *
 * Segmento sem `tipos` (oficina, informática) responde `temTipos = false` e
 * tudo continua pelo caminho de sempre — é isso que mantém as duas lojas em
 * produção intocadas.
 */
export function useTiposDeTrabalho() {
  const { data } = useOSFieldDefinition();

  const tipos = computed<SegmentWorkType[]>(() => data.value?.definicao?.tipos ?? []);

  const temTipos = computed(() => tipos.value.length > 0);

  /** Opções prontas para o seletor. */
  const opcoes = computed(() =>
    tipos.value.map((tipo) => ({ value: tipo.id, label: tipo.label })),
  );

  /**
   * O tipo padrão é o primeiro declarado. Uma OS nova já abre com ele
   * escolhido — formulário vazio esperando uma escolha é o tipo de tela que
   * faz o atendente achar que o sistema travou.
   */
  const tipoPadrao = computed<string | null>(() => tipos.value[0]?.id ?? null);

  function tipoPorId(id: string | null | undefined): SegmentWorkType | null {
    if (!id) return null;
    return tipos.value.find((tipo) => tipo.id === id) ?? null;
  }

  /** Campos do tipo escolhido; vazio se o tipo não existe (ou não há tipos). */
  function camposDoTipo(id: string | null | undefined): SegmentField[] {
    return tipoPorId(id)?.campos ?? [];
  }

  /**
   * Os campos agrupados na ordem em que foram declarados, para o formulário
   * desenhar seção por seção. Campo sem `grupo` cai num bloco sem título, no
   * lugar em que apareceu.
   */
  function gruposDoTipo(id: string | null | undefined) {
    const grupos: { titulo: string | null; campos: SegmentField[] }[] = [];
    for (const campo of camposDoTipo(id)) {
      const titulo = campo.grupo ?? null;
      const ultimo = grupos[grupos.length - 1];
      if (ultimo && ultimo.titulo === titulo) {
        ultimo.campos.push(campo);
      } else {
        grupos.push({ titulo, campos: [campo] });
      }
    }
    return grupos;
  }

  return { tipos, temTipos, opcoes, tipoPadrao, tipoPorId, camposDoTipo, gruposDoTipo };
}
