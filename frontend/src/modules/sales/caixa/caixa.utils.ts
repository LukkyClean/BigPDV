/**
 * Formata centavos como moeda. Aceita negativo — a diferença de caixa é o único
 * lugar do sistema em que o sinal importa de verdade para quem lê.
 */
export function formatarCentavos(centavos: number): string {
  return ((centavos ?? 0) / 100).toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  });
}
