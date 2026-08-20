import type { ProductSaleListItem } from './schemas/productSale.schema';

/**
 * Regras do leitor de código de barras na venda.
 *
 * POR QUE ESTE ARQUIVO EXISTE. O leitor "digita" o código inteiro em
 * milissegundos e manda um Enter logo atrás. Como a busca da tela é debounced em
 * 300 ms, quando o Enter chegava a consulta ainda nem tinha saído: o código
 * ficava parado na caixa e o operador terminava no braço, com seta e Enter.
 *
 * A saída foi NÃO mexer no caminho de quem digita. Quem digita continua com o
 * debounce, a lista e a navegação por seta exatamente como sempre foi. O leitor
 * ganhou um atalho próprio, que só é considerado quando o texto tem cara de
 * código de barras.
 */

/** Comprimento mínimo para um texto ser tratado como código de barras.
 *
 * EAN-8 é o menor padrão em uso no varejo. Abaixo disso é busca por nome ou
 * código curto digitado à mão, e tratar como leitura automática arriscaria
 * somar item errado no carrinho de alguém que só estava pesquisando.
 */
const MIN_DIGITOS = 8;

/** Só dígitos e comprimento de código real. */
export function pareceCodigoDeBarras(termo: string): boolean {
  const limpo = (termo ?? '').trim();
  return limpo.length >= MIN_DIGITOS && /^\d+$/.test(limpo);
}

/** O que a busca por código exato encontrou. */
export type ResolucaoCodigo =
  | { tipo: 'unico'; produto: ProductSaleListItem[number] }
  | { tipo: 'nenhum' }
  | { tipo: 'ambiguo'; quantos: number };

/**
 * Resolve um código digitado ou bipado em um produto — ou diz por que não deu.
 *
 * Exige DUAS coisas ao mesmo tempo: um único candidato com aquele código exato,
 * e correspondência literal em `codigo_barras` ou `sku`. "Veio um resultado só"
 * não basta — a busca é ampla (nome, marca, categoria) e uma coincidência
 * somaria o produto errado sem ninguém perceber.
 *
 * Na dúvida NÃO escolhe: errar para a lista custa um clique, errar para o
 * carrinho custa dinheiro no fechamento. Mas a dúvida agora tem nome — `nenhum`
 * e `ambiguo` são coisas diferentes e merecem mensagens diferentes. Enquanto os
 * dois voltavam como o mesmo `null`, a tela não tinha o que dizer e não dizia
 * nada.
 */
export function resolverPorCodigoExato(
  termo: string,
  produtos: ProductSaleListItem,
): ResolucaoCodigo {
  const alvo = (termo ?? '').trim();
  if (!alvo) return { tipo: 'nenhum' };

  const exatos = produtos.filter(
    (p) => p.codigo_barras?.trim() === alvo || p.sku?.trim() === alvo,
  );

  if (exatos.length === 1) return { tipo: 'unico', produto: exatos[0] };
  if (exatos.length === 0) return { tipo: 'nenhum' };
  return { tipo: 'ambiguo', quantos: exatos.length };
}
