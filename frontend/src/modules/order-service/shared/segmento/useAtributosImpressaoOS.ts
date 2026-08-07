import { computed } from 'vue';

import { useOSFieldDefinition } from './useOSFieldDefinition.queries';
import type { SegmentField } from './segmentDefinition.type';

/** Par rótulo/valor pronto para sair na via, já formatado como texto. */
export interface AtributoImpresso {
  label: string;
  valor: string;
}

/**
 * Campos que a via já imprime em linha própria (Marca, Modelo, identificador,
 * Cor). Sem esta lista o veículo sairia com "Placa" duas vezes.
 */
const JA_NA_VIA = new Set(['placa', 'numero_serie', 'marca', 'modelo', 'cor']);

/**
 * Do check-in (escopo OS), só a quilometragem entra na via do cliente.
 * Combustível, pneus, estepe, prisma e CT são conteúdo da ficha de vistoria —
 * no quadro do recibo eles empurrariam o resto da folha para baixo.
 */
const CHECKIN_NA_VIA = ['km_entrada'];

/**
 * Atributos do objeto que a via imprime ALÉM das linhas fixas, lidos do
 * contrato do segmento (GET /ordens-servico/definicao-campos) e dos
 * `dados_adicionais` gravados pelo formulário.
 *
 * Dirigido pelo contrato de propósito: em oficina isto rende Ano, Chassi e KM
 * de entrada sem citar nenhum desses nomes aqui, e um segmento novo que declare
 * seus campos passa a imprimi-los sozinho. Em informática `veiculo` é `[]` e
 * não existe `km_entrada`, então a lista sai vazia e a via não muda.
 */
export function useAtributosImpressaoOS() {
  const { data } = useOSFieldDefinition();

  const definicao = computed(() => data.value?.definicao ?? null);

  function atributos(
    dadosObjeto: Record<string, unknown> | null | undefined,
    dadosOS: Record<string, unknown> | null | undefined,
  ): AtributoImpresso[] {
    const def = definicao.value;
    if (!def) return [];

    const lista: AtributoImpresso[] = [];

    const acrescentar = (
      campo: SegmentField,
      fonte: Record<string, unknown> | null | undefined,
    ) => {
      const valor = fonte?.[campo.nome];
      // Campo em branco não vira linha "Chassi: -": na via em papel o espaço é
      // caro e um rótulo sem valor só ocupa lugar.
      if (valor === null || valor === undefined || valor === '') return;
      lista.push({ label: campo.label, valor: String(valor) });
    };

    for (const campo of def.veiculo ?? []) {
      if (JA_NA_VIA.has(campo.nome)) continue;
      acrescentar(campo, dadosObjeto);
    }

    for (const nome of CHECKIN_NA_VIA) {
      const campo = (def.checkin ?? []).find((c) => c.nome === nome);
      if (campo) acrescentar(campo, dadosOS);
    }

    return lista;
  }

  return { atributos };
}
