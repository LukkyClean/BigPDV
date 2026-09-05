/**
 * Chaves de cache do módulo financeiro.
 *
 * Todas pendem de `FINANCEIRO_KEY` porque o TanStack casa chave por PREFIXO:
 * uma `invalidateQueries([FINANCEIRO_KEY])` alcança tudo o que está aqui, e não
 * alcançaria uma chave-irmã escrita solta (ver o comentário em
 * shared/constants/entityKeys.ts — a divergência já custou caro no catálogo).
 *
 * Dar baixa numa conta mexe em vários lugares ao mesmo tempo (a lista, o saldo,
 * o resultado do mês), então o prefixo único não é organização: é o que faz a
 * tela inteira se atualizar de uma vez.
 */
import { FINANCEIRO_KEY } from '@/shared/constants/entityKeys';

export const financeiroKeys = {
  todos: [FINANCEIRO_KEY] as const,
  contasPagar: (filtros?: unknown) => [FINANCEIRO_KEY, 'contas-pagar', filtros] as const,
  contasReceber: (filtros?: unknown) => [FINANCEIRO_KEY, 'contas-receber', filtros] as const,
  planoContas: () => [FINANCEIRO_KEY, 'plano-contas'] as const,
  resumo: (periodo?: unknown) => [FINANCEIRO_KEY, 'resumo', periodo] as const,
  custoDetalhe: (periodo?: unknown) => [FINANCEIRO_KEY, 'custo-detalhe', periodo] as const,
  fluxoCaixa: (dias?: unknown) => [FINANCEIRO_KEY, 'fluxo-caixa', dias] as const,
  conciliacao: (periodo?: unknown) => [FINANCEIRO_KEY, 'conciliacao', periodo] as const,
  extrato: (filtros?: unknown) => [FINANCEIRO_KEY, 'extrato', filtros] as const,
  serie: (meses?: unknown) => [FINANCEIRO_KEY, 'serie', meses] as const,
  projecao: () => [FINANCEIRO_KEY, 'projecao'] as const,
};
