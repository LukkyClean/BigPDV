/**
 * @fileoverview Peso guardado em GRAMAS INTEIRAS, exibido em quilos.
 *
 * O sistema já resolve exatamente este problema em outro lugar: dinheiro. Nada
 * aqui guarda "4,50" — guarda `450` centavos, inteiro, e a tela mostra R$ 4,50
 * (ver `finance.ts`, ao lado). Peso segue a mesma convenção: guarda `2500`,
 * mostra 2,5 kg.
 *
 * POR QUE NÃO DECIMAL NO BANCO. A serigrafia vende sacola por quilo, e
 * `quantidade` é inteiro em estoque, movimentação e item de OS. Converter as
 * quatro colunas exigiria migração no banco vivo de duas lojas em produção —
 * e o SQLite recria a tabela inteira para mudar tipo de coluna, sem backup
 * automático antes. Além disso, o custo médio ponderado faz conta com essas
 * quantidades: hoje é tudo inteiro e fecha exato; com decimal entram
 * arredondamentos, e custo médio que arredonda errado vira relatório de lucro
 * mentiroso devagar, sem ninguém perceber.
 *
 * O PREÇO DESTA ESCOLHA, dito em voz alta: `quantidade` passa a significar
 * "unidades" para produto em UN e "gramas" para produto em KG. Todo lugar que
 * EXIBE quantidade de item em quilo precisa passar por aqui. Esquecer num canto
 * mostra "50000 kg" na tela. É o mesmo contrato que o centavo já tem, e a
 * mitigação é a mesma: uma função só, usada em todos os lugares.
 */

/** Unidades cujo valor é guardado em gramas. */
const UNIDADES_EM_GRAMAS = new Set(['KG', 'G']);

/** True se a quantidade deste item é guardada em gramas. */
export function pesaEmGramas(unidade: string | null | undefined): boolean {
  return UNIDADES_EM_GRAMAS.has((unidade ?? '').toUpperCase());
}

/**
 * Quilos digitados pelo usuário → gramas inteiras para o banco.
 * Aceita vírgula decimal, que é como se escreve em português.
 * Ex: "2,5" → 2500
 */
export function quilosParaGramas(valor: string | number): number {
  const texto = String(valor).replace(/[^\d,.-]/g, '').replace(',', '.');
  const numero = Number(texto);
  if (texto === '' || Number.isNaN(numero)) return 0;
  return Math.round(numero * 1000);
}

/**
 * Gramas do banco → texto em quilos para o input.
 * Sem casas decimais à toa: 50000 vira "50", não "50,000".
 * Ex: 2500 → "2,5" | 50000 → "50"
 */
export function gramasParaQuilos(gramas: number): string {
  const quilos = (gramas ?? 0) / 1000;
  return quilos.toLocaleString('pt-BR', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  });
}

/**
 * Quantidade pronta para a tela e para o papel, com a unidade junto.
 *
 * É a função que todo lugar que mostra quantidade deve usar — é ela que impede
 * o "50000 kg". Item que não pesa passa reto e sai como sempre saiu.
 * Ex: (2500, 'KG') → "2,5 kg" | (3, 'UN') → "3 UN"
 */
export function formatarQuantidade(
  quantidade: number,
  unidade: string | null | undefined,
): string {
  if (!pesaEmGramas(unidade)) return `${quantidade} ${unidade ?? 'UN'}`;
  return `${gramasParaQuilos(quantidade)} kg`;
}
