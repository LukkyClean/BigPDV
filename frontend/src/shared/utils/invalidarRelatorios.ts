import type { QueryClient } from '@tanstack/vue-query';

/**
 * Raízes de cache que dependem de dinheiro e estoque.
 *
 * São as mesmas de `reportKeys.all` (modules/reports/query.keys.ts) e
 * `dashboardKeys.all` (modules/home/constants/dashboard.constants.ts).
 * Ficam literais aqui de propósito: `shared/` não deve importar de `modules/`.
 * Se alguma das duas raízes mudar, muda aqui também.
 */
const RAIZES_FINANCEIRAS = [['relatorios'], ['dashboard']] as const;

/**
 * Invalida relatórios e dashboard depois de uma operação que mexe em dinheiro
 * ou em estoque.
 *
 * Existe porque o cache tem 5 minutos de vida (`vueQueryConfig`) e as mutações
 * só invalidavam as chaves do próprio módulo. Cancelar uma venda atualizava a
 * lista de vendas mas deixava o relatório mostrando o dinheiro no caixa — e o
 * usuário não tem como saber que está olhando um número velho.
 *
 * Chame em toda mutação que altere faturamento, comissão ou estoque:
 * finalizar/cancelar/reabrir venda e OS, e movimentação de estoque.
 */
export function invalidarRelatorios(queryClient: QueryClient): void {
  for (const queryKey of RAIZES_FINANCEIRAS) {
    queryClient.invalidateQueries({ queryKey });
  }
}
