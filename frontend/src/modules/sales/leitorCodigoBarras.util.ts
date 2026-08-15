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

/**
 * O produto a ser bipado, ou `null` quando não há certeza.
 *
 * Exige DUAS coisas ao mesmo tempo: um único candidato com aquele código exato,
 * e correspondência literal em `codigo_barras` ou `sku`. "Veio um resultado só"
 * não basta — a busca é ampla (nome, marca, categoria) e uma coincidência
 * somaria o produto errado sem ninguém perceber.
 *
 * Na dúvida devolve `null`, e a tela cai no fluxo normal: a lista aparece e a
 * pessoa escolhe. Errar para a lista custa um clique; errar para o carrinho
 * custa dinheiro no fechamento.
 */
export function encontrarPorCodigoExato(
  termo: string,
  produtos: ProductSaleListItem,
): ProductSaleListItem[number] | null {
  const alvo = (termo ?? '').trim();
  if (!alvo) return null;

  const exatos = produtos.filter(
    (p) => p.codigo_barras?.trim() === alvo || p.sku?.trim() === alvo,
  );

  return exatos.length === 1 ? exatos[0] : null;
}
