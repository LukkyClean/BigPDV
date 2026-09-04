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

/**
 * Chaves do cadastro de terminais.
 *
 * Prefixo próprio: terminal não é turno. Renomear uma máquina não pode
 * invalidar a sessão de caixa aberta, nem o contrário — são coisas com tempos de
 * vida diferentes, e foi misturá-las que criou o bug que esta fase conserta.
 */
export const TERMINAIS_KEY = 'terminais' as const;

export const terminaisKeys = {
  all: [TERMINAIS_KEY] as const,
  lista: () => [...terminaisKeys.all, 'lista'] as const,
  este: () => [...terminaisKeys.all, 'este'] as const,
};
