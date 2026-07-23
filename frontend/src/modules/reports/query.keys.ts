export const reportKeys = {
  all: ['relatorios'] as const,
  faturamento: (inicio: string, fim: string) =>
    [...reportKeys.all, 'faturamento', inicio, fim] as const,
  ranking: (inicio: string, fim: string) =>
    [...reportKeys.all, 'ranking', inicio, fim] as const,
  comissao: (inicio: string, fim: string) =>
    [...reportKeys.all, 'comissao', inicio, fim] as const,
};
