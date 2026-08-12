/**
 * @fileoverview Formatação de quantidade com unidade de medida.
 *
 * Existe pelo mesmo motivo do `formatCurrency`: a unidade estava escrita à mão
 * em cada tela ("{{ quantidade }} un"), sempre como "un", ignorando o
 * `unidade_medida` que o produto já traz do cadastro.
 *
 * Não era só rótulo errado. O estoque é fracionado (`Float` no banco), então uma
 * sacola comprada por peso aparecia como **"2,5 un"** — que se lê como duas
 * sacolas e meia, quando são 2,5 kg e podem ser 200 sacolas. Num inventário ou
 * numa conferência de balcão, isso é erro de leitura sobre o número que serve
 * justamente para contar mercadoria.
 */

/** Unidades vendidas a granel, em que a fração É o normal. */
const UNIDADES_FRACIONADAS = new Set(['KG', 'G', 'L', 'ML', 'M', 'CM']);

/** Fallback: sem unidade cadastrada, é peça — o caso de informática e oficina. */
const UNIDADE_PADRAO = 'UN';

/**
 * Só a sigla, minúscula. Para quando o número já foi formatado à parte — é o
 * caso do painel de transações, onde ele leva sinal (+/−) na frente.
 */
export function siglaUnidade(unidade?: string | null): string {
  return ((unidade ?? '').trim() || UNIDADE_PADRAO).toLowerCase();
}

export function unidadeEhFracionada(unidade?: string | null): boolean {
  return UNIDADES_FRACIONADAS.has((unidade ?? UNIDADE_PADRAO).trim().toUpperCase());
}

/**
 * Formata a quantidade com a unidade do cadastro.
 *
 * Casas decimais seguem a unidade, e não o valor: "2,5 kg" descreve o mundo,
 * "2,5 un" não descreve nada. Em unidade inteira o número é arredondado; em
 * unidade de peso/volume, mostra até 3 casas — e corta os zeros à direita, para
 * "2 kg" não virar "2,000 kg".
 *
 * @param quantidade  valor numérico do estoque/item
 * @param unidade     `produto.unidade_medida` (ou do item da OS). Vazio = "UN".
 */
export function formatarQuantidade(
  quantidade: number | null | undefined,
  unidade?: string | null,
): string {
  const valor = Number(quantidade ?? 0);
  const seguro = Number.isFinite(valor) ? valor : 0;

  const sigla = (unidade ?? '').trim() || UNIDADE_PADRAO;

  const texto = unidadeEhFracionada(sigla)
    ? seguro.toLocaleString('pt-BR', { maximumFractionDigits: 3 })
    : Math.round(seguro).toLocaleString('pt-BR');

  return `${texto} ${sigla.toLowerCase()}`;
}
