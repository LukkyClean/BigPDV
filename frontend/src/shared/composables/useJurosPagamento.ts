import { ref, computed } from 'vue';

/**
 * Quem arca com os juros de um pagamento no cartão.
 *
 * - `CLIENTE`: juros repassado. O cliente paga a mais e o `valor` do pagamento
 *   já inclui o acréscimo. É o comportamento histórico e continua sendo o padrão.
 * - `LOJA`: juros absorvido. O cliente paga o preço combinado, sem acréscimo, e
 *   a loja recebe menos da operadora. O `valor` do pagamento NÃO inclui o juros.
 */
export type JurosResponsavel = 'CLIENTE' | 'LOJA';

export const JUROS_RESPONSAVEL_OPTIONS: { value: JurosResponsavel; label: string }[] = [
  { value: 'CLIENTE', label: 'Repassar ao cliente' },
  { value: 'LOJA', label: 'Loja absorve' },
];

/**
 * Converte o texto digitado numa taxa utilizável.
 *
 * O campo é `type="text"` de propósito. Um `<input type="number">` usa o
 * separador decimal do **locale do navegador**: com o navegador em inglês, a
 * tecla de vírgula é ignorada e o usuário não consegue digitar "3,5" de jeito
 * nenhum — a tecla morre antes de qualquer código nosso rodar. Aceitando texto,
 * a vírgula entra e a conversão acontece aqui, que absorve `''`, `null`, `NaN`,
 * vírgula, ponto e lixo digitado sem quebrar o cálculo.
 */
export function normalizarTaxaJuros(valor: unknown): number {
  const bruto = typeof valor === 'number' ? valor : parseFloat(String(valor ?? '').replace(',', '.'));
  if (!Number.isFinite(bruto)) return 0;
  return Math.min(100, Math.max(0, bruto));
}

/** Formata a taxa para exibição em pt-BR (vírgula decimal). Vazio quando é zero. */
export function formatarTaxaJuros(taxa: number): string {
  return taxa === 0 ? '' : String(taxa).replace('.', ',');
}

/**
 * Estado e cálculo dos juros de um pagamento, compartilhado entre o checkout de
 * Vendas e a finalização de OS — que precisam se comportar de forma idêntica.
 */
export function useJurosPagamento() {
  /**
   * Ligado direto ao input, como texto. Nada é escrito de volta enquanto o
   * usuário digita: reescrever o campo no meio da digitação era o que apagava
   * o número e jogava o cursor para o começo. A normalização acontece só no
   * blur, via `normalizar()`.
   */
  const taxaInput = ref<number | string>('');
  const responsavel = ref<JurosResponsavel>('CLIENTE');

  /** Taxa efetiva, sempre um número entre 0 e 100. É esta que os cálculos usam. */
  const taxa = computed(() => normalizarTaxaJuros(taxaInput.value));
  const temJuros = computed(() => taxa.value > 0);
  const lojaAbsorve = computed(() => responsavel.value === 'LOJA');

  /** Juros em centavos sobre uma base em centavos. */
  function calcular(base: number): number {
    if (!Number.isFinite(base) || base <= 0) return 0;
    return Math.round(base * (taxa.value / 100));
  }

  /** Quanto o cliente paga a mais. Zero quando a loja absorve. */
  function acrescimoDoCliente(base: number): number {
    return lojaAbsorve.value ? 0 : calcular(base);
  }

  /** Quanto sai do bolso da loja. Zero quando o juros é repassado. */
  function custoDaLoja(base: number): number {
    return lojaAbsorve.value ? calcular(base) : 0;
  }

  /** Chamar no blur do campo: arruma o que ficou meio digitado. */
  function normalizar(): void {
    taxaInput.value = formatarTaxaJuros(taxa.value);
  }

  function reset(): void {
    taxaInput.value = '';
    responsavel.value = 'CLIENTE';
  }

  return {
    taxaInput,
    responsavel,
    taxa,
    temJuros,
    lojaAbsorve,
    calcular,
    acrescimoDoCliente,
    custoDaLoja,
    normalizar,
    reset,
  };
}
