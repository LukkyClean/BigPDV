import { computed } from 'vue';

import { useOSFieldDefinition } from './useOSFieldDefinition.queries';
import type { SegmentDefinition, SegmentField } from './segmentDefinition.type';

/** Par rótulo/valor pronto para sair na via, já formatado como texto. */
export interface AtributoImpresso {
  label: string;
  valor: string;
}

/**
 * Campos que a via já imprime em linha própria (Marca, Modelo, identificador,
 * Cor). Rede de segurança para contrato antigo que não declare `origem` — o
 * critério de verdade é `origem === 'coluna'`, logo abaixo.
 */
const JA_NA_VIA = new Set(['placa', 'numero_serie', 'marca', 'modelo', 'cor']);

/**
 * Do check-in (escopo OS), só a quilometragem entra na via do cliente.
 * Combustível, pneus, estepe, prisma e CT são conteúdo da ficha de vistoria —
 * no quadro do recibo eles empurrariam o resto da folha para baixo.
 */
const CHECKIN_NA_VIA = ['km_entrada'];

/** Chave da OS em que o tipo de trabalho fica gravado (ver OSObjetoDinamicoTab). */
const CHAVE_TIPO = 'tipo_trabalho';

/**
 * Um campo que vai para uma coluna real já saiu nas linhas fixas da via
 * (identificador, Marca, Modelo, Cor). Repetir daria "Placa" duas vezes.
 *
 * Vale para os dois desenhos: em oficina isto reproduz exatamente o que a lista
 * `JA_NA_VIA` fazia (placa/marca/modelo/cor são as colunas), e em serigrafia
 * cobre `codigo_arte`/`nome_arte`/`empresa_arte`, cujos nomes não estão em lista
 * nenhuma — é a diferença entre a regra ser metadado ou ser um `Set` que alguém
 * precisa lembrar de atualizar a cada segmento.
 */
function jaSaiNasLinhasFixas(campo: SegmentField): boolean {
  return campo.origem === 'coluna' || JA_NA_VIA.has(campo.nome);
}

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

  /**
   * Campos do tipo de trabalho da OS, quando o segmento tem tipos.
   * `null` = segmento de formulário único, que segue pelo caminho de sempre.
   */
  function camposDoTipoDaOS(
    def: SegmentDefinition,
    dadosOS: Record<string, unknown> | null | undefined,
  ): SegmentField[] | null {
    const tipos = def.tipos ?? [];
    if (tipos.length === 0) return null;
    const escolhido = dadosOS?.[CHAVE_TIPO] as string | undefined;
    const tipo = tipos.find((t) => t.id === escolhido) ?? tipos[0];
    return tipo?.campos ?? [];
  }

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

      // Campo `lista` (ex: referências de sacola). Sem este ramo o `String()`
      // abaixo sairia "20.1,22" — colado, sem espaço — e uma lista vazia viraria
      // um rótulo com valor em branco na via.
      if (Array.isArray(valor)) {
        const itens = valor.filter((item) => item !== null && item !== undefined && item !== '');
        if (itens.length === 0) return;
        lista.push({ label: campo.label, valor: itens.map(String).join(', ') });
        return;
      }

      // Booleano só faz sentido impresso como palavra.
      const texto = typeof valor === 'boolean' ? (valor ? 'Sim' : 'Não') : String(valor);
      lista.push({ label: campo.label, valor: texto });
    };

    // --- Segmento com tipos de trabalho (serigrafia) ---
    // Aqui os campos SÃO a ordem de produção: molde, cores, papel, alça. Saem
    // todos, dos dois escopos, porque é o que quem vai estampar precisa ler.
    const camposDoTipo = camposDoTipoDaOS(def, dadosOS);
    if (camposDoTipo) {
      for (const campo of camposDoTipo) {
        if (jaSaiNasLinhasFixas(campo)) continue;
        acrescentar(campo, campo.escopo === 'os' ? dadosOS : dadosObjeto);
      }
      return lista;
    }

    // --- Segmento de formulário único (oficina, informática) ---
    for (const campo of def.veiculo ?? []) {
      if (jaSaiNasLinhasFixas(campo)) continue;
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
