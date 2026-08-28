// Prefixo canônico de cache por entidade.
//
// Toda query que lê a mesma entidade — não importa em que módulo mora — deve
// começar sua queryKey por um destes prefixos, e toda mutation que a altera
// invalida só o prefixo. O TanStack casa chave por prefixo, então as sub-chaves
// podem ser livres (e o formato do dado pode divergir): `[PRODUTOS, 'venda-busca',
// termo]` e `[PRODUTOS, busca, limite]` são caches independentes que uma única
// `invalidateQueries([PRODUTOS])` alcança.
//
// A regra existe porque a divergência custou caro: vendas cacheava produto em
// 'products', o estoque em 'produtos', e o item da OS cacheava serviço em
// 'servicos-os-item' enquanto o catálogo usava 'servicos'. Como invalidar uma
// chave nunca alcança a vizinha, editar o preço de um serviço não aparecia na OS
// e produto novo não entrava na busca de vendas — só com F5.

export const PRODUTOS_KEY = 'produtos' as const;
export const SERVICOS_KEY = 'servicos' as const;
export const CLIENTES_KEY = 'clientes' as const;
export const FINANCEIRO_KEY = 'financeiro' as const;
