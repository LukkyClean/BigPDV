/**
 * Chaves de cache do caixa.
 *
 * Prefixo próprio ('caixa') porque o turno é uma entidade própria — não é venda.
 * Toda mutation do caixa invalida SÓ este prefixo: chave-irmã não é alcançada
 * pelo TanStack, então tudo que precisa ser invalidado junto tem que pender daqui.
 */
export const CAIXA_KEY = 'caixa' as const;

export const caixaKeys = {
  all: [CAIXA_KEY] as const,
  atual: () => [...caixaKeys.all, 'atual'] as const,
  sessao: (sessaoId: number) => [...caixaKeys.all, 'sessao', sessaoId] as const,
};
